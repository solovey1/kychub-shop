from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert

from app.application.errors.base import UserNotFound
from app.application.ports.repositories.support import SupportGateway
from app.domain.enums.support import ConversationKind, TicketStatus
from app.domain.support import Conversation, Message, Ticket
from app.domain.user import User
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW


@dataclass
class SupportRepository(SupportGateway):
    _uow: UoW
    _helper: SqlRepositoryHelper[Ticket]

    async def lock_user(self, user_id: int) -> None:
        row = await self._helper.session.scalar(
            select(User.id).where(User.id == user_id).with_for_update(key_share=True)
        )
        if row is None:
            raise UserNotFound(user_id)

    async def add_ticket(self, ticket: Ticket) -> None:
        await self._uow.flush(ticket)

    async def add_conversation(self, conversation: Conversation) -> None:
        await self._uow.flush(conversation)

    async def add_message(self, message: Message) -> None:
        await self._uow.flush(message)

    async def ticket(self, ticket_id: int) -> Ticket | None:
        return await self._helper.get_one(Ticket.id == ticket_id)

    async def ticket_for_update(self, ticket_id: int) -> Ticket | None:
        query = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        ticket: Ticket | None = await self._helper.session.scalar(query)
        return ticket

    async def open_ticket_of(self, user_id: int, order_id: int | None) -> Ticket | None:
        same_order = Ticket.order_id.is_(None) if order_id is None else Ticket.order_id == order_id
        return await self._helper.get_one(
            Ticket.user_id == user_id,
            Ticket.status.in_((TicketStatus.open, TicketStatus.taken)),
            same_order,
        )

    async def conversation(self, conversation_id: int) -> Conversation | None:
        conversation: Conversation | None = await self._helper.session.get(
            Conversation, conversation_id
        )
        return conversation

    async def ticket_conversation(self, ticket_id: int) -> Conversation | None:
        query = select(Conversation).where(Conversation.ticket_id == ticket_id)
        conversation: Conversation | None = await self._helper.session.scalar(query)
        return conversation

    async def order_conversation(self, order_id: int) -> Conversation:
        session = self._helper.session
        await session.execute(
            insert(Conversation)
            .values(kind=ConversationKind.order, order_id=order_id)
            .on_conflict_do_nothing(
                index_elements=[Conversation.order_id], index_where=text("kind = 'order'")
            )
        )
        conversation = await session.scalar(
            select(Conversation).where(
                Conversation.kind == ConversationKind.order, Conversation.order_id == order_id
            )
        )
        assert conversation is not None
        return conversation

    async def message(self, message_id: int) -> Message | None:
        query = (
            select(Message)
            .where(Message.id == message_id)
            .execution_options(populate_existing=True)  # server-set created_at
        )
        message: Message | None = await self._helper.session.scalar(query)
        return message

    async def message_by_copy(self, tg_chat_id: int, tg_message_id: int) -> Message | None:
        query = select(Message).where(
            Message.tg_chat_id == tg_chat_id, Message.tg_message_id == tg_message_id
        )
        message: Message | None = await self._helper.session.scalar(query)
        return message

    async def history(self, conversation_id: int, limit: int) -> list[Message]:
        query = (
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.id.desc())
            .limit(limit)
        )
        return list(reversed(list(await self._helper.session.scalars(query))))

    async def messages_page(
        self, conversation_id: int, before_id: int | None, limit: int
    ) -> list[Message]:
        query = select(Message).where(Message.conversation_id == conversation_id)
        if before_id is not None:
            query = query.where(Message.id < before_id)
        query = query.order_by(Message.id.desc()).limit(limit)
        return list(reversed(list(await self._helper.session.scalars(query))))

    async def tickets(
        self, status: TicketStatus | None, manager_id: int | None, limit: int
    ) -> list[Ticket]:
        query = select(Ticket)
        if status is not None:
            query = query.where(Ticket.status == status)
        if manager_id is not None:
            query = query.where(Ticket.manager_id == manager_id)
        query = query.order_by(Ticket.id.desc()).limit(limit)
        return list(await self._helper.session.scalars(query))
