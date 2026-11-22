from dataclasses import dataclass
from typing import Any

from app.application.contacts_filter import find_contact
from app.application.errors.shop import (
    ChatForbidden,
    Conflict,
    ContactsBlocked,
    InvalidInput,
    ManagerNotFound,
    OrderUnavailable,
    TicketUnavailable,
)
from app.application.interactors.base import BaseInteractor
from app.application.interactors.dispute_state import reply_seen
from app.application.ports.repositories.disputes import DisputesGateway
from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.support import SupportGateway, UnreadCounts
from app.application.ports.repositories.users import UsersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.audit import AuditLog
from app.domain.enums.order import OrderStatus
from app.domain.enums.roles import Role
from app.domain.enums.support import ChatRole, ConversationKind, TicketStatus
from app.domain.order import Order, OrderEvent
from app.domain.support import Conversation, Message, Ticket
from app.domain.user import User
from app.utils.time import datetime_now

CHAT_STATUSES = frozenset({OrderStatus.assigned, OrderStatus.ready})
BLOCKS_BEFORE_NOTICE = 3


@dataclass(frozen=True)
class Participants:
    buyer_id: int
    counterpart_id: int | None  # the ticket manager / the current order executor
    counterpart_role: ChatRole


@dataclass(frozen=True)
class Recipient:
    user_id: int
    role: ChatRole


@dataclass(frozen=True)
class Posted:
    """A stored message and who has to get a copy. Deliver after the commit that stored it."""

    message_id: int
    conversation_id: int
    kind: ConversationKind
    ticket_id: int | None
    order_id: int | None
    sender_id: int
    sender_role: ChatRole
    buyer_name: str
    executor_alias: str | None
    text: str | None
    media: dict[str, Any] | None
    recipients: list[Recipient]
    needs_offer: bool  # an open ticket nobody has taken: managers have to be told


@dataclass(frozen=True)
class OrderChat:
    conversation_id: int
    unread: int
    last: Message | None


_Context = tuple[Participants, Ticket | None, Order | None]


