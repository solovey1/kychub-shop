from decimal import Decimal
from typing import Protocol

from app.domain.enums.ledger import LedgerAccount
from app.domain.ledger import LedgerEntry


class LedgerGateway(Protocol):
    async def lock_user(self, user_id: int) -> None: ...

    async def balance(self, user_id: int, account: LedgerAccount) -> Decimal: ...

    async def add(self, entry: LedgerEntry) -> None: ...
