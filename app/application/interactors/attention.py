from dataclasses import dataclass
from typing import Final, Literal

from app.application.interactors.base import BaseInteractor
from app.application.interactors.cancel_request import CANCEL_EVENTS, cancel_state
from app.application.interactors.conversations import CHAT_STATUSES
from app.application.interactors.deadlines import EXTENSION_EVENTS, extension_state
from app.application.interactors.dispatch import DispatchInteractor
from app.application.ports.repositories.disputes import DisputesGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.support import SupportGateway
from app.domain.enums.order import OrderStatus
from app.domain.order import Order

# what an order waits for from its reader
Action = Literal["confirm", "extension", "dispute", "info"]

_IN_WORK: Final = frozenset({OrderStatus.assigned, OrderStatus.ready})


@dataclass(frozen=True)
class Attention:
    """Orders that need the user, distinct (an order with an unread chat and a confirmation to
    give counts once). `offers`: what an executor may take now."""

    orders: int = 0  # buyer: unread chat or an action
    orders_action: int = 0  # buyer: an action only
    work: int = 0  # executor, own orders: unread chat or assigned or a dispute to answer
    work_action: int = 0  # executor: assigned or a dispute to answer
    offers: int = 0


@dataclass(frozen=True)
class AttentionInteractor(BaseInteractor):
    orders: OrdersGateway
    disputes: DisputesGateway
    support: SupportGateway
    dispatch: DispatchInteractor

    async def buyer_actions(self, orders: list[Order]) -> dict[int, Action]:
        """What the buyer has to do per order (orders that wait for nothing are absent): answer
        in an open dispute, answer the executor's question («need data»), answer an extension
        request, say «all fine» to a ready order. Two queries for the whole list."""
        in_work = [o for o in orders if o.status in _IN_WORK]
        disputes = await self.disputes.open_for_orders([o.id for o in in_work])
        assigned = [
            o.id for o in in_work if o.status is OrderStatus.assigned and o.id not in disputes
        ]
        events = await self.orders.extension_events(assigned, EXTENSION_EVENTS)
        found: dict[int, Action] = {}
        for order in in_work:
            dispute = disputes.get(order.id)
            if dispute is not None:
                if dispute.awaiting_role == "buyer":
                    found[order.id] = "dispute"
            elif order.status is OrderStatus.ready:
                found[order.id] = "confirm"
            elif order.paused_at is not None and order.status is OrderStatus.assigned:
                found[order.id] = "info"  # the executor waits for his answer
            elif extension_state(events.get(order.id, [])).pending is not None:
                found[order.id] = "extension"
        return found

    async def executor_actions(
        self, orders: list[Order]
    ) -> dict[int, Literal["work", "dispute", "cancel", "accept", "paused"]]:
        """«work» for an assigned order, «accept» while he has to confirm it, «cancel» when the
        buyer asks to cancel it, «dispute» when a dispute waits for his answer, «paused» while
        the buyer is asked for data (nothing to do for him)."""
        in_work = [o for o in orders if o.status in _IN_WORK]
        disputes = await self.disputes.open_for_orders([o.id for o in in_work])
        assigned = [
            o.id for o in in_work if o.status is OrderStatus.assigned and o.id not in disputes
        ]
        events = await self.orders.extension_events(assigned, CANCEL_EVENTS)
        found: dict[int, Literal["work", "dispute", "cancel", "accept", "paused"]] = {}
        for order in in_work:
            dispute = disputes.get(order.id)
            if dispute is not None:
                if dispute.awaiting_role == "executor":
                    found[order.id] = "dispute"
            elif order.status is OrderStatus.assigned:
                pending = cancel_state(events.get(order.id, [])).pending
                found[order.id] = (
                    "accept"
                    if order.accept_until is not None
                    else "paused"
                    if order.paused_at is not None
                    else "cancel"
                    if pending
                    else "work"
                )
        return found

    async def counts(self, user_id: int, is_executor: bool) -> Attention:
        bought, worked = await self.support.unread_order_ids(user_id, CHAT_STATUSES)
        buyer = await self.buyer_actions(await self.orders.active_for_user(user_id))
        if not is_executor:
            return Attention(len(bought | buyer.keys()), len(buyer))
        actions = await self.executor_actions(await self.orders.in_work_for_executor(user_id))
        mine = {oid for oid, action in actions.items() if action != "paused"}
        return Attention(
            len(bought | buyer.keys()),
            len(buyer),
            len(worked | mine),
            len(mine),
            len(await self.dispatch.queue_for(user_id)),
        )
