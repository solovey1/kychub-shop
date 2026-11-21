from typing import Protocol

from app.domain.audit import AuditLog
from app.domain.ledger import LedgerEntry


class BalanceGateway(Protocol):
    async def history(self, user_id: int, limit: int) -> list[LedgerEntry]: ...

    async def add_audit(self, record: AuditLog) -> None: ...
