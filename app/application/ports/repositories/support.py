from typing import Protocol

from app.domain.support import Conversation, Message, Ticket


class SupportGateway(Protocol):
    async def lock_user(self, user_id: int) -> None:
        """Serialises ticket creation of one user (a double tap must not make two)."""

    async def add_ticket(self, ticket: Ticket) -> None:
        """Insert and flush, so `ticket.id` is available."""

    async def add_conversation(self, conversation: Conversation) -> None:
        """Insert and flush."""

    async def add_message(self, message: Message) -> None:
        """Insert and flush, so `message.id` is available."""

    async def ticket(self, ticket_id: int) -> Ticket | None: ...

    async def ticket_for_update(self, ticket_id: int) -> Ticket | None: ...

    async def open_ticket_of(self, user_id: int, order_id: int | None) -> Ticket | None:
        """The user's `open` or `taken` ticket for this order (or the general one)."""

    async def conversation(self, conversation_id: int) -> Conversation | None: ...

    async def ticket_conversation(self, ticket_id: int) -> Conversation | None: ...

    async def order_conversation(self, order_id: int) -> Conversation:
        """Get or create; safe against two concurrent creators."""

    async def message(self, message_id: int) -> Message | None: ...

    async def message_by_copy(self, tg_chat_id: int, tg_message_id: int) -> Message | None: ...

    async def history(self, conversation_id: int, limit: int) -> list[Message]:
        """The latest `limit` messages, oldest first."""
