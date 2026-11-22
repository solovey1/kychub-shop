from dataclasses import dataclass

from app.application.errors.shop import OrderUnavailable
from app.application.fulfillment.base import move
from app.application.interactors.base import BaseInteractor
from app.application.interactors.catalog import PAGE_SIZE
from app.application.interactors.ledger import LedgerService
from app.application.interactors.payouts import Refunded, refund_buyer
from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent


@dataclass(frozen=True)
class OrdersInteractor(BaseInteractor):
    gateway: OrdersGateway
    uow: UnitOfWork
    ledger: LedgerService
    executors: ExecutorsGateway

    async def list_orders(self, user_id: int, page: int) -> tuple[list[Order], int, int]:
        """Returns (orders on the page, total orders, corrected page)."""
        total = await self.gateway.count_for_user(user_id)
        pages = max(1, -(-total // PAGE_SIZE))
        page = min(max(page, 0), pages - 1)
        return await self.gateway.list_for_user(user_id, page * PAGE_SIZE, PAGE_SIZE), total, page

    async def get(self, user_id: int, order_id: int) -> Order | None:
        return await self.gateway.get_for_user(user_id, order_id)

    async def active(self, user_id: int) -> list[Order]:
        return await self.gateway.active_for_user(user_id)

    async def events(self, order_id: int) -> list[OrderEvent]:
        return await self.gateway.events(order_id)

    async def executor_alias(self, order: Order) -> str | None:
        """The only thing a buyer may know about the executor."""
        if order.executor_id is None:
            return None
        profile = await self.executors.get_profile(order.executor_id)
        return profile.alias if profile else None

    async def cancel(self, user_id: int, order_id: int) -> Refunded:
        """Only an order nobody has taken yet; the buyer gets everything back."""
        try:
            order = await self.gateway.get_for_update(order_id)
            if (
                order is None
                or order.user_id != user_id
                or order.status is not OrderStatus.in_queue
            ):
                raise OrderUnavailable(order_id)
            await move(self.gateway, order, OrderStatus.cancelled, user_id)
            amount = await refund_buyer(self.ledger, order)
            await self.uow.commit()
            return Refunded(order.id, user_id, None, amount, OrderStatus.in_queue)
        except BaseException:
            await self.uow.rollback()
            raise
