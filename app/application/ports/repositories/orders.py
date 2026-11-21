from datetime import datetime
from typing import Protocol

from app.domain.order import Order, OrderEvent


class OrdersGateway(Protocol):
    async def add(self, order: Order) -> None:
        """Insert and flush, so `order.id` is available."""

    async def add_event(self, event: OrderEvent) -> None: ...

    async def get_for_user(self, user_id: int, order_id: int) -> Order | None: ...

    async def list_for_user(self, user_id: int, offset: int, limit: int) -> list[Order]: ...

    async def count_for_user(self, user_id: int) -> int: ...

    async def find_by_token(self, user_id: int, token: str) -> Order | None: ...

    async def get(self, order_id: int) -> Order | None: ...

    async def get_for_update(self, order_id: int) -> Order | None:
        """`SELECT ... FOR UPDATE` with fresh column values: held until the transaction ends."""

    async def has_event(self, order_id: int, event_type: str) -> bool: ...

    async def excluded_executor_ids(self, order_id: int) -> set[int]:
        """Executors who refused the order or let its deadline pass."""

    async def overdue_ids(self, now: datetime) -> list[int]:
        """`assigned` orders whose deadline has passed."""

    async def stale_ids(self, cutoff: datetime) -> list[int]:
        """Unassigned `in_queue` orders with no dispatch attempt since `cutoff`."""
