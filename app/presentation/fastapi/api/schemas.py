"""Response bodies of the Mini App API. Money is a string ("12.50"), time is ISO 8601 UTC.
Nothing here carries the buyer's id, name or username: executors read these too."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.application.cards import OrderCard
from app.application.i18n_text import pick_i18n
from app.application.models.base import PydanticModel
from app.domain.dispute import Dispute
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
    hold: str
    executor: WalletOut | None = None


class OrderBrief(PydanticModel):
    id: int
    status: OrderStatus
    product: str
    variant: str
    country: str | None
    total: str
    created_at: datetime
    unread: int = 0  # messages in the order chat the buyer has not read

    @classmethod
    def of(cls, order: Order, locale: str, unread: int = 0) -> "OrderBrief":
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
            unread=unread,
        )


class ExtensionAskOut(PydanticModel):
    """What the buyer is asked: more time for the executor, and the deadline he would get."""

    request_id: int
    minutes: int
    until: datetime


class ExtensionAnswerIn(PydanticModel):
    request_id: int
    approve: bool


class ExtensionRequestIn(PydanticModel):
    minutes: int


class ExtensionStateOut(PydanticModel):
    pending_minutes: int | None  # a request waits for the buyer
    can_request: bool
    options: list[int]


class DisputeOut(PydanticModel):
    """An open dispute. `reason` is for support only: the other side never reads it."""

    opened_role: str
    awaiting_role: str | None
    awaiting_until: datetime | None
    opened_at: datetime
    reason: str | None = None

    @classmethod
    def of(cls, dispute: Dispute, *, staff: bool = False) -> "DisputeOut":
        return cls(
            opened_role=dispute.opened_role,
            awaiting_role=dispute.awaiting_role,
            awaiting_until=dispute.awaiting_until,
            opened_at=dispute.opened_at,
            reason=dispute.reason if staff else None,
        )


class DisputeIn(PydanticModel):
    reason: str | None = Field(None, max_length=500)


class ReplyRequestIn(PydanticModel):
    side: Literal["buyer", "executor"]


class DisputeRowOut(PydanticModel):
    order_id: int
    status: OrderStatus
    product: str
    variant: str
    country: str | None
    opened_role: str
    awaiting_role: str | None
    awaiting_until: datetime | None
    opened_at: datetime


class OrderOut(OrderBrief):
    executor_alias: str | None = None
    result: str | None = None  # from the moment the executor is done (ready) on
    result_files: int = 0
    can_confirm: bool = False  # ready: the buyer may say «everything is fine»
    can_dispute: bool = False  # assigned or ready, no open dispute
    dispute: DisputeOut | None = None
    confirm_at: datetime | None = None  # ready: when it confirms itself
    can_cancel: bool = False
    reserved: str | None = None  # still held for this order, not charged yet
    extension: ExtensionAskOut | None = None


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
    hold: str
    entries: list[LedgerEntryOut]


class UnreadOut(PydanticModel):
    orders: int
    support: int
    work: int
    tickets: int
    review: int
    disputes: int


class ReadIn(PydanticModel):
    message_id: int = Field(ge=1)


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


class CardFieldOut(PydanticModel):
    label: str
    value: str | None  # None for a file: files are not served to the Mini App
    is_file: bool = False


class ResultFieldOut(PydanticModel):
    key: str
    label: str
    type: str
    required: bool
    options: list[str] | None
    max_length: int


class ExecutorOrderBrief(PydanticModel):
    """No buyer data and no price the buyer paid: the executor sees his earning."""

    id: int
    status: OrderStatus
    product: str
    country: str | None
    earning: str
    deadline_minutes: int


class ExecutorOrderOut(ExecutorOrderBrief):
    deadline_at: datetime | None = None
    fields: list[CardFieldOut]
    result_form: list[ResultFieldOut] | None = None  # while the order waits for a result
    result: dict[str, str] | None = None  # what the executor handed in
    extension: ExtensionStateOut | None = None  # only while the order is assigned
    can_dispute: bool = False
    dispute: DisputeOut | None = None


class ExecutorOrderListItem(PydanticModel):
    id: int
    status: OrderStatus
    product: str
    variant: str
    country: str | None
    deadline_at: datetime | None
    unread: int = 0


class ExecutorOrderListOut(PydanticModel):
    items: list[ExecutorOrderListItem]
    total: int
    page: int
    page_size: int


class ResultIn(PydanticModel):
    fields: dict[str, str]


class StatsOut(PydanticModel):
    completed: int
    failed: int
    overdue: int
    refused: int
    avg_minutes: float | None
    avg_score: float | None


class WalletDetailOut(PydanticModel):
    hold: str
    available: str
    wallet: str | None
    minimum: str
    entries: list[LedgerEntryOut]


class OnlineIn(PydanticModel):
    online: bool


class OnlineOut(PydanticModel):
    online: bool


class WalletIn(PydanticModel):
    address: str = Field(min_length=1, max_length=128)


class WithdrawalOut(PydanticModel):
    id: int
    amount: str
    address: str


class TicketOut(PydanticModel):
    id: int
    status: str
    order_id: int | None
    buyer_name: str  # staff only
    mine: bool
    conversation_id: int
    created_at: datetime
    unread: int = 0


class SendBackIn(PydanticModel):
    comment: str = Field(min_length=1, max_length=1000)


class StaffOrderBrief(OrderBrief):
    executor_id: int | None
    ready_at: datetime | None


class StaffOrderOut(StaffOrderBrief):
    executor_alias: str | None
    earning: str
    fields: list[CardFieldOut]  # includes the fields hidden from executors
    result: str
    result_files: int
    dispute: DisputeOut | None = None


def card_fields(card: OrderCard, locale: str) -> list[CardFieldOut]:
    return [
        CardFieldOut(
            label=pick_i18n(f.label, locale),
            value=None if f.is_file else f.value,
            is_file=f.is_file,
        )
        for f in card.fields
    ]


def card_brief(card: OrderCard, status: OrderStatus, locale: str) -> dict[str, object]:
    return {
        "id": card.order_id,
        "status": status,
        "product": pick_i18n(card.product, locale),
        "country": card.country_code,
        "earning": usd(card.earning),
        "deadline_minutes": card.deadline_minutes,
    }


class StaffMemberOut(PydanticModel):
    id: int
    name: str
    admin: bool


class HandoverIn(PydanticModel):
    manager_id: int
