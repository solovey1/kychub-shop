"""Disputes: the buyer or the executor calls support on an assigned or submitted order.

State machine of one dispute (all changes under the order lock):

    open --(a side writes in the order chat)--> still open, nobody awaited
    open --(staff "request a reply")----------> awaiting buyer | executor, until now + reply hours
    awaiting executor, deadline passed -------> order failed and refunded     (refunded)
    awaiting buyer,    deadline passed -------> order confirmed if submitted  (completed)
                                                 else only the dispute closes (closed)
    staff: confirm / send back / fail --------> completed / sent_back / refunded
    staff: close without changes -------------> closed
    anybody confirms the order meanwhile -----> completed

While a dispute is open the executor's deadline and the auto-confirmation do not run.

Everything that settles the order closes the dispute in the same transaction
(`dispute_state.close_dispute`), so a dispute that was resolved by hand a moment earlier is not
resolved a second time by the job: it is gone from the query, and the re-read under the lock
finds nothing."""

import logging
import math
from dataclasses import dataclass
from datetime import timedelta
from typing import Final

from app.application.errors.shop import Conflict, InvalidInput, OrderUnavailable
from app.application.interactors.base import BaseInteractor
from app.application.interactors.dispute_state import close_dispute
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.interactors.payouts import Refunded
from app.application.ports.repositories.disputes import DisputesGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.settings import SettingsGateway
from app.application.ports.uow import UnitOfWork
from app.application.settings_keys import DEFAULT_DISPUTE_REPLY_HOURS, DISPUTE_REPLY_HOURS
from app.domain.dispute import Dispute
from app.domain.enums.dispute import DisputeResolution, DisputeSide
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.utils.time import datetime_now

logger: Final = logging.getLogger(__name__)

DISPUTE_STATUSES: Final = (OrderStatus.assigned, OrderStatus.ready)
REASON_MAX: Final = 500
REMIND_BEFORE: Final = timedelta(hours=1)
MIN_DEADLINE_LEFT: Final = timedelta(hours=1)
LIST_LIMIT: Final = 100


@dataclass(frozen=True)
class DisputeNews:
    """What the caller tells people after the commit. `side`: who has to answer (None: nobody)."""

    order: Order
    dispute: Dispute
    side: str | None = None


@dataclass(frozen=True)
class AutoResolved:
    order: Order
    dispute: Dispute
    resolution: DisputeResolution
    refund: Refunded | None = None


@dataclass(frozen=True)
class DisputeReminder:
    order: Order
    dispute: Dispute
    left_minutes: int


async def reply_hours(settings: SettingsGateway) -> int:
    return int(await settings.get(DISPUTE_REPLY_HOURS, DEFAULT_DISPUTE_REPLY_HOURS))


def other_side(side: str) -> DisputeSide:
    return DisputeSide.executor if side == DisputeSide.buyer else DisputeSide.buyer


def side_user(order: Order, side: str) -> int | None:
    return order.user_id if side == DisputeSide.buyer else order.executor_id


