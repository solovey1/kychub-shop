"""Cancel by agreement: the buyer of an assigned order asks, the executor agrees or not.

Same shape as the extension request in `deadlines.py`: events on the order, one open request at
a time, at most two per order, a new assignment makes an open request nobody's. An executor who
stays silent for an hour agrees (job `agree_due`). Everything runs under the order lock, so the
executor's answer, the timer and a dispute opened meanwhile give exactly one outcome and the
refund (`refund_locked`, idempotent in the ledger) is posted once."""

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from app.application.errors.shop import Conflict, OrderUnavailable
from app.application.interactors.base import BaseInteractor
from app.application.interactors.deadlines import NEW_ASSIGNMENT
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.interactors.payouts import Refunded
from app.application.ports.repositories.disputes import DisputesGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.utils.time import datetime_now

logger: Final = logging.getLogger(__name__)

MAX_CANCEL_REQUESTS: Final = 2
AGREE_AFTER: Final = timedelta(hours=1)

CANCEL_EVENTS: Final = ("cancel_requested", "cancel_agreed", "cancel_declined", *NEW_ASSIGNMENT)


@dataclass(frozen=True)
class CancelPending:
    request_id: int
    at: datetime  # when it was asked: the executor has until `at + AGREE_AFTER`

    @property
    def agrees_at(self) -> datetime:
        return self.at + AGREE_AFTER


@dataclass(frozen=True)
class CancelState:
    pending: CancelPending | None
    requests: int  # all requests of the order, answered or not

    @property
    def can_request(self) -> bool:
        return self.pending is None and self.requests < MAX_CANCEL_REQUESTS


def cancel_state(events: list[OrderEvent]) -> CancelState:
    pending: CancelPending | None = None
    requests = 0
    for event in events:
        rid = event.payload.get("request_id")
        if event.type == "cancel_requested":
            requests += 1
            pending = CancelPending(int(str(rid)), event.created_at)
        elif event.type in ("cancel_agreed", "cancel_declined"):
            if pending is not None and pending.request_id == rid:
                pending = None
        elif event.type in NEW_ASSIGNMENT:
            pending = None
    return CancelState(pending, requests)


@dataclass(frozen=True)
class CancelAsk:
    order: Order
    request_id: int


@dataclass(frozen=True)
class CancelAnswer:
    order: Order
    agreed: bool
    refund: Refunded | None = None  # when agreed
    by_timer: bool = False


@dataclass(frozen=True)
class CancelRequestInteractor(BaseInteractor):
    uow: UnitOfWork
    orders: OrdersGateway
    disputes: DisputesGateway
    review: OrderReviewInteractor

    async def state(self, order_id: int) -> CancelState:
        return cancel_state(await self.orders.events(order_id))

    async def request(self, buyer_id: int, order_id: int) -> CancelAsk:
        """The buyer of an assigned order asks to cancel. Conflict: `dispute_open`,
        `cancel_pending`, `cancel_limit`."""
        try:
            order = await self.orders.get_for_update(order_id)
            if (
                order is None
                or order.user_id != buyer_id
                or order.status is not OrderStatus.assigned
            ):
                raise OrderUnavailable(order_id)
            if await self.disputes.open_for_order(order_id) is not None:
                raise Conflict("dispute_open")
            state = cancel_state(await self.orders.events(order_id))
            if state.pending is not None:
                raise Conflict("cancel_pending")
            if state.requests >= MAX_CANCEL_REQUESTS:
                raise Conflict("cancel_limit")
            request_id = state.requests + 1
            await self.orders.add_event(
                OrderEvent(
                    order_id=order_id,
                    actor_id=buyer_id,
                    type="cancel_requested",
                    payload={"request_id": request_id},
                )
            )
            await self.uow.commit()
            return CancelAsk(order, request_id)
        except BaseException:
            await self.uow.rollback()
            raise

    async def answer(
        self, executor_id: int, order_id: int, request_id: int, agree: bool
    ) -> CancelAnswer:
        """The executor's answer. Conflict `cancel_stale`: the request is gone (the order was
        handed in, went overdue, a dispute opened, the timer agreed first): nothing changed."""
        try:
            order = await self.orders.get_for_update(order_id)
            if order is None or order.executor_id != executor_id:
                raise OrderUnavailable(order_id)
            pending = cancel_state(await self.orders.events(order_id)).pending
            if (
                order.status is not OrderStatus.assigned
                or pending is None
                or pending.request_id != request_id
                or await self.disputes.open_for_order(order_id) is not None
            ):
                raise Conflict("cancel_stale")
            answer = await self._settle(order, pending, agree, executor_id, by_timer=False)
            await self.uow.commit()
            return answer
        except BaseException:
            await self.uow.rollback()
            raise

    async def agree_due(self) -> list[CancelAnswer]:
        """Requests the executor left unanswered for an hour count as agreed. One transaction
        per order; a broken one does not stop the rest."""
        done: list[CancelAnswer] = []
        for order_id in await self.orders.cancel_request_ids(datetime_now() - AGREE_AFTER):
            try:
                order = await self.orders.get_for_update(order_id)
                pending = (
                    cancel_state(await self.orders.events(order_id)).pending
                    if order is not None
                    else None
                )
                if (
                    order is None
                    or order.status is not OrderStatus.assigned  # answered, handed in, overdue
                    or pending is None
                    or pending.agrees_at > datetime_now()
                    or await self.disputes.open_for_order(order_id) is not None
                ):
                    await self.uow.rollback()
                    continue
                done.append(await self._settle(order, pending, True, None, by_timer=True))
                await self.uow.commit()
            except Exception:
                await self.uow.rollback()
                logger.exception("cancelling order %s by agreement failed", order_id)
        return done

    async def _settle(
        self,
        order: Order,
        pending: CancelPending,
        agree: bool,
        actor_id: int | None,
        *,
        by_timer: bool,
    ) -> CancelAnswer:
        """Under the order lock, commits nothing."""
        payload = {"request_id": pending.request_id, "by_timer": by_timer}
        if not agree:
            await self.orders.add_event(
                OrderEvent(
                    order_id=order.id, actor_id=actor_id, type="cancel_declined", payload=payload
                )
            )
            return CancelAnswer(order, False)
        refund = await self.review.refund_locked(order, actor_id, "cancel_agreed")
        await self.orders.add_event(
            OrderEvent(order_id=order.id, actor_id=actor_id, type="cancel_agreed", payload=payload)
        )
        return CancelAnswer(order, True, refund, by_timer)
