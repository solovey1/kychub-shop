from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from app.application.cards import OrderCard
from app.application.errors.shop import Conflict, OrderUnavailable
from app.application.fulfillment.base import move
from app.application.interactors.base import BaseInteractor
from app.application.interactors.cards import CardBuilder, earning_for, load_context, percent_for
from app.application.interactors.dispute_state import close_dispute
from app.application.interactors.ledger import LedgerService
from app.application.interactors.payouts import (
    Refunded,
    capture_buyer,
    order_ref,
    refund_buyer,
    reverse_earning,
)
from app.application.ports.repositories.catalog import CatalogGateway
from app.application.ports.repositories.disputes import DisputesGateway
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
from app.domain.enums.dispute import DisputeResolution
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
    executor_alias: str | None


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
    disputes: DisputesGateway

    async def get(self, order_id: int) -> ReviewView | None:
        order = await self.orders.get(order_id)
        if order is None:
            return None
        card = await self.cards.build(order, order.executor_id, hide_private=False)
        result = order.result or {}
        profile = (
            await self.executors.get_profile(order.executor_id) if order.executor_id else None
        )
        return ReviewView(
            order,
            card,
            str(result.get("text", "")),
            list(result.get("files", [])),
            profile.alias if profile else None,
        )

    async def list_by_status(self, status: OrderStatus, limit: int) -> list[Order]:
        return await self.orders.list_by_status(status, limit)

    async def confirm(self, actor_id: int, order_id: int) -> Order:
        """Staff: ready -> completed; the executor share goes to the hold."""
        return await self._confirm(actor_id, order_id, buyer_id=None)

    async def confirm_by_buyer(self, buyer_id: int, order_id: int) -> Order:
        """The buyer of this order says everything is fine (anyone else: OrderUnavailable)."""
        return await self._confirm(buyer_id, order_id, buyer_id=buyer_id)

    async def _confirm(self, actor_id: int, order_id: int, buyer_id: int | None) -> Order:
        try:
            order = await self._locked(order_id, OrderStatus.ready)
            if buyer_id is not None and order.user_id != buyer_id:
                raise OrderUnavailable(order_id)
            if buyer_id is not None and await self.disputes.open_for_order(order_id) is not None:
                raise Conflict("dispute_open")  # support decides, not «everything is fine»
            await self.complete_locked(order, actor_id)
            if buyer_id is not None:
                # he is looking at the order now: ask for the rating at once; the event (same one
                # the timed job writes) keeps the job from asking a second time
                await self.orders.add_event(OrderEvent(order_id=order.id, type="review_requested"))
                order.review_due_at = None
            await self.uow.commit()
            return order
        except BaseException:
            await self.uow.rollback()
            raise

    async def complete_locked(self, order: Order, actor_id: int | None) -> None:
        """ready -> completed under the order lock, commits nothing. Every way of completing an
        order (buyer, staff, the auto-confirm job) comes through here: a second one finds the order
        no longer `ready` and never reaches the ledger, and `capture_buyer` posts once per order
        anyway. `actor_id` None: the system."""
        if order.status is not OrderStatus.ready or order.executor_id is None:
            raise OrderUnavailable(order.id)
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
        await capture_buyer(self.ledger, self.ledger_gateway, order)
        if earning > 0:
            await self.ledger.post(
                order.executor_id,
                LedgerAccount.executor_hold,
                earning,
                LedgerKind.executor_earning,
                order_id=order.id,
                ref=order_ref(order),
            )
        await close_dispute(
            self.disputes, self.orders, order, DisputeResolution.completed, actor_id
        )

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
            await close_dispute(
                self.disputes, self.orders, order, DisputeResolution.sent_back, actor_id
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
            if order is None:
                raise OrderUnavailable(order_id)
            refund = await self.refund_locked(order, actor_id, reason)
            await self.uow.commit()
            return refund
        except BaseException:
            await self.uow.rollback()
            raise

    async def refund_locked(self, order: Order, actor_id: int | None, reason: str) -> Refunded:
        """The body of `fail_and_refund` under the order lock, commits nothing (the dispute job
        uses it too). A second call finds the order already refunded and stops."""
        if order.status not in _REFUNDABLE:
            raise OrderUnavailable(order.id)
        was = order.status
        if was is not OrderStatus.completed:
            await move(self.orders, order, OrderStatus.failed, actor_id)
        await move(self.orders, order, OrderStatus.refunded, actor_id)
        amount = await refund_buyer(self.ledger, self.ledger_gateway, order)
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
        await close_dispute(
            self.disputes, self.orders, order, DisputeResolution.refunded, actor_id
        )
        return Refunded(order.id, order.user_id, order.executor_id, amount, was)

    async def _locked(self, order_id: int, status: OrderStatus) -> Order:
        order = await self.orders.get_for_update(order_id)
        if order is None or order.status is not status:
            raise OrderUnavailable(order_id)
        return order