@dataclass(frozen=True)
class DisputeInteractor(BaseInteractor):
    uow: UnitOfWork
    orders: OrdersGateway
    disputes: DisputesGateway
    settings: SettingsGateway
    review: OrderReviewInteractor

    async def current(self, order_id: int) -> Dispute | None:
        return await self.disputes.open_for_order(order_id)

    async def open_rows(self) -> list[tuple[Dispute, Order]]:
        return await self.disputes.open_rows(LIST_LIMIT)

    async def open(self, user_id: int, order_id: int, reason: str | None) -> DisputeNews:
        """The buyer or the executor of an assigned / submitted order calls support. The other
        side is asked to answer in the chat within the reply hours. Conflict `dispute_open`."""
        reason = (reason or "").strip()[:REASON_MAX] or None
        try:
            order = await self.orders.get_for_update(order_id)
            if order is None or order.status not in DISPUTE_STATUSES:
                raise OrderUnavailable(order_id)
            if user_id == order.user_id:
                side = DisputeSide.buyer
            elif user_id == order.executor_id:
                side = DisputeSide.executor
            else:
                raise OrderUnavailable(order_id)
            if order.accept_until is not None:  # auto-assigned, not accepted yet: nothing to argue
                raise Conflict("not_accepted")
            if await self.disputes.open_for_order(order_id) is not None:
                raise Conflict("dispute_open")
            awaited = other_side(side)
            dispute = Dispute(
                order_id=order_id,
                opened_by=user_id,
                opened_role=side.value,
                reason=reason,
                awaiting_role=awaited.value,
                awaiting_until=datetime_now() + timedelta(hours=await reply_hours(self.settings)),
            )
            await self.disputes.add(dispute)
            await self.orders.add_event(
                OrderEvent(
                    order_id=order_id,
                    actor_id=user_id,
                    type="dispute_opened",
                    payload={"dispute_id": dispute.id, "by": side.value},
                )
            )
            await self.uow.commit()
            return DisputeNews(order, dispute, awaited.value)
        except BaseException:
            await self.uow.rollback()
            raise

    async def request_reply(self, staff_id: int, order_id: int, side: str) -> DisputeNews:
        """Support asks one side to answer in the chat: the wait starts again from now."""
        if side not in (DisputeSide.buyer, DisputeSide.executor):
            raise InvalidInput("side")
        try:
            order = await self.orders.get_for_update(order_id)
            dispute = await self.disputes.open_for_order(order_id) if order else None
            if order is None or dispute is None:
                raise OrderUnavailable(order_id)
            if side_user(order, side) is None:
                raise Conflict("no_executor")
            dispute.awaiting_role = side
            dispute.awaiting_until = datetime_now() + timedelta(
                hours=await reply_hours(self.settings)
            )
            await self.orders.add_event(
                OrderEvent(
                    order_id=order_id,
                    actor_id=staff_id,
                    type="dispute_reply_requested",
                    payload={"dispute_id": dispute.id, "side": side},
                )
            )
            await self.uow.commit()
            return DisputeNews(order, dispute, side)
        except BaseException:
            await self.uow.rollback()
            raise

    async def close(self, staff_id: int, order_id: int) -> DisputeNews:
        """Support closes the dispute and changes nothing about the order, which goes on: an
        assigned one gets at least an hour more (the clock was stopped), a submitted one gets a
        fresh confirmation term."""
        try:
            order = await self.orders.get_for_update(order_id)
            if order is None:
                raise OrderUnavailable(order_id)
            dispute = await self._close_unchanged(order, staff_id)
            if dispute is None:
                raise OrderUnavailable(order_id)
            await self.uow.commit()
            return DisputeNews(order, dispute)
        except BaseException:
            await self.uow.rollback()
            raise

    async def auto_resolve_due(self) -> list[AutoResolved]:
        """Disputes whose awaited side stayed silent past the deadline. One transaction each."""
        done: list[AutoResolved] = []
        for order_id in await self.disputes.expired_order_ids(datetime_now()):
            try:
                order = await self.orders.get_for_update(order_id)
                dispute = await self.disputes.open_for_order(order_id)  # fresh, under the lock
                if (
                    order is None
                    or dispute is None
                    or dispute.awaiting_role is None
                    or dispute.awaiting_until is None
                    or dispute.awaiting_until >= datetime_now()
                ):
                    await self.uow.rollback()  # answered or resolved by hand a moment ago
                    continue
                done.append(await self._resolve(order, dispute))
                await self.uow.commit()
            except Exception:
                await self.uow.rollback()
                logger.exception("resolving the dispute of order %s failed", order_id)
        return done

    async def remind_due(self) -> list[DisputeReminder]:
        """One message to the silent side an hour before the deadline (the event is committed
        first and carries the deadline, so a new request for a reply is reminded again). No
        reminders when the whole term is an hour or less."""
        found: list[DisputeReminder] = []
        if await reply_hours(self.settings) <= 1:
            return found
        now = datetime_now()
        for order_id in await self.disputes.ending_order_ids(now + REMIND_BEFORE, now):
            try:
                order = await self.orders.get_for_update(order_id)
                dispute = await self.disputes.open_for_order(order_id)
                now = datetime_now()
                if (
                    order is None
                    or dispute is None
                    or dispute.awaiting_until is None
                    or dispute.awaiting_until <= now
                    or dispute.awaiting_until - now > REMIND_BEFORE
                ):
                    await self.uow.rollback()
                    continue
                stamp = dispute.awaiting_until.isoformat()
                if any(
                    e.type == "dispute_reminder" and e.payload.get("until") == stamp
                    for e in await self.orders.events(order_id)
                ):
                    await self.uow.rollback()
                    continue
                await self.orders.add_event(
                    OrderEvent(
                        order_id=order_id, type="dispute_reminder", payload={"until": stamp}
                    )
                )
                await self.uow.commit()
                left = math.ceil((dispute.awaiting_until - now).total_seconds() / 60)
                found.append(DisputeReminder(order, dispute, max(left, 1)))
            except Exception:
                await self.uow.rollback()
                logger.exception("recording the dispute reminder of order %s failed", order_id)
        return found

    async def _resolve(self, order: Order, dispute: Dispute) -> AutoResolved:
        """Under the order lock, commits nothing. The silent executor loses (refund), the silent
        buyer loses a submitted order (confirmed); a buyer who is silent about work that is not
        done yet changes nothing, the dispute just closes."""
        silent = dispute.awaiting_role
        if silent == DisputeSide.executor and order.status in DISPUTE_STATUSES:
            refund = await self.review.refund_locked(order, None, "dispute_timeout")
            return AutoResolved(order, dispute, DisputeResolution.refunded, refund)
        if silent == DisputeSide.buyer and order.status is OrderStatus.ready:
            await self.review.complete_locked(order, None)
            return AutoResolved(order, dispute, DisputeResolution.completed)
        await self._close_unchanged(order, None)
        return AutoResolved(order, dispute, DisputeResolution.closed)

    async def _close_unchanged(self, order: Order, by: int | None) -> Dispute | None:
        dispute = await close_dispute(
            self.disputes, self.orders, order, DisputeResolution.closed, by
        )
        if dispute is None:
            return None
        now = datetime_now()
        if order.status is OrderStatus.assigned and order.deadline_at is not None:
            order.deadline_at = max(order.deadline_at, now + MIN_DEADLINE_LEFT)
        elif order.status is OrderStatus.ready:
            order.ready_at = now  # the buyer's confirmation term starts over
        return dispute
