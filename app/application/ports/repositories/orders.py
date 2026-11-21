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
