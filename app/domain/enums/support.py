from enum import StrEnum


class TicketStatus(StrEnum):
    open = "open"
    taken = "taken"
    closed = "closed"


class ConversationKind(StrEnum):
    ticket = "ticket"
    order = "order"
