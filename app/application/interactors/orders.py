from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from app.application.errors.shop import OrderUnavailable
from app.application.fulfillment.base import move
from app.application.interactors.auto_confirm import confirm_deadline, confirm_hours
from app.application.interactors.base import BaseInteractor
from app.application.interactors.catalog import PAGE_SIZE, VariantView
from app.application.interactors.deadlines import Pending, extension_state
from app.application.interactors.ledger import LedgerService
from app.application.interactors.payouts import Refunded, open_hold, refund_buyer
from app.application.ports.repositories.disputes import DisputesGateway
from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.ledger import LedgerGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.settings import SettingsGateway
from app.application.ports.uow import UnitOfWork
from app.domain.catalog import Product
from app.domain.dispute import Dispute
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent

REORDER_LIMIT = 3


@dataclass(frozen=True)
class OrdersInteractor(BaseInteractor):
    gateway: OrdersGateway
    uow: UnitOfWork
    ledger: LedgerService
    ledger_gateway: LedgerGateway
    executors: ExecutorsGateway
    settings: SettingsGateway
    disputes: DisputesGateway

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

    async def reorderable(self, user_id: int) -> list[tuple[VariantView, Product]]:
        rows = await self.gateway.reorderable(user_id, REORDER_LIMIT)
        return [(VariantView(v, True, country), p) for v, p, country in rows]

    async def can_reorder(self, variant_id: int) -> bool:
        return await self.gateway.variant_orderable(variant_id)

    async def reserved(self, order: Order) -> Decimal:
        """What the buyer has reserved in this order: 0 once it is done or closed."""
        if await open_hold(self.ledger_gateway, order):
            return order.price - order.discount
        return Decimal(0)

    async def pending_extension(self, order: Order) -> Pending | None:
        """The executor's open request for more time, what the buyer has to answer."""
        if order.status is not OrderStatus.assigned:
            return None
        return extension_state(await self.gateway.events(order.id)).pending

    async def dispute(self, order: Order) -> Dispute | None:
        return await self.disputes.open_for_order(order.id)

    async def confirm_at(self, order: Order) -> datetime | None:
        """When a `ready` order confirms itself if the buyer says nothing (None: not ready, or
        a dispute has stopped the clock)."""
        if await self.dispute(order) is not None:
            return None
        return confirm_deadline(order, await confirm_hours(self.settings))

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
            amount = await refund_buyer(self.ledger, self.ledger_gateway, order)
            await self.uow.commit()
            return Refunded(order.id, user_id, None, amount, OrderStatus.in_queue)
        except BaseException:
            await self.uow.rollback()
            raise