@dataclass(frozen=True)
class ConversationInteractor(BaseInteractor):
    uow: UnitOfWork
    support: SupportGateway
    orders: OrdersGateway
    users: UsersGateway
    executors: ExecutorsGateway
    disputes: DisputesGateway

    async def current_ticket(
        self, user_id: int, order_id: int | None
    ) -> tuple[Ticket, Conversation] | None:
        """The user's open ticket for this order (or the general one). Creates nothing."""
        if order_id is not None and await self.orders.get_for_user(user_id, order_id) is None:
            raise OrderUnavailable(order_id)
        ticket = await self.support.open_ticket_of(user_id, order_id)
        return None if ticket is None else (ticket, await self.ticket_conversation(ticket.id))

    async def open_ticket(
        self, user_id: int, order_id: int | None
    ) -> tuple[Ticket, Conversation, bool]:
        """The user's open ticket for this order (or the general one), or a new one."""
        try:
            await self.support.lock_user(user_id)
            if order_id is not None and await self.orders.get_for_user(user_id, order_id) is None:
                raise OrderUnavailable(order_id)
            ticket = await self.support.open_ticket_of(user_id, order_id)
            created = ticket is None
            if ticket is None:
                ticket = Ticket(user_id=user_id, order_id=order_id, status=TicketStatus.open)
                await self.support.add_ticket(ticket)
                conversation = Conversation(kind=ConversationKind.ticket, ticket_id=ticket.id)
                await self.support.add_conversation(conversation)
            else:
                found = await self.support.ticket_conversation(ticket.id)
                assert found is not None
                conversation = found
            await self.uow.commit()
            return ticket, conversation, created
        except BaseException:
            await self.uow.rollback()
            raise

    async def get_conversation(self, conversation_id: int) -> Conversation | None:
        return await self.support.conversation(conversation_id)

    async def list_tickets(
        self, actor_id: int, scope: str, limit: int = 50
    ) -> list[tuple[Ticket, str, int]]:
        """(ticket, buyer name, conversation id) for staff. scope: open (nobody took it),
        mine (taken by the actor), all (admins only, anything else is empty)."""
        if scope == "all" and not await self._is_admin(actor_id):
            return []
        status = {"open": TicketStatus.open, "mine": TicketStatus.taken}.get(scope)
        manager = actor_id if scope == "mine" else None
        rows: list[tuple[Ticket, str, int]] = []
        for ticket in await self.support.tickets(status, manager, limit):
            user = await self.users.get(ticket.user_id)
            conversation = await self.ticket_conversation(ticket.id)
            rows.append((ticket, user.name if user else "", conversation.id))
        return rows

    async def staff(self) -> list[User]:
        """Managers and admins: whom a ticket can be handed to."""
        return await self.users.staff()

    async def ticket_card(self, ticket_id: int) -> tuple[Ticket, str] | None:
        """The ticket and its owner's name, for the manager."""
        ticket = await self.support.ticket(ticket_id)
        if ticket is None:
            return None
        user = await self.users.get(ticket.user_id)
        return ticket, user.name if user else ""

    async def take_ticket(self, manager_id: int, ticket_id: int) -> bool:
        """The first manager wins; False for everyone else (or for a non-manager)."""
        try:
            user = await self.users.get(manager_id)
            if user is None or not user.roles & (Role.MANAGER | Role.ADMIN):
                await self.uow.rollback()
                return False
            ticket = await self.support.ticket_for_update(ticket_id)
            if ticket is None or ticket.status is not TicketStatus.open or ticket.manager_id:
                await self.uow.rollback()
                return False
            ticket.manager_id = manager_id
            ticket.status = TicketStatus.taken
            ticket.taken_at = datetime_now()
            await self.uow.commit()
            return True
        except BaseException:
            await self.uow.rollback()
            raise

    async def hand_over(
        self, actor_id: int, ticket_id: int, manager_id: int
    ) -> tuple[Ticket, int | None]:
        """An admin passes any live ticket, a manager only his own, to another manager or admin.
        Returns the ticket and the manager who had it (None: nobody)."""
        try:
            ticket = await self.support.ticket_for_update(ticket_id)
            actor = await self.users.get(actor_id)
            if ticket is None or ticket.status is TicketStatus.closed or actor is None:
                raise TicketUnavailable(ticket_id)
            if not actor.roles & Role.ADMIN and ticket.manager_id != actor_id:
                raise TicketUnavailable(ticket_id)
            target = await self.users.get(manager_id)
            if target is None or not target.roles & (Role.MANAGER | Role.ADMIN):
                raise ManagerNotFound(manager_id)
            if ticket.manager_id == manager_id:
                raise Conflict("same_manager")
            previous = ticket.manager_id
            ticket.manager_id = manager_id
            ticket.status = TicketStatus.taken
            ticket.taken_at = datetime_now()
            await self.executors.add_audit(
                AuditLog(
                    actor_id=actor_id,
                    action="ticket.handover",
                    target=f"ticket:{ticket_id}",
                    payload={"from": previous, "to": manager_id},
                )
            )
            await self.uow.commit()
            return ticket, previous
        except BaseException:
            await self.uow.rollback()
            raise

    async def close_ticket(self, actor_id: int, ticket_id: int) -> Ticket:
        """The ticket manager, an admin or the user who opened it."""
        try:
            ticket = await self.support.ticket_for_update(ticket_id)
            if ticket is None or ticket.status is TicketStatus.closed:
                raise TicketUnavailable(ticket_id)
            if actor_id not in (ticket.user_id, ticket.manager_id) and not await self._is_admin(
                actor_id
            ):
                raise TicketUnavailable(ticket_id)
            ticket.status = TicketStatus.closed
            ticket.closed_at = datetime_now()
            await self.uow.commit()
            return ticket
        except BaseException:
            await self.uow.rollback()
            raise

    async def order_conversation(self, actor_id: int, order_id: int) -> Conversation:
        """Only for the buyer, the current executor, an admin, or a manager while a dispute is
        open."""
        try:
            order = await self.orders.get(order_id)
            if order is None or (
                actor_id not in (order.user_id, order.executor_id)
                and await self._staff_role(actor_id, order) is None
            ):
                raise OrderUnavailable(order_id)
            conversation = await self.support.order_conversation(order_id)
            await self.uow.commit()
            return conversation
        except BaseException:
            await self.uow.rollback()
            raise

    async def ticket_conversation(self, ticket_id: int) -> Conversation:
        conversation = await self.support.ticket_conversation(ticket_id)
        assert conversation is not None  # made together with the ticket
        return conversation

    async def participants(self, conversation: Conversation) -> Participants | None:
        ctx = await self._load(conversation)
        return None if ctx is None else ctx[0]

    async def reader_role(self, user_id: int, conversation: Conversation) -> ChatRole | None:
        """The capacity in which the user may read here (a closed ticket stays readable):
        the buyer, the counterpart, any admin, a manager for an untaken ticket or an order with
        an open dispute."""
        ctx = await self._load(conversation)
        if ctx is None:
            return None
        participants, ticket, order = ctx
        if user_id == participants.buyer_id:
            return ChatRole.buyer
        if user_id == participants.counterpart_id:
            return participants.counterpart_role
        if order is not None:
            return await self._staff_role(user_id, order)
        user = await self.users.get(user_id)
        if user is None:
            return None
        if user.roles & Role.ADMIN:
            return ChatRole.admin
        if user.roles & Role.MANAGER and ticket and not ticket.manager_id:
            return ChatRole.manager
        return None

    async def messages(
        self, conversation_id: int, before_id: int | None, limit: int
    ) -> tuple[list[Message], bool]:
        """One page, oldest first, and whether older messages exist."""
        page = await self.support.messages_page(conversation_id, before_id, limit + 1)
        return page[-limit:], len(page) > limit

    async def message(self, message_id: int) -> Message | None:
        return await self.support.message(message_id)

    async def readable_message(self, user_id: int, message_id: int) -> Message | None:
        """The message, only for someone who may read its conversation."""
        message = await self.support.message(message_id)
        conversation = (
            await self.support.conversation(message.conversation_id) if message else None
        )
        if message is None or conversation is None:
            return None
        return message if await self.reader_role(user_id, conversation) else None

    async def mark_read(self, user_id: int, conversation_id: int, message_id: int) -> None:
        """Reads up to `message_id` (the caller has checked he may read the conversation)."""
        try:
            message = await self.support.message(message_id)
            if message is None or message.conversation_id != conversation_id:
                raise InvalidInput("message")  # a made-up id would hide future messages
            await self.support.mark_read(conversation_id, user_id, message_id)
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise

    async def unread_counts(self, user_id: int) -> UnreadCounts:
        return await self.support.unread_counts(
            user_id, await self._is_staff(user_id), CHAT_STATUSES
        )

    async def unread_by_order(self, user_id: int, orders: list[Order]) -> dict[int, int]:
        """For a list of his own orders; a chat closed with its order shows nothing."""
        return await self.support.unread_by_order(
            user_id, [o.id for o in orders if o.status in CHAT_STATUSES]
        )

    async def order_chat_summary(self, user_id: int, order_id: int) -> OrderChat | None:
        """None when there is no chat yet or the user may not read it."""
        conversation = await self.support.find_order_conversation(order_id)
        if conversation is None or await self.reader_role(user_id, conversation) is None:
            return None
        unread = await self.support.unread_by_order(user_id, [order_id])
        page = await self.support.messages_page(conversation.id, None, 1)
        return OrderChat(conversation.id, unread.get(order_id, 0), page[-1] if page else None)

    async def unread_by_ticket(self, user_id: int, tickets: list[Ticket]) -> dict[int, int]:
        return await self.support.unread_by_ticket(
            user_id, [t.id for t in tickets if t.status is not TicketStatus.closed]
        )

    async def can_post(self, user_id: int, conversation: Conversation) -> ChatRole | None:
        """The capacity in which the user may write here now, or None."""
        ctx = await self._load(conversation)
        return None if ctx is None else await self._role(user_id, ctx)

    async def post(
        self,
        conversation_id: int,
        sender_id: int,
        text: str | None,
        media: dict[str, Any] | None,
    ) -> Posted:
        """Stores the message first; the caller delivers copies afterwards.
        A failed delivery never loses the message."""
        text = (text or "").strip() or None
        if text is None and media is None:
            raise InvalidInput("empty")
        try:
            conversation = await self.support.conversation(conversation_id)
            ctx = await self._load(conversation) if conversation else None
            role = await self._role(sender_id, ctx) if ctx else None
            if conversation is None or ctx is None or role is None:
                raise ChatForbidden(conversation_id)
            participants, ticket, order = ctx
            if order is not None and role in (ChatRole.buyer, ChatRole.executor):
                await self._no_contacts(order, sender_id, role, text)
                await reply_seen(self.disputes, self.orders, order.id, role.value)
            message = Message(
                conversation_id=conversation.id,
                sender_id=sender_id,
                sender_role=role,
                text=text,
                media=media,
            )
            await self.support.add_message(message)
            await self.support.mark_read(conversation.id, sender_id, message.id)  # his own: read
            buyer = await self.users.get(participants.buyer_id)
            alias = None
            if order is not None and order.executor_id is not None:
                profile = await self.executors.get_profile(order.executor_id)
                alias = profile.alias if profile else None
            recipients = [
                Recipient(uid, r)
                for uid, r in (
                    (participants.buyer_id, ChatRole.buyer),
                    (participants.counterpart_id, participants.counterpart_role),
                )
                if uid is not None and uid != sender_id
            ]
            await self.uow.commit()
            return Posted(
                message_id=message.id,
                conversation_id=conversation.id,
                kind=conversation.kind,
                ticket_id=ticket.id if ticket else None,
                order_id=order.id if order else (ticket.order_id if ticket else None),
                sender_id=sender_id,
                sender_role=role,
                buyer_name=buyer.name if buyer else "",
                executor_alias=alias,
                text=text,
                media=media,
                recipients=recipients,
                needs_offer=ticket is not None and ticket.status is TicketStatus.open,
            )
        except BaseException:
            await self.uow.rollback()
            raise

    async def record_delivery(self, message_id: int, tg_chat_id: int, tg_message_id: int) -> None:
        """Remembers the copy a recipient got, so a reply to it finds the conversation.
        Only the first copy is kept (a message with two recipients is rare)."""
        try:
            message = await self.support.message(message_id)
            if message is not None and message.tg_message_id is None:
                message.tg_chat_id = tg_chat_id
                message.tg_message_id = tg_message_id
                await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise

    async def find_by_reply(self, tg_chat_id: int, tg_message_id: int) -> Conversation | None:
        message = await self.support.message_by_copy(tg_chat_id, tg_message_id)
        if message is None:
            return None
        return await self.support.conversation(message.conversation_id)

    async def _no_contacts(
        self, order: Order, sender_id: int, role: ChatRole, text: str | None
    ) -> None:
        """A buyer or an executor may not hand over contacts in an order chat (support is not
        filtered). The attempt is kept as an event (the text is not), and the third one of the same
        person is reported to the caller once."""
        found = find_contact(text)
        if found is None:
            return
        await self.orders.add_event(
            OrderEvent(
                order_id=order.id,
                actor_id=sender_id,
                type="blocked_message",
                payload={"by": role.value, "found": found},
            )
        )
        attempts = sum(
            1
            for e in await self.orders.events(order.id)
            if e.type == "blocked_message" and e.actor_id == sender_id
        )
        alias = None
        if role is ChatRole.executor:
            profile = await self.executors.get_profile(sender_id)
            alias = profile.alias if profile else None
        await self.uow.commit()
        raise ContactsBlocked(order.id, role.value, alias, attempts == BLOCKS_BEFORE_NOTICE)

    async def _is_staff(self, user_id: int) -> bool:
        user = await self.users.get(user_id)
        return user is not None and bool(user.roles & (Role.ADMIN | Role.MANAGER))

    async def _staff_role(self, user_id: int, order: Order) -> ChatRole | None:
        """Support in an order chat: an admin any time, a manager while a dispute is open."""
        user = await self.users.get(user_id)
        if user is None:
            return None
        if user.roles & Role.ADMIN:
            return ChatRole.admin
        if user.roles & Role.MANAGER and await self.disputes.open_for_order(order.id):
            return ChatRole.manager
        return None

    async def _is_admin(self, user_id: int) -> bool:
        user = await self.users.get(user_id)
        return user is not None and bool(user.roles & Role.ADMIN)

    async def _load(self, conversation: Conversation) -> _Context | None:
        if conversation.kind is ConversationKind.ticket and conversation.ticket_id:
            ticket = await self.support.ticket(conversation.ticket_id)
            if ticket is None:
                return None
            return Participants(ticket.user_id, ticket.manager_id, ChatRole.manager), ticket, None
        if conversation.order_id:
            order = await self.orders.get(conversation.order_id)
            if order is None:
                return None
            return Participants(order.user_id, order.executor_id, ChatRole.executor), None, order
        return None

    async def _role(self, user_id: int, ctx: _Context) -> ChatRole | None:
        participants, ticket, order = ctx
        if ticket is not None and ticket.status is TicketStatus.closed:
            return None
        if order is not None and order.status not in CHAT_STATUSES:  # chat only while in work
            return None
        if user_id == participants.buyer_id:
            return ChatRole.buyer
        if user_id == participants.counterpart_id:
            return participants.counterpart_role
        if order is not None:
            return await self._staff_role(user_id, order)
        return ChatRole.admin if await self._is_admin(user_id) else None
