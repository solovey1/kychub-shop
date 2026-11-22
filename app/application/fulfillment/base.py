from typing import Any, ClassVar, NewType, Protocol

from app.application.ports.repositories.orders import OrdersGateway
from app.domain.catalog import Product
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.domain.order_status import ensure_transition


class FulfillmentHandler(Protocol):
    code: ClassVar[str]

    def validate_config(self, config: dict[str, Any]) -> None: ...

    async def on_paid(self, order: Order, product: Product) -> None:
        """Runs inside the purchase transaction. May raise OutOfStock. Updates status/result."""


FulfillmentRegistry = NewType("FulfillmentRegistry", dict[str, FulfillmentHandler])


async def move(
    orders: OrdersGateway, order: Order, new: OrderStatus, actor_id: int | None = None
) -> None:
    """Status change with a validated transition and an OrderEvent."""
    ensure_transition(order.status, new)
    old = order.status
    order.status = new
    order.paused_at = None  # a pause belongs to one stay in `assigned`
    await orders.add_event(
        OrderEvent(
            order_id=order.id,
            actor_id=actor_id,
            type="status",
            payload={"from": str(old), "to": str(new)},
        )
    )
