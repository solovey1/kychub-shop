"""Response bodies of the Mini App API. Money is a string ("12.50"), time is ISO 8601 UTC.
Nothing here carries the buyer's id, name or username: executors read these too."""

from datetime import datetime
from decimal import Decimal

from pydantic import Field

from app.application.i18n_text import pick_i18n
from app.application.models.base import PydanticModel
from app.domain.enums.order import OrderStatus
from app.domain.ledger import LedgerEntry
from app.domain.order import Order


def usd(amount: Decimal) -> str:
    return f"{amount:.2f}"


class WalletOut(PydanticModel):
    hold: str
    available: str


class MeOut(PydanticModel):
    id: int
    name: str
    language: str
    roles: list[str]
    balance: str
    executor: WalletOut | None = None


class OrderBrief(PydanticModel):
    id: int
    status: OrderStatus
    product: str
    variant: str
    country: str | None
    total: str
    created_at: datetime

    @classmethod
    def of(cls, order: Order, locale: str) -> "OrderBrief":
        snap = order.snapshot
        variant = snap.get("variant") or {}
        return cls(
            id=order.id,
            status=order.status,
            product=pick_i18n(snap.get("product"), locale),
            variant=pick_i18n(variant.get("title"), locale),
            country=variant.get("country"),
            total=usd(order.price - order.discount),
            created_at=order.created_at,
        )


class OrderOut(OrderBrief):
    executor_alias: str | None = None
    result: str | None = None  # only once the order is completed
    result_files: int = 0
    can_cancel: bool = False


class OrderListOut(PydanticModel):
    items: list[OrderBrief]
    total: int
    page: int
    page_size: int


class CancelOut(PydanticModel):
    order_id: int
    refunded: str


class LedgerEntryOut(PydanticModel):
    id: int
    kind: str
    amount: str
    balance_after: str
    order_id: int | None
    created_at: datetime

    @classmethod
    def of(cls, entry: LedgerEntry) -> "LedgerEntryOut":
        return cls(
            id=entry.id,
            kind=entry.kind.value,
            amount=usd(entry.amount),
            balance_after=usd(entry.balance_after),
            order_id=entry.order_id,
            created_at=entry.created_at,
        )


class BalanceOut(PydanticModel):
    balance: str
    entries: list[LedgerEntryOut]


class BuyerExecutorOut(PydanticModel):
    alias: str
    completed: int


class ConversationOut(PydanticModel):
    conversation_id: int
    can_post: bool


class TicketRefOut(PydanticModel):
    ticket_id: int
    conversation_id: int
    created: bool


class SupportIn(PydanticModel):
    order_id: int | None = None


class PostMessageIn(PydanticModel):
    text: str = Field(min_length=1, max_length=4000)


class MessageOut(PydanticModel):
    """Same fields as the `message` event of the WebSocket (`message_view`)."""

    id: int
    sender_role: str
    mine: bool
    text: str | None
    media_type: str | None
    created_at: datetime


class MessagesOut(PydanticModel):
    items: list[MessageOut]  # oldest first
    has_more: bool
    can_post: bool
