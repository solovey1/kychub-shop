import logging
from collections.abc import Awaitable, Iterable
from dataclasses import dataclass
from typing import Final

from aiogram import html

from app.application.i18n_text import fmt_usd
from app.application.interactors.conversations import Posted
from app.application.interactors.dispatch import Assigned, DispatchInteractor, DispatchResult
from app.application.interactors.payouts import Refunded
from app.application.models.config import AppConfig
from app.application.ports.repositories.orders import OrdersGateway
from app.domain.enums.order import OrderStatus
from app.domain.enums.support import TicketStatus
from app.domain.ledger import Withdrawal
from app.domain.order import Order
from app.domain.support import Ticket
from app.domain.user import User
from app.infrastructure.events import EventHub
from app.infrastructure.telegram.notices import OrderNotices
from app.infrastructure.telegram.notifier import Notifier
from app.infrastructure.telegram.offers import OfferService
from app.infrastructure.telegram.relay import Delivery, Relay
from app.infrastructure.telegram.ticket_offers import TicketOffers
from app.presentation.telegram.keyboards.chat import ticket_keyboard

logger: Final = logging.getLogger(__name__)


async def _safe(what: str, call: Awaitable[object]) -> None:
    try:
        await call
    except Exception:
        logger.exception("%s failed", what)


