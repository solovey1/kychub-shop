import logging
from collections.abc import Awaitable, Iterable
from dataclasses import dataclass
from typing import Final

from app.application.interactors.conversations import Posted
from app.domain.enums.support import TicketStatus
from app.domain.support import Ticket
from app.infrastructure.events import EventHub
from app.infrastructure.telegram.notifier import Notifier
from app.infrastructure.telegram.offers import OfferService
from app.infrastructure.telegram.relay import Delivery, Relay
from app.infrastructure.telegram.ticket_offers import TicketOffers

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

    async def order_cancelled(self, order_id: int) -> None:
        await _safe(
            f"closing the offers of order {order_id}",
            self.offers.close(order_id, "messages-executor-offer_cancelled"),
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

    async def ticket_taken(self, ticket: Ticket, manager_id: int, manager_name: str) -> None:
        await _safe(
            f"updating ticket {ticket.id} notices",
            self.ticket_offers.close(
                ticket.id, "messages-ticket-taken_by", except_chat=manager_id, name=manager_name
            ),
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
