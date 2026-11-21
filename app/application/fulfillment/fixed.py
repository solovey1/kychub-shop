from dataclasses import dataclass
from typing import Any, ClassVar

from app.application.fulfillment.base import move
from app.application.ports.repositories.orders import OrdersGateway
from app.domain.catalog import Product
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.utils.time import datetime_now


@dataclass(frozen=True)
class FixedFulfillment:
    code: ClassVar[str] = "fixed"
    orders: OrdersGateway

    def validate_config(self, config: dict[str, Any]) -> None:
        if not isinstance(config.get("text"), str) or not config["text"]:
            raise ValueError("fixed fulfillment requires a non-empty 'text'")

    async def on_paid(self, order: Order, product: Product) -> None:
        order.result = {"text": product.fulfillment_config["text"]}
        order.completed_at = datetime_now()
        await move(self.orders, order, OrderStatus.completed)
