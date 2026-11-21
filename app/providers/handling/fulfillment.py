from dishka import Provider, Scope, provide

from app.application.fulfillment import (
    ExecutorFulfillment,
    FixedFulfillment,
    FulfillmentRegistry,
    ManualFulfillment,
    StockFulfillment,
)
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.stock import StockGateway


class FulfillmentProvider(Provider):
    scope = Scope.REQUEST

    @provide
    def provide_registry(self, orders: OrdersGateway, stock: StockGateway) -> FulfillmentRegistry:
        handlers = (
            StockFulfillment(orders, stock),
            FixedFulfillment(orders),
            ManualFulfillment(),
            ExecutorFulfillment(orders),
        )
        return FulfillmentRegistry({h.code: h for h in handlers})
