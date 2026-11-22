import re
from dataclasses import dataclass
from typing import Final

from app.application.errors.shop import Conflict, InvalidField
from app.application.interactors.admin.base import AdminInteractor
from app.application.interactors.ledger import LedgerService
from app.domain.enums.ledger import LedgerAccount, LedgerKind, WithdrawalStatus
from app.domain.ledger import Withdrawal
from app.utils.time import datetime_now

LIST_LIMIT: Final = 100
_TX_RE: Final = re.compile(r"\S{4,128}")


@dataclass(frozen=True)
class WithdrawalRow:
    withdrawal: Withdrawal
    alias: str | None
    name: str


@dataclass(frozen=True)
class Decided:
    """`changed` is False when the withdrawal was already decided this way (nothing was done)."""

    withdrawal: Withdrawal
    changed: bool


@dataclass(frozen=True)
class MoneyAdminInteractor(AdminInteractor):
    ledger: LedgerService

    async def withdrawals(self, status: WithdrawalStatus) -> list[WithdrawalRow]:
        rows = await self.db.withdrawals(status, LIST_LIMIT)
        ids = [w.executor_id for w in rows]
        aliases, names = await self.db.executor_aliases(ids), await self.db.user_names(ids)
        return [
            WithdrawalRow(w, aliases.get(w.executor_id), names.get(w.executor_id, ""))
            for w in rows
        ]

    async def pay(self, actor: int, withdrawal_id: int, tx_hash: str) -> Decided:
        """pending -> paid. The same transaction hash again changes nothing."""
        tx_hash = tx_hash.strip()
        if not _TX_RE.fullmatch(tx_hash):
            raise InvalidField("tx_hash", "4 to 128 characters, no spaces")
        async with self.tx():
            w = await self.need(Withdrawal, withdrawal_id)  # row lock: one decision at a time
            if w.status is WithdrawalStatus.paid and w.tx_hash == tx_hash:
                return Decided(w, False)
            if w.status is not WithdrawalStatus.pending:
                raise Conflict("not_pending")
            w.status = WithdrawalStatus.paid
            w.tx_hash = tx_hash
            w.processed_by = actor
            w.processed_at = datetime_now()
            await self.db.audit(
                actor, "withdrawal.pay", f"withdrawal:{w.id}", {"amount": str(w.amount)}
            )
        return Decided(w, True)

    async def reject(self, actor: int, withdrawal_id: int, reason: str) -> Decided:
        """pending -> rejected and the money goes back to the executor, in one transaction under
        the lock of the withdrawal row. A second call finds it rejected and does nothing; the
        ledger ref makes a second posting impossible anyway."""
        reason = reason.strip()
        if not 1 <= len(reason) <= 500:
            raise InvalidField("reason", "1 to 500 characters")
        async with self.tx():
            w = await self.need(Withdrawal, withdrawal_id)
            if w.status is WithdrawalStatus.rejected:
                return Decided(w, False)
            if w.status is not WithdrawalStatus.pending:
                raise Conflict("not_pending")
            w.status = WithdrawalStatus.rejected
            w.reject_reason = reason
            w.processed_by = actor
            w.processed_at = datetime_now()
            await self.ledger.post(
                w.executor_id,
                LedgerAccount.executor_available,
                w.amount,
                LedgerKind.withdrawal,
                ref=f"withdrawal:{w.id}:reject",
            )
            await self.db.audit(
                actor,
                "withdrawal.reject",
                f"withdrawal:{w.id}",
                {"amount": str(w.amount), "reason": reason},
            )
        return Decided(w, True)
