"""«Need data»: the executor of an assigned order asks the buyer a question and the order is on
pause (`orders.paused_at`): the deadline does not run, the overdue job and the reminders skip it.
The buyer's first message in the order chat ends the pause and the deadline moves by its length;
a buyer who stays silent for `INFO_HOURS` gets a refund (job `info_timeout`, in `info_request.py`).

The question itself is a chat message of the executor; the event `info_requested` keeps its text
for the notice and the order card."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Final

from app.application.ports.repositories.orders import OrdersGateway
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.utils.time import datetime_now

INFO_HOURS: Final = 24
INFO_REMIND_BEFORE: Final = timedelta(hours=2)
MAX_PAUSES: Final = 3
QUESTION_MAX: Final = 300


@dataclass(frozen=True)
class InfoPending:
    """The unanswered question: the buyer has until `until`, then the order is refunded."""

    question: str
    asked_at: datetime

    @property
    def until(self) -> datetime:
        return self.asked_at + timedelta(hours=INFO_HOURS)


def is_paused(order: Order) -> bool:
    return order.status is OrderStatus.assigned and order.paused_at is not None


def pauses_used(events: list[OrderEvent]) -> int:
    return sum(1 for e in events if e.type == "info_requested")


def pending_info(order: Order, events: list[OrderEvent]) -> InfoPending | None:
    if not is_paused(order) or order.paused_at is None:
        return None
    asked = [e for e in events if e.type == "info_requested"]
    question = str(asked[-1].payload.get("question", "")) if asked else ""
    return InfoPending(question, order.paused_at)


def can_ask_info(order: Order, events: list[OrderEvent], now: datetime) -> bool:
    """The executor may ask: accepted, in time, not paused already, under the limit. (An open
    dispute is checked by the caller.)"""
    return (
        order.status is OrderStatus.assigned
        and order.accept_until is None
        and order.deadline_at is not None
        and order.deadline_at > now
        and order.paused_at is None
        and pauses_used(events) < MAX_PAUSES
    )


async def resume_locked(
    orders: OrdersGateway, order: Order, actor_id: int | None
) -> datetime | None:
    """The buyer answered: the pause ends and the deadline is moved by its length. Under the
    order lock, commits nothing. Returns the new deadline, None when there was no pause."""
    if not is_paused(order) or order.paused_at is None:
        return None
    now = datetime_now()
    if order.deadline_at is not None:
        # at most the 24 h the buyer is given: a longer pause (a dispute) is not credited
        paused = min(max(now - order.paused_at, timedelta(0)), timedelta(hours=INFO_HOURS))
        order.deadline_at += paused
    order.paused_at = None
    await orders.add_event(
        OrderEvent(
            order_id=order.id,
            actor_id=actor_id,
            type="info_answered",
            payload={"deadline": order.deadline_at.isoformat() if order.deadline_at else None},
        )
    )
    return order.deadline_at
