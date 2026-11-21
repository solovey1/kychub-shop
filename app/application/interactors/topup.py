import logging
from dataclasses import dataclass
from datetime import timedelta
from decimal import Decimal
from typing import Final
from uuid import uuid4

from app.application.errors.shop import (
    GatewayUnavailable,
    InvalidAmount,
    PaymentNotFound,
    TopupDisabled,
)
from app.application.interactors.base import BaseInteractor
from app.application.interactors.ledger import LedgerService
from app.application.models.config import AppConfig
from app.application.ports.payments import (
    STATUS_RANK,
    CreatedPayment,
    PaymentGateways,
)
from app.application.ports.repositories.ledger import LedgerGateway
from app.application.ports.repositories.payments import PaymentsGateway
from app.application.ports.uow import UnitOfWork
from app.domain.enums.ledger import LedgerAccount, LedgerKind, PaymentStatus
from app.domain.ledger import Payment
from app.domain.money import money

logger: Final = logging.getLogger(__name__)


@dataclass(frozen=True)
class TopupInteractor(BaseInteractor):
    uow: UnitOfWork
    ledger: LedgerService
    ledger_gateway: LedgerGateway
    payments: PaymentsGateway
    gateways: PaymentGateways
    config: AppConfig

    @property
    def providers(self) -> list[str]:
        """Codes of the enabled gateways."""
        return list(self.gateways)

    @property
    def limits(self) -> tuple[Decimal, Decimal]:
        cfg = self.config.payments
        return cfg.min_topup, cfg.max_topup

    @property
    def binance_pay_id(self) -> str | None:
        return self.config.payments.binance_pay_id

    def validate(self, amount: Decimal) -> Decimal:
        """Two decimal places at most and within the configured limits, else InvalidAmount."""
        try:
            amount = money(amount)
        except (ValueError, TypeError) as e:
            raise InvalidAmount(str(amount)) from e
        low, high = self.limits
        if not low <= amount <= high:
            raise InvalidAmount(str(amount))
        return amount

    async def create(
        self, user_id: int, amount: Decimal, provider: str
    ) -> tuple[Payment, CreatedPayment]:
        gateway = self.gateways.get(provider)
        if gateway is None:
            raise TopupDisabled(provider)
        amount = self.validate(amount)
        payment_id = uuid4().hex
        try:
            created = await gateway.create_payment(amount, payment_id, f"Top-up {amount} USDT")
        except Exception as e:
            logger.exception("%s: could not create a payment", provider)
            raise GatewayUnavailable(provider) from e
        try:
            payment = Payment(
                user_id=user_id,
                provider=provider,
                external_id=created.pay_id,
                amount=amount,
                status=PaymentStatus.created,
                raw={"payment_id": payment_id},
            )
            await self.payments.add(payment)
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise
        return payment, created

    async def get(self, payment_id: int) -> Payment:
        payment = await self.payments.get(payment_id)
        if payment is None:
            raise PaymentNotFound(payment_id)
        return payment

    async def check(self, payment_id: int) -> Payment:
        return (await self.sync(payment_id))[0]

    async def sync(self, payment_id: int) -> tuple[Payment, bool]:
        """Ask the gateway and move the status forward. Second value: credited by this call."""
        payment = await self.get(payment_id)
        if payment.status is PaymentStatus.success:
            return payment, False
        gateway = self.gateways.get(payment.provider)
        if gateway is None:  # gateway switched off in the config
            return payment, False
        try:
            status = await gateway.get_status(payment.external_id, payment.amount)
        except Exception as e:
            logger.warning(
                "%s: status of payment %s unavailable: %r", payment.provider, payment.id, e
            )
            return payment, False
        if status is PaymentStatus.success:
            credited = await self.credit(payment.id)
            return await self.get(payment.id), credited
        if STATUS_RANK[status] > STATUS_RANK[payment.status]:
            return await self._advance(payment.id, status), False
        return payment, False

    async def credit(self, payment_id: int) -> bool:
        """Mark paid and post the top-up in one transaction. True if credited now."""
        try:
            payment = await self.payments.get_for_update(payment_id)
            if payment is None:
                raise PaymentNotFound(payment_id)
            ref = f"payment:{payment.id}"
            already = await self.ledger_gateway.get_by_ref(
                payment.user_id, LedgerAccount.main, LedgerKind.topup, ref
            )
            payment.status = PaymentStatus.success
            if already is None:
                await self.ledger.post(
                    payment.user_id, LedgerAccount.main, payment.amount, LedgerKind.topup, ref=ref
                )
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise
        return already is None

    async def _advance(self, payment_id: int, status: PaymentStatus) -> Payment:
        try:
            payment = await self.payments.get_for_update(payment_id)
            if payment is None:
                raise PaymentNotFound(payment_id)
            if STATUS_RANK[status] > STATUS_RANK[payment.status]:
                payment.status = status
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise
        return payment

    async def pending(self, max_age: timedelta) -> list[Payment]:
        return await self.payments.pending(max_age)

    async def unfulfilled_success(self) -> list[Payment]:
        return await self.payments.unfulfilled_success()