@dataclass(frozen=True)
class Effects:
    """What happens in Telegram and in open Mini Apps after an action succeeded. The bot flows
    and the Mini App API both call these, so a button and an endpoint always do the same.
    Call after the commit; a failure here is logged and never undoes the action."""

    offers: OfferService
    ticket_offers: TicketOffers
    notifier: Notifier
    relay: Relay
    hub: EventHub
    notices: OrderNotices
    orders: OrdersGateway
    dispatcher: DispatchInteractor
    config: AppConfig

    async def order_cancelled(self, order_id: int) -> None:
        await _safe(
            f"closing the offers of order {order_id}",
            self.offers.close(order_id, "messages-executor-offer_cancelled"),
        )
        await self._order_event(order_id, OrderStatus.cancelled, queue=True)

    async def order_taken(self, order_id: int, executor_id: int) -> None:
        await _safe(
            f"closing the offers of order {order_id}",
            self.offers.close(order_id, "messages-executor-offer_taken", except_chat=executor_id),
        )
        await self._order_event(order_id, OrderStatus.assigned, queue=True, extra=[executor_id])

    async def order_assigned(self, assigned: Assigned) -> None:
        """A manager gave the order to an executor: the new one gets the card, the old one (or
        the other executors still holding the offer) lose it."""
        if assigned.previous_id is None:
            await _safe(
                f"closing the offers of order {assigned.order_id}",
                self.offers.close(
                    assigned.order_id,
                    "messages-executor-offer_taken",
                    except_chat=assigned.executor_id,
                ),
            )
        else:
            await self.notifier.send(
                assigned.previous_id,
                "messages-executor-reassigned_away",
                id=str(assigned.order_id),
            )
        await self.offers.announce(
            DispatchResult(assigned.order_id, "assigned", [assigned.executor_id])
        )
        extra = [assigned.executor_id, *([assigned.previous_id] if assigned.previous_id else [])]
        await self._order_event(
            assigned.order_id,
            OrderStatus.assigned,
            queue=assigned.previous_id is None,
            staff=True,
            extra=extra,
        )

    async def order_refused(self, result: DispatchResult) -> None:
        """The order is back in the queue: offers (and live events) go out as for any dispatch."""
        await self.offers.announce(result)

    async def result_submitted(self, order: Order) -> None:
        await _safe(
            f"notifying reviewers about order {order.id}", self.notices.ready_for_review(order)
        )
        await self._order_event(order.id, OrderStatus.ready, staff=True)

    async def order_confirmed(self, order: Order) -> None:
        await _safe(f"delivering order {order.id}", self.notices.deliver(order))
        await _safe(f"confirming order {order.id}", self.notices.confirmed(order))
        await self._order_event(order.id, OrderStatus.completed, staff=True)

    async def order_sent_back(self, order: Order, comment: str) -> None:
        await _safe(f"sending back order {order.id}", self.notices.sent_back(order, comment))
        await self._order_event(order.id, OrderStatus.assigned, staff=True)

    async def order_failed(self, refund: Refunded) -> None:
        in_queue = refund.was is OrderStatus.in_queue
        if in_queue:
            await _safe(
                f"closing the offers of order {refund.order_id}",
                self.offers.close(refund.order_id, "messages-executor-offer_cancelled"),
            )
        await _safe(f"refunding order {refund.order_id}", self.notices.refunded(refund))
        await self._order_event(refund.order_id, OrderStatus.refunded, queue=in_queue, staff=True)

    async def withdrawal_created(self, user: User, withdrawal: Withdrawal) -> None:
        await _safe(
            f"notifying staff about withdrawal {withdrawal.id}",
            self.notifier.staff(
                "messages-withdrawal-new",
                id=str(withdrawal.id),
                user=user.mention,
                amount=fmt_usd(withdrawal.amount),
                address=html.quote(withdrawal.address),
            ),
        )

    async def message_posted(
        self, posted: Posted, source_message_id: int | None = None
    ) -> Delivery:
        """Copies to the other side, the «new ticket» notice for managers, live events.
        `source_message_id`: the sender's own Telegram message, None when it came from the app."""
        delivery = await self.relay.deliver(posted, source_message_id)
        await self.ticket_offers.announce(posted)
        if posted.needs_offer and posted.ticket_id is not None:
            users = [posted.sender_id, *(r.user_id for r in posted.recipients)]
            await self._ticket_event(posted.ticket_id, TicketStatus.open, users)
        return delivery

    async def ticket_taken(
        self, ticket: Ticket, conversation_id: int, manager_id: int, manager_name: str
    ) -> None:
        """The others lose the «Take» button; the manager gets the chat, the buyer a hello."""
        url = self.config.server.url
        await _safe(
            f"updating ticket {ticket.id} notices",
            self.ticket_offers.close(
                ticket.id, "messages-ticket-taken_by", except_chat=manager_id, name=manager_name
            ),
        )
        await self.notifier.send(
            manager_id,
            "messages-ticket-taken",
            lambda tr: ticket_keyboard(tr, url, conversation_id, ticket.id, staff=True),
            id=str(ticket.id),
        )
        if ticket.user_id != manager_id:
            await self.notifier.send(
                ticket.user_id,
                "messages-ticket-joined",
                lambda tr: ticket_keyboard(tr, url, conversation_id, ticket.id, staff=False),
            )
        await self._ticket_event(ticket.id, TicketStatus.taken, [ticket.user_id])

    async def ticket_closed(self, ticket: Ticket, actor_id: int) -> None:
        if ticket.user_id != actor_id:
            await self.notifier.send(
                ticket.user_id, "messages-ticket-closed_buyer", id=str(ticket.id)
            )
        await _safe(
            f"updating ticket {ticket.id} notices",
            self.ticket_offers.close(ticket.id, "messages-ticket-closed"),
        )
        await self._ticket_event(ticket.id, TicketStatus.closed, [ticket.user_id])

    async def ticket_handed_over(
        self, ticket: Ticket, conversation_id: int, previous_id: int | None
    ) -> None:
        url = self.config.server.url
        assert ticket.manager_id is not None
        await self.notifier.send(
            ticket.manager_id,
            "messages-ticket-handed",
            lambda tr: ticket_keyboard(tr, url, conversation_id, ticket.id, staff=True),
            id=str(ticket.id),
        )
        if previous_id is not None:
            await self.notifier.send(previous_id, "messages-ticket-handed_away", id=str(ticket.id))
        await self._ticket_event(
            ticket.id,
            TicketStatus.taken,
            [ticket.user_id, *([previous_id] if previous_id else [])],
        )

    async def _ticket_event(
        self, ticket_id: int, status: TicketStatus, users: Iterable[int]
    ) -> None:
        try:
            staff = await self.notifier.executors.staff_ids()
            await self.hub.publish(
                [*staff, *users],
                {"type": "ticket", "ticket_id": ticket_id, "status": status.value},
            )
        except Exception:
            logger.exception("publishing ticket %s failed", ticket_id)

    async def _order_event(
        self,
        order_id: int,
        status: OrderStatus,
        *,
        queue: bool = False,
        staff: bool = False,
        extra: Iterable[int] = (),
    ) -> None:
        """Live events: the buyer and the executor of the order (and staff, and the executors
        whose queue changed) learn that it moved."""
        try:
            order = await self.orders.get(order_id)
            if order is None:
                return
            users = {order.user_id, *extra}
            if order.executor_id is not None:
                users.add(order.executor_id)
            if staff:
                users.update(await self.notifier.executors.staff_ids())
            await self.hub.publish(
                users, {"type": "order", "order_id": order_id, "status": status.value}
            )
            if queue:
                waiting = [*await self.dispatcher.eligible(order_id), *extra]
                await self.hub.publish(waiting, {"type": "queue"})
        except Exception:
            logger.exception("publishing order %s failed", order_id)
