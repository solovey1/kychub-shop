from enum import StrEnum


class TicketStatus(StrEnum):
    open = "open"
    taken = "taken"
    closed = "closed"


class ConversationKind(StrEnum):
    ticket = "ticket"
    order = "order"


class ChatRole(StrEnum):
    """Who is writing in a conversation; also stored as `Message.sender_role`."""

    buyer = "buyer"
    executor = "executor"
    manager = "manager"
    admin = "admin"
