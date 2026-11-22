import re
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Final

from app.application.errors.shop import (
    BelowMinimum,
    ExecutorNotFound,
    InvalidInput,
    WalletNotSet,
)
from app.application.i18n_text import local_date
from app.application.interactors.base import BaseInteractor
from app.application.interactors.ledger import LedgerService
from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.ledger import LedgerGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.settings import SettingsGateway
from app.application.ports.uow import UnitOfWork
from app.application.settings_keys import DEFAULT_MIN_WITHDRAWAL, MIN_WITHDRAWAL
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.ledger import LedgerEntry, Withdrawal
from app.domain.money import money

HISTORY_LIMIT: Final = 10
_WALLET_RE: Final = re.compile(r"\S{1,128}")


@dataclass(frozen=True)
class WalletSummary:
    hold: Decimal
    available: Decimal
    wallet: str | None
    minimum: Decimal
    entries: list[LedgerEntry]
    holds: list[tuple[datetime, Decimal]]  # (hold ends, earning), earliest first

    def hold_days(self, tz: str | None) -> list[tuple[date, Decimal]]:
        """What becomes available on which day (his time zone), earliest first."""
        days: dict[date, Decimal] = {}
        for at, amount in self.holds:
            day = local_date(at, tz)
            days[day] = days.get(day, Decimal(0)) + amount
        return sorted(days.items())


@dataclass(frozen=True)
class ExecutorWalletInteractor(BaseInteractor):
    uow: UnitOfWork
    executors: ExecutorsGateway
    orders: OrdersGateway
    ledger: LedgerService
    ledger_gateway: LedgerGateway
    settings: SettingsGateway

    async def _minimum(self) -> Decimal:
        return money(str(await self.settings.get(MIN_WITHDRAWAL, str(DEFAULT_MIN_WITHDRAWAL))))

    async def summary(self, executor_id: int) -> WalletSummary:
        profile = await self.executors.get_profile(executor_id)
        if profile is None:
            raise ExecutorNotFound(executor_id)
        return WalletSummary(
            hold=await self.ledger_gateway.balance(executor_id, LedgerAccount.executor_hold),
            available=await self.ledger_gateway.balance(
                executor_id, LedgerAccount.executor_available
            ),
            wallet=profile.payout_wallet,
            minimum=await self._minimum(),
            entries=await self.executors.wallet_entries(executor_id, HISTORY_LIMIT),
            holds=await self.orders.held_earnings(executor_id),
        )

    async def set_wallet(self, executor_id: int, address: str) -> None:
        """A single token of up to 128 characters, no spaces."""
        address = address.strip()
        if not _WALLET_RE.fullmatch(address):
            raise InvalidInput("wallet")
        try:
            profile = await self.executors.get_profile(executor_id)
            if profile is None:
                raise ExecutorNotFound(executor_id)
            profile.payout_wallet = address
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise

    async def withdraw(self, executor_id: int) -> Withdrawal:
        """A request only: everything available goes to a pending withdrawal. Sending the money
        is not done here (spec 15b)."""
        try:
            await self.ledger_gateway.lock_user(executor_id)  # before the balance is read
            profile = await self.executors.get_profile(executor_id)
            if profile is None:
                raise ExecutorNotFound(executor_id)
            if not profile.payout_wallet:
                raise WalletNotSet(executor_id)
            amount = await self.ledger_gateway.balance(
                executor_id, LedgerAccount.executor_available
            )
            if amount <= 0 or amount < await self._minimum():
                raise BelowMinimum(str(amount))
            withdrawal = Withdrawal(
                executor_id=executor_id, amount=amount, address=profile.payout_wallet
            )
            await self.executors.add_withdrawal(withdrawal)
            await self.ledger.post(
                executor_id,
                LedgerAccount.executor_available,
                -amount,
                LedgerKind.withdrawal,
                ref=f"withdrawal:{withdrawal.id}",
            )
            await self.uow.commit()
            return withdrawal
        except BaseException:
            await self.uow.rollback()
            raise
