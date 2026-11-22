from dataclasses import dataclass
from decimal import Decimal
from typing import Optional

from app.application.errors.base import InsufficientFunds, LedgerConflict
from app.application.interactors.base import BaseInteractor
from app.application.ports.repositories.ledger import LedgerGateway
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.ledger import LedgerEntry
from app.domain.money import money

_NON_NEGATIVE = {LedgerAccount.main, LedgerAccount.executor_available, LedgerAccount.buyer_hold}


@dataclass(frozen=True)
class LedgerService(BaseInteractor):
    gateway: LedgerGateway

    async def post(
        self,
        user_id: int,
        account: LedgerAccount,
        amount: Decimal,
        kind: LedgerKind,
        *,
        order_id: Optional[int] = None,
        ref: Optional[str] = None,
    ) -> LedgerEntry:
        """Append under a user row lock. Does NOT commit: the caller owns the transaction."""
        amount = money(amount)
        await self.gateway.lock_user(user_id)
        if ref is not None and (
            existing := await self.gateway.get_by_ref(user_id, account, kind, ref)
        ):
            if existing.amount != amount or existing.order_id != order_id:
                raise LedgerConflict(f"ref {ref!r}: got {amount}, stored {existing.amount}")
            return existing  # idempotent replay
        balance_after = await self.gateway.balance(user_id, account) + amount
        if account in _NON_NEGATIVE and balance_after < 0:
            raise InsufficientFunds(f"user {user_id}: {account} balance would be {balance_after}")
        entry = LedgerEntry(
            user_id=user_id,
            account=account,
            amount=amount,
            kind=kind,
            order_id=order_id,
            ref=ref,
            balance_after=balance_after,
        )
        await self.gateway.add(entry)
        return entry
