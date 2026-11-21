from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from app.application.cards import OrderCard
from app.application.errors.shop import OrderUnavailable
from app.application.fulfillment.base import move
from app.application.interactors.base import BaseInteractor
from app.application.interactors.cards import CardBuilder, earning_for, load_context, percent_for
from app.application.interactors.ledger import LedgerService
from app.application.interactors.payouts import (
    Refunded,
    order_ref,
    refund_buyer,
    reverse_earning,
)
from app.application.ports.repositories.catalog import CatalogGateway
from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.ledger import LedgerGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.settings import SettingsGateway
from app.application.ports.uow import UnitOfWork
from app.application.settings_keys import (
    DEFAULT_HOLD_DAYS,
    DEFAULT_REVIEW_DELAY_HOURS,
    HOLD_DAYS,
    REVIEW_DELAY_HOURS,
)
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.utils.time import datetime_now

_REFUNDABLE: Final = (
    OrderStatus.paid,
    OrderStatus.in_queue,
    OrderStatus.assigned,
    OrderStatus.ready,
    OrderStatus.completed,
)


@dataclass(frozen=True)
class ReviewView:
    order: Order
    card: OrderCard
    text: str
    files: list[str]


@dataclass(frozen=True)
class OrderReviewInteractor(BaseInteractor):
    """For admins and managers: the role is checked by the handler filter."""

    uow: UnitOfWork
    orders: OrdersGateway
    catalog: CatalogGateway
    executors: ExecutorsGateway
    ledger: LedgerService
    ledger_gateway: LedgerGateway
    settings: SettingsGateway
    cards: CardBuilder

    async def get(self, order_id: int) -> ReviewView | None:
        order = await self.orders.get(order_id)
        if order is None:
            return None
        card = await self.cards.build(order, order.executor_id, hide_private=False)
        result = order.result or {}
        return ReviewView(order, card, str(result.get("text", "")), list(result.get("files", [])))

    async def list_by_status(self, status: OrderStatus, limit: int) -> list[Order]:
        return await self.orders.list_by_status(status, limit)

    async def confirm(self, actor_id: int, order_id: int) -> Order:
        """ready -> completed; the executor share goes to the hold."""
        try:
            order = await self._locked(order_id, OrderStatus.ready)
            if order.executor_id is None:
                raise OrderUnavailable(order_id)
            ctx = await load_context(self.catalog, order)
            profile = await self.executors.get_profile(order.executor_id)
            earning = earning_for(order, percent_for(profile, ctx.service if ctx else None))
            now = datetime_now()
            hold_days = int(await self.settings.get(HOLD_DAYS, DEFAULT_HOLD_DAYS))
            delay = int(await self.settings.get(REVIEW_DELAY_HOURS, DEFAULT_REVIEW_DELAY_HOURS))
            order.completed_at = now
            order.hold_until = now + timedelta(days=hold_days)
            order.review_due_at = now + timedelta(hours=delay)
            await move(self.orders, order, OrderStatus.completed, actor_id)
            if earning > 0:
                await self.ledger.post(
                    order.executor_id,
                    LedgerAccount.executor_hold,
                    earning,
                    LedgerKind.executor_earning,
                    order_id=order.id,
                    ref=order_ref(order),
                )
            await self.uow.commit()
            return order
        except BaseException:
            await self.uow.rollback()
            raise

    async def send_back(self, actor_id: int, order_id: int, comment: str) -> Order:
        """ready -> assigned with a fresh deadline and the reviewer comment."""
        try:
            order = await self._locked(order_id, OrderStatus.ready)
            ctx = await load_context(self.catalog, order)
            minutes = ctx.service.deadline_minutes if ctx and ctx.service else 0
            order.ready_at = None
            order.deadline_at = datetime_now() + timedelta(minutes=minutes)
            await move(self.orders, order, OrderStatus.assigned, actor_id)
            await self.orders.add_event(
                OrderEvent(
                    order_id=order.id,
                    actor_id=actor_id,
                    type="sent_back",
                    payload={"comment": comment},
                )
            )
            await self.uow.commit()
            return order
        except BaseException:
            await self.uow.rollback()
            raise

    async def fail_and_refund(self, actor_id: int, order_id: int, reason: str) -> Refunded:
        """paid | in_queue | assigned | ready -> failed -> refunded; completed -> refunded."""
        try:
            order = await self.orders.get_for_update(order_id)
            if order is None or order.status not in _REFUNDABLE:
                raise OrderUnavailable(order_id)
            was = order.status
            if was is not OrderStatus.completed:
                await move(self.orders, order, OrderStatus.failed, actor_id)
            await move(self.orders, order, OrderStatus.refunded, actor_id)
            amount = await refund_buyer(self.ledger, order)
            if was is OrderStatus.completed:
                # while the hold is on, the order lock also fences off the hold release job
                await reverse_earning(self.ledger, self.ledger_gateway, order)
            await self.orders.add_event(
                OrderEvent(
                    order_id=order.id,
                    actor_id=actor_id,
                    type="refund",
                    payload={"reason": reason, "amount": str(amount), "was": str(was)},
                )
            )
            await self.uow.commit()
            return Refunded(order.id, order.user_id, order.executor_id, amount, was)
        except BaseException:
            await self.uow.rollback()
            raise

    async def _locked(self, order_id: int, status: OrderStatus) -> Order:
        order = await self.orders.get_for_update(order_id)
        if order is None or order.status is not status:
            raise OrderUnavailable(order_id)
        return order
