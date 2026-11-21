from dataclasses import dataclass
from typing import Any

from app.application.errors.shop import (
    ChatForbidden,
    InvalidInput,
    OrderUnavailable,
    TicketUnavailable,
)
from app.application.interactors.base import BaseInteractor
from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.repositories.support import SupportGateway
from app.application.ports.repositories.users import UsersGateway
from app.application.ports.uow import UnitOfWork
from app.domain.enums.roles import Role
from app.domain.enums.support import ChatRole, ConversationKind, TicketStatus
from app.domain.order import Order
from app.domain.support import Conversation, Message, Ticket
from app.utils.time import datetime_now

HISTORY_LIMIT = 20


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


_Context = tuple[Participants, Ticket | None, Order | None]


@dataclass(frozen=True)
class ConversationInteractor(BaseInteractor):
    uow: UnitOfWork
    support: SupportGateway
    orders: OrdersGateway
    users: UsersGateway
    executors: ExecutorsGateway

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
        """Only for the buyer, the current executor, a manager or an admin."""
        try:
            order = await self.orders.get(order_id)
            if order is None or (
                actor_id not in (order.user_id, order.executor_id)
                and not await self._is_staff(actor_id)
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
        the buyer, the counterpart, any admin, a manager for an order or an untaken ticket."""
        ctx = await self._load(conversation)
        if ctx is None:
            return None
        participants, ticket, order = ctx
        if user_id == participants.buyer_id:
            return ChatRole.buyer
        if user_id == participants.counterpart_id:
            return participants.counterpart_role
        user = await self.users.get(user_id)
        if user is None:
            return None
        if user.roles & Role.ADMIN:
            return ChatRole.admin
        if user.roles & Role.MANAGER and (order is not None or (ticket and not ticket.manager_id)):
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
            message = Message(
                conversation_id=conversation.id,
                sender_id=sender_id,
                sender_role=role,
                text=text,
                media=media,
            )
            await self.support.add_message(message)
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

    async def history(self, conversation_id: int, limit: int = HISTORY_LIMIT) -> list[Message]:
        return await self.support.history(conversation_id, limit)

    async def _is_staff(self, user_id: int) -> bool:
        user = await self.users.get(user_id)
        return user is not None and bool(user.roles & (Role.ADMIN | Role.MANAGER))

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
        participants, ticket, _ = ctx
        if ticket is not None and ticket.status is TicketStatus.closed:
            return None
        if user_id == participants.buyer_id:
            return ChatRole.buyer
        if user_id == participants.counterpart_id:
            return participants.counterpart_role
        return ChatRole.admin if await self._is_admin(user_id) else None
