from dataclasses import dataclass

from app.application.interactors.base import BaseInteractor
from app.application.interactors.catalog import PAGE_SIZE
from app.application.ports.repositories.orders import OrdersGateway
from app.domain.order import Order


@dataclass(frozen=True)
class OrdersInteractor(BaseInteractor):
    gateway: OrdersGateway

    async def list_orders(self, user_id: int, page: int) -> tuple[list[Order], int, int]:
        """Returns (orders on the page, total orders, corrected page)."""
        total = await self.gateway.count_for_user(user_id)
        pages = max(1, -(-total // PAGE_SIZE))
        page = min(max(page, 0), pages - 1)
        return await self.gateway.list_for_user(user_id, page * PAGE_SIZE, PAGE_SIZE), total, page

    async def get(self, user_id: int, order_id: int) -> Order | None:
        return await self.gateway.get_for_user(user_id, order_id)
