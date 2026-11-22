from datetime import datetime
from typing import Protocol

from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent


class OrdersGateway(Protocol):
    async def add(self, order: Order) -> None:
        """Insert and flush, so `order.id` is available."""

    async def add_event(self, event: OrderEvent) -> None: ...

    async def get_for_user(self, user_id: int, order_id: int) -> Order | None: ...

    async def list_for_user(self, user_id: int, offset: int, limit: int) -> list[Order]: ...

    async def count_for_user(self, user_id: int) -> int: ...

    async def active_for_user(self, user_id: int) -> list[Order]:
        """Orders still on their way to the buyer: paid, in_queue, assigned, ready."""

    async def events(self, order_id: int) -> list[OrderEvent]:
        """Oldest first."""

    async def last_for_product(self, user_id: int, product_id: int) -> Order | None:
        """The user's newest order of this product, whatever its status."""

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

    async def list_for_executor(
        self, executor_id: int, offset: int, limit: int
    ) -> list[Order]: ...

    async def count_for_executor(self, executor_id: int) -> int: ...

    async def hold_due_ids(self, now: datetime) -> list[int]:
        """Completed orders past their hold with an accrual that was not released yet."""

    async def review_due_ids(self, now: datetime) -> list[int]:
        """Completed orders whose rating request is due and was not sent yet."""

    async def queue(self, limit: int) -> list[Order]:
        """Unassigned `in_queue` orders, oldest first."""

    async def list_by_status(self, status: OrderStatus, limit: int) -> list[Order]:
        """Newest first."""
