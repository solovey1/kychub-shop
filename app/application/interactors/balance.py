from dataclasses import dataclass
from decimal import Decimal
from uuid import uuid4

from app.application.errors.shop import InvalidAmount, TopupDisabled
from app.application.interactors.base import BaseInteractor
from app.application.interactors.ledger import LedgerService
from app.application.interactors.promo import PromoService
from app.application.models.config import AppConfig
from app.application.ports.repositories.balance import BalanceGateway
from app.application.ports.repositories.ledger import LedgerGateway
from app.application.ports.repositories.promo import PromoGateway
from app.application.ports.repositories.users import UsersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.audit import AuditLog
from app.domain.enums.ledger import LedgerAccount, LedgerKind, PaymentStatus
from app.domain.ledger import LedgerEntry, Payment
from app.domain.money import money
from app.domain.promo import PromoCodeUsage
from app.domain.user import User

HISTORY_LIMIT = 10
MAX_TOPUP = Decimal("1000.00")


def parse_money(text: str) -> Decimal:
    """User input like "12,5" to Decimal with 2 places. Raises InvalidAmount."""
    try:
        return money(text.strip().replace(",", "."))
    except ValueError as e:
        raise InvalidAmount(text) from e


@dataclass(frozen=True)
class BalanceInteractor(BaseInteractor):
    uow: UnitOfWork
    ledger: LedgerService
    ledger_gateway: LedgerGateway
    gateway: BalanceGateway
    users: UsersGateway
    promo: PromoService
    promo_gateway: PromoGateway
    config: AppConfig

    @property
    def test_payments_enabled(self) -> bool:
        return self.config.common.test_payments

    async def balance(self, user_id: int) -> Decimal:
        return await self.ledger_gateway.balance(user_id, LedgerAccount.main)

    async def summary(self, user_id: int) -> tuple[Decimal, list[LedgerEntry]]:
        return await self.balance(user_id), await self.gateway.history(user_id, HISTORY_LIMIT)

    async def get_user(self, user_id: int) -> User | None:
        return await self.users.get(user_id)

    async def test_topup(self, user_id: int, amount: Decimal) -> Payment:
        if not self.test_payments_enabled:
            raise TopupDisabled()
        amount = money(amount)
        if not 0 < amount <= MAX_TOPUP:
            raise InvalidAmount(str(amount))
        try:
            await self.ledger_gateway.lock_user(user_id)
            payment = Payment(
                user_id=user_id,
                provider="test",
                external_id=uuid4().hex,
                amount=amount,
                status=PaymentStatus.success,
            )
            await self.gateway.add_payment(payment)
            await self.ledger.post(
                user_id,
                LedgerAccount.main,
                amount,
                LedgerKind.topup,
                ref=f"payment:{payment.id}",
            )
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise
        return payment

    async def redeem_bonus(self, user_id: int, code: str) -> Decimal:
        try:
            await self.ledger_gateway.lock_user(user_id)
            promo = await self.promo.check(user_id, code, bonus=True, lock=True)
            bonus = promo.bonus_amount
            if bonus is None:  # check() guarantees it; keeps the types honest
                raise InvalidAmount(code)
            promo.times_used += 1
            await self.promo_gateway.add_usage(
                PromoCodeUsage(promo_code_id=promo.id, user_id=user_id)
            )
            ref = f"promo:{promo.id}:{user_id}"
            if promo.reusable:
                ref += f":{promo.times_used}"
            await self.ledger.post(
                user_id, LedgerAccount.main, bonus, LedgerKind.promo_bonus, ref=ref
            )
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise
        return bonus

    async def admin_topup(
        self, admin_id: int, user_id: int, amount: Decimal, comment: str
    ) -> LedgerEntry:
        """Negative amount debits the balance."""
        amount = money(amount)
        if amount == 0:
            raise InvalidAmount("0")
        try:
            entry = await self.ledger.post(
                user_id, LedgerAccount.main, amount, LedgerKind.admin_adjust
            )
            await self.gateway.add_audit(
                AuditLog(
                    actor_id=admin_id,
                    action="balance.adjust",
                    target=f"user:{user_id}",
                    payload={"amount": str(amount), "comment": comment},
                )
            )
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise
        return entry
