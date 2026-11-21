from typing import Protocol

from app.domain.audit import AuditLog
from app.domain.ledger import LedgerEntry, Payment


class BalanceGateway(Protocol):
    async def history(self, user_id: int, limit: int) -> list[LedgerEntry]: ...

    async def add_payment(self, payment: Payment) -> None:
        """Insert and flush, so `payment.id` is available."""

    async def add_audit(self, record: AuditLog) -> None: ...
