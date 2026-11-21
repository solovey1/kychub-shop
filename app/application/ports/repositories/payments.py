from datetime import timedelta
from typing import Protocol

from app.domain.ledger import Payment


class PaymentsGateway(Protocol):
    async def add(self, payment: Payment) -> None:
        """Insert and flush, so `payment.id` is available."""

    async def get(self, payment_id: int) -> Payment | None: ...

    async def get_for_update(self, payment_id: int) -> Payment | None:
        """`SELECT ... FOR UPDATE`: held until the transaction ends."""

    async def pending(self, max_age: timedelta) -> list[Payment]:
        """Unpaid payments younger than `max_age`, oldest first."""

    async def unfulfilled_success(self) -> list[Payment]:
        """Successful payments without a top-up ledger entry."""
