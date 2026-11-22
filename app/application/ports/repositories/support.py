from collections.abc import Collection
from dataclasses import dataclass
from typing import Protocol

from app.domain.enums.order import OrderStatus
from app.domain.enums.support import TicketStatus
from app.domain.support import Conversation, Message, Ticket


@dataclass(frozen=True)
class UnreadCounts:
    """Chats with something unread per tab (`review`: orders waiting for a check)."""

    orders: int = 0
    support: int = 0
    work: int = 0
    tickets: int = 0
    review: int = 0
    disputes: int = 0  # open disputes (staff)


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

    async def find_order_conversation(self, order_id: int) -> Conversation | None:
        """Read-only: None until somebody opens the chat."""

    async def order_conversation(self, order_id: int) -> Conversation:
        """Get or create; safe against two concurrent creators."""

    async def message(self, message_id: int) -> Message | None: ...

    async def message_by_copy(self, tg_chat_id: int, tg_message_id: int) -> Message | None: ...

    async def messages_page(
        self, conversation_id: int, before_id: int | None, limit: int
    ) -> list[Message]:
        """The `limit` messages before `before_id` (the newest ones when None), oldest first."""

    async def tickets(
        self, status: TicketStatus | None, manager_id: int | None, limit: int
    ) -> list[Ticket]:
        """Newest first; each filter applies only when given."""

    async def mark_read(self, conversation_id: int, user_id: int, message_id: int) -> None:
        """Moves the read mark forward only: a late request never takes it back."""

    async def unread_by_order(self, user_id: int, order_ids: Collection[int]) -> dict[int, int]:
        """Unread messages (not his own) per order chat; chats with none are absent."""

    async def unread_by_ticket(self, user_id: int, ticket_ids: Collection[int]) -> dict[int, int]:
        """Unread messages (not his own) per ticket chat; chats with none are absent."""

    async def unread_counts(
        self, user_id: int, staff: bool, chat_statuses: Collection[OrderStatus]
    ) -> UnreadCounts:
        """The tab counters in one query. Order chats count only while `chat_statuses` holds;
        staff counters (open tickets nobody took + his own, orders to check) only for `staff`."""
