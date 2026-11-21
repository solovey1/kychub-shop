from dataclasses import dataclass
from typing import Any, ClassVar

from app.application.errors.shop import OutOfStock
from app.application.fulfillment.base import move
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.stock import StockGateway
from app.domain.catalog import Product
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.utils.time import datetime_now


@dataclass(frozen=True)
class StockFulfillment:
    code: ClassVar[str] = "stock"
    orders: OrdersGateway
    stock: StockGateway

    def validate_config(self, config: dict[str, Any]) -> None:
        return None

    async def on_paid(self, order: Order, product: Product) -> None:
        unit = await self.stock.take(order.variant_id, order.id)
        if unit is None:
            raise OutOfStock(f"variant {order.variant_id}")
        order.result = {"text": unit.payload}
        order.completed_at = datetime_now()
        await move(self.orders, order, OrderStatus.completed)
