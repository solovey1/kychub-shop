import logging
import math
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final, Literal

from app.application.errors.shop import Conflict, DeadlineExpired, InvalidInput, OrderUnavailable
from app.application.interactors.base import BaseInteractor
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.utils.time import datetime_now

logger: Final = logging.getLogger(__name__)

EXTENSION_MINUTES: Final = (15, 30, 60, 120, 360, 1440)
MAX_REQUESTS: Final = 3
SOON_MINUTES: Final = 15
HALF_MIN_TOTAL_MINUTES: Final = 60

# the events after which a request that is still open belongs to nobody any more
_NEW_ASSIGNMENT: Final = ("assigned", "reassigned", "overdue", "refused", "sent_back")


@dataclass(frozen=True)
class Pending:
    request_id: int
    minutes: int


@dataclass(frozen=True)
class ExtensionState:
    pending: Pending | None
    requests: int  # all requests of the order, answered or not

    @property
    def can_request(self) -> bool:
        return self.pending is None and self.requests < MAX_REQUESTS


def extension_state(events: list[OrderEvent]) -> ExtensionState:
    """Pending = the last `extension_requested` nobody answered, within the current assignment."""
    pending: Pending | None = None
    requests = 0
    for event in events:
        rid = event.payload.get("request_id")
        if event.type == "extension_requested":
            requests += 1
            pending = Pending(int(str(rid)), int(str(event.payload["minutes"])))
        elif event.type in ("extended", "extension_declined"):
            if pending is not None and pending.request_id == rid:
                pending = None
        elif event.type in _NEW_ASSIGNMENT:
            pending = None
    return ExtensionState(pending, requests)


def extended_deadline(order: Order, minutes: int, now: datetime) -> datetime:
    assert order.deadline_at is not None
    return max(order.deadline_at, now) + timedelta(minutes=minutes)


@dataclass(frozen=True)
class ExtensionAsk:
    order: Order
    request_id: int
    minutes: int


@dataclass(frozen=True)
class ExtensionAnswer:
    order: Order
    approved: bool
    minutes: int


@dataclass(frozen=True)
class ExtensionInteractor(BaseInteractor):
    uow: UnitOfWork
    orders: OrdersGateway

    async def state(self, order_id: int) -> ExtensionState:
        return extension_state(await self.orders.events(order_id))

    async def request(self, executor_id: int, order_id: int, minutes: int) -> ExtensionAsk:
        """The executor of an assigned order asks for more time. Conflict: a request is already
        waiting, or the limit is spent."""
        if minutes not in EXTENSION_MINUTES:
            raise InvalidInput(f"minutes {minutes}")
        try:
            order = await self.orders.get_for_update(order_id)
            if (
                order is None
                or order.status is not OrderStatus.assigned
                or order.executor_id != executor_id
            ):
                raise OrderUnavailable(order_id)
            if order.deadline_at is None or order.deadline_at <= datetime_now():
                raise DeadlineExpired(order_id)
            state = extension_state(await self.orders.events(order_id))
            if state.pending is not None:
                raise Conflict("extension_pending")
            if state.requests >= MAX_REQUESTS:
                raise Conflict("extension_limit")
            request_id = state.requests + 1
            await self.orders.add_event(
                OrderEvent(
                    order_id=order_id,
                    actor_id=executor_id,
                    type="extension_requested",
                    payload={"request_id": request_id, "minutes": minutes},
                )
            )
            await self.uow.commit()
            return ExtensionAsk(order, request_id, minutes)
        except BaseException:
            await self.uow.rollback()
            raise

    async def answer(
        self, buyer_id: int, order_id: int, request_id: int, approve: bool
    ) -> ExtensionAnswer:
        """The buyer's answer. Runs under the order lock, the same one the overdue job takes:
        either the deadline moves here and the job then finds the order not overdue, or the job
        has already put the order back in the queue and this call is stale. Conflict
        `extension_stale`: nothing changed."""
        try:
            order = await self.orders.get_for_update(order_id)
            if order is None or order.user_id != buyer_id:
                raise OrderUnavailable(order_id)
            pending = extension_state(await self.orders.events(order_id)).pending
            if (
                order.status is not OrderStatus.assigned
                or order.deadline_at is None
                or pending is None
                or pending.request_id != request_id
            ):
                raise Conflict("extension_stale")
            if approve:
                order.deadline_at = extended_deadline(order, pending.minutes, datetime_now())
                event = OrderEvent(
                    order_id=order_id,
                    actor_id=buyer_id,
                    type="extended",
                    payload={
                        "request_id": request_id,
                        "minutes": pending.minutes,
                        "deadline": order.deadline_at.isoformat(),
                    },
                )
            else:
                event = OrderEvent(
                    order_id=order_id,
                    actor_id=buyer_id,
                    type="extension_declined",
                    payload={"request_id": request_id},
                )
            await self.orders.add_event(event)
            await self.uow.commit()
            return ExtensionAnswer(order, approve, pending.minutes)
        except BaseException:
            await self.uow.rollback()
            raise


Step = Literal["half", "soon"]


@dataclass(frozen=True)
class Reminder:
    order: Order
    step: Step
    left_minutes: int


def due_step(order: Order, now: datetime) -> Step | None:
    """Which reminder the order is ripe for right now: "soon" in the last 15 minutes, "half"
    once half of a term of an hour or more is gone (and "soon" is not due yet)."""
    if order.deadline_at is None or order.deadline_at <= now:
        return None
    left = order.deadline_at - now
    if left <= timedelta(minutes=SOON_MINUTES):
        return "soon"
    if order.assigned_at is not None:
        total = order.deadline_at - order.assigned_at
        if total >= timedelta(minutes=HALF_MIN_TOTAL_MINUTES) and left <= total / 2:
            return "half"
    return None


@dataclass(frozen=True)
class ReminderInteractor(BaseInteractor):
    uow: UnitOfWork
    orders: OrdersGateway

    async def due(self) -> list[Reminder]:
        """Records the reminders that are due, one transaction per order, and returns them for the
        caller to send. Like the rating request: the event is committed first, so a crash loses
        one message at most and never sends two. Once per step and per `deadline_at`: an
        extension moves the deadline, so its reminders come again."""
        found: list[Reminder] = []
        now = datetime_now()
        for candidate in await self.orders.assigned_with_deadline(now):
            if due_step(candidate, now) is None:
                continue
            try:
                order = await self.orders.get_for_update(candidate.id)
                now = datetime_now()
                step = due_step(order, now) if order is not None else None
                if order is None or step is None or order.status is not OrderStatus.assigned:
                    await self.uow.rollback()
                    continue
                assert order.deadline_at is not None
                deadline = order.deadline_at.isoformat()
                if any(
                    e.type == "reminder"
                    and e.payload.get("step") == step
                    and e.payload.get("deadline") == deadline
                    for e in await self.orders.events(order.id)
                ):
                    await self.uow.rollback()
                    continue
                await self.orders.add_event(
                    OrderEvent(
                        order_id=order.id,
                        type="reminder",
                        payload={"step": step, "deadline": deadline},
                    )
                )
                await self.uow.commit()
                left = math.ceil((order.deadline_at - now).total_seconds() / 60)
                found.append(Reminder(order, step, max(left, 1)))
            except Exception:
                await self.uow.rollback()
                logger.exception("recording the reminder of order %s failed", candidate.id)
        return found
