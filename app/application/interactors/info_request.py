"""«Need data»: the question, the 24 h wait for the answer and the refund when none comes. The
pause itself (what it stops, how it ends) is described in `info_state.py`. The buyer's answer
(`ConversationInteractor.post`) and the timer below both run under the order lock, so a second
before the end exactly one of them wins: an answer resumes the order, a missed one refunds it."""

import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from app.application.errors.shop import Conflict, DeadlineExpired, InvalidInput, OrderUnavailable
from app.application.interactors.base import BaseInteractor
from app.application.interactors.conversations import ConversationInteractor, Posted
from app.application.interactors.info_state import (
    INFO_HOURS,
    INFO_REMIND_BEFORE,
    MAX_PAUSES,
    QUESTION_MAX,
    is_paused,
    pauses_used,
)
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.interactors.payouts import Refunded
from app.application.ports.repositories.disputes import DisputesGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.utils.time import datetime_now

logger: Final = logging.getLogger(__name__)

WAIT: Final = timedelta(hours=INFO_HOURS)


@dataclass(frozen=True)
class InfoAsk:
    order: Order
    posted: Posted
    question: str


@dataclass(frozen=True)
class InfoTimeout:
    order: Order
    refund: Refunded


@dataclass(frozen=True)
class InfoRequestInteractor(BaseInteractor):
    uow: UnitOfWork
    orders: OrdersGateway
    disputes: DisputesGateway
    chat: ConversationInteractor
    review: OrderReviewInteractor

    async def ask(self, executor_id: int, order_id: int, question: str) -> InfoAsk:
        """The executor of an assigned order asks the buyer for data: the question goes into the
        order chat (through the contacts filter, ContactsBlocked) and the order is paused, both
        in one transaction. Conflict: `info_pending`, `info_limit`, `dispute_open`,
        `not_accepted`; DeadlineExpired; InvalidInput `question`."""
        question = question.strip()
        if not question or len(question) > QUESTION_MAX:
            raise InvalidInput("question")
        conversation = await self.chat.order_conversation(executor_id, order_id)

        async def pause(order: Order) -> None:
            locked = await self.orders.get_for_update(order_id)
            if (
                locked is None
                or locked.status is not OrderStatus.assigned
                or locked.executor_id != executor_id
            ):
                raise OrderUnavailable(order_id)
            if await self.disputes.open_for_order(order_id) is not None:
                raise Conflict("dispute_open")
            if locked.accept_until is not None:
                raise Conflict("not_accepted")
            if locked.paused_at is not None:
                raise Conflict("info_pending")
            used = pauses_used(await self.orders.events(order_id))
            if used >= MAX_PAUSES:
                raise Conflict("info_limit")
            now = datetime_now()
            if locked.deadline_at is None or locked.deadline_at <= now:
                raise DeadlineExpired(order_id)
            locked.paused_at = now
            await self.orders.add_event(
                OrderEvent(
                    order_id=order_id,
                    actor_id=executor_id,
                    type="info_requested",
                    payload={"question": question, "n": used + 1},
                )
            )

        posted = await self.chat.post(
            conversation.id, executor_id, question, None, before_store=pause
        )
        order = await self.orders.get(order_id)
        assert order is not None
        return InfoAsk(order, posted, question)

    async def timeout_due(self) -> list[InfoTimeout]:
        """Buyers who did not answer for 24 h: the order is refunded (no fault of the executor,
        like a cancellation by agreement). One transaction per order."""
        done: list[InfoTimeout] = []
        for order_id in await self.orders.paused_before(datetime_now() - WAIT):
            try:
                order = await self.orders.get_for_update(order_id)
                if (
                    order is None
                    or not is_paused(order)
                    or order.paused_at is None
                    or order.paused_at + WAIT > datetime_now()
                    or await self.disputes.open_for_order(order_id) is not None
                ):
                    await self.uow.rollback()  # answered, handed in or disputed a moment ago
                    continue
                refund = await self.review.refund_locked(order, None, "info_timeout")
                await self.orders.add_event(OrderEvent(order_id=order_id, type="info_timeout"))
                await self.uow.commit()
                done.append(InfoTimeout(order, refund))
            except Exception:
                await self.uow.rollback()
                logger.exception(
                    "refunding order %s after an unanswered question failed", order_id
                )
        return done

    async def remind_due(self) -> list[Order]:
        """One message to the buyer 2 hours before the refund. The event is committed first (a
        crash loses one message, never sends two) and carries `paused_at`, so a second pause of
        the order is reminded again."""
        found: list[Order] = []
        for order_id in await self.orders.paused_before(
            datetime_now() - WAIT + INFO_REMIND_BEFORE
        ):
            try:
                order = await self.orders.get_for_update(order_id)
                now = datetime_now()
                if (
                    order is None
                    or not is_paused(order)
                    or order.paused_at is None
                    or order.paused_at + WAIT - INFO_REMIND_BEFORE > now
                    or order.paused_at + WAIT <= now
                    or await self.disputes.open_for_order(order_id) is not None
                ):
                    await self.uow.rollback()
                    continue
                stamp = order.paused_at.isoformat()
                if any(
                    e.type == "info_reminder" and e.payload.get("paused_at") == stamp
                    for e in await self.orders.events(order_id)
                ):
                    await self.uow.rollback()
                    continue
                await self.orders.add_event(
                    OrderEvent(
                        order_id=order_id, type="info_reminder", payload={"paused_at": stamp}
                    )
                )
                await self.uow.commit()
                found.append(order)
            except Exception:
                await self.uow.rollback()
                logger.exception("recording the info reminder of order %s failed", order_id)
        return found
