from decimal import Decimal
from typing import Protocol

from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.ledger import LedgerEntry


class LedgerGateway(Protocol):
    async def lock_user(self, user_id: int) -> None: ...

    async def balance(self, user_id: int, account: LedgerAccount) -> Decimal: ...

    async def get_by_ref(self, kind: LedgerKind, ref: str) -> LedgerEntry | None: ...

    async def add(self, entry: LedgerEntry) -> None: ...
