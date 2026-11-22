from dataclasses import dataclass
from typing import Final

from app.application.cards import OrderCard
from app.application.errors.shop import OrderUnavailable
from app.application.interactors.admin.base import AdminInteractor
from app.application.interactors.cards import CardBuilder, load_context
from app.application.ports.repositories.catalog import CatalogGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.domain.enums.order import OrderStatus
from app.domain.executor import ExecutorProfile
from app.domain.ledger import LedgerEntry
from app.domain.order import Order, OrderEvent

PAGE_SIZE: Final = 30


@dataclass(frozen=True)
class OrderDetail:
    order: Order
    card: OrderCard
    buyer_name: str
    executor_alias: str | None
    events: list[OrderEvent]
    entries: list[LedgerEntry]
    actions: list[str]


def actions_for(status: OrderStatus) -> list[str]:
    """What staff may do with an order in this status (the endpoints check it again)."""
    out = {
        OrderStatus.in_queue: ["assign", "refund", "cancel"],
        OrderStatus.assigned: ["assign", "refund", "cancel"],
        OrderStatus.ready: ["confirm", "send_back", "refund"],
        OrderStatus.paid: ["refund"],
        OrderStatus.completed: ["refund"],
    }
    return out.get(status, [])


@dataclass(frozen=True)
class OrdersAdminInteractor(AdminInteractor):
    orders: OrdersGateway
    catalog: CatalogGateway
    cards: CardBuilder

    async def listing(
        self,
        status: OrderStatus | None,
        product_id: int | None,
        user_id: int | None,
        executor_id: int | None,
        page: int,
    ) -> tuple[list[Order], dict[int, str], int]:
        """The page, the executor aliases of its orders, the total."""
        items, total = await self.db.orders_filtered(
            status, product_id, user_id, executor_id, page * PAGE_SIZE, PAGE_SIZE
        )
        ids = [o.executor_id for o in items if o.executor_id is not None]
        return items, await self.db.executor_aliases(ids), total

    async def detail(self, order_id: int) -> OrderDetail:
        order = await self.orders.get(order_id)
        if order is None:
            raise OrderUnavailable(order_id)
        names = await self.db.user_names([order.user_id])
        aliases = await self.db.executor_aliases([order.executor_id] if order.executor_id else [])
        return OrderDetail(
            order,
            await self.cards.build(order, order.executor_id, hide_private=False),
            names.get(order.user_id, ""),
            aliases.get(order.executor_id) if order.executor_id else None,
            await self.orders.events(order_id),
            await self.db.entries_for_order(order_id),
            actions_for(order.status),
        )

    async def assignable(self, order_id: int) -> list[tuple[ExecutorProfile, int]]:
        order = await self.orders.get(order_id)
        if order is None or order.status not in (OrderStatus.in_queue, OrderStatus.assigned):
            raise OrderUnavailable(order_id)
        ctx = await load_context(self.catalog, order)
        if ctx is None or ctx.service is None:
            return []
        return await self.db.assignable(ctx.service.id, ctx.variant.country_code)
