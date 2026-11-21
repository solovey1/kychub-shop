from dataclasses import dataclass
from typing import Any, ClassVar

from app.application.fulfillment.base import move
from app.application.ports.repositories.orders import OrdersGateway
from app.domain.catalog import Product
from app.domain.enums.order import OrderStatus
from app.domain.order import Order


@dataclass(frozen=True)
class ExecutorFulfillment:
    code: ClassVar[str] = "executor"
    orders: OrdersGateway

    def validate_config(self, config: dict[str, Any]) -> None:
        return None

    async def on_paid(self, order: Order, product: Product) -> None:
        # queueing and assignment are done by the executor phase
        await move(self.orders, order, OrderStatus.in_queue)
