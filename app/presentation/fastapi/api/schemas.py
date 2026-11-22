"""Response bodies of the Mini App API. Money is a string ("12.50"), time is ISO 8601 UTC.
Nothing here carries the buyer's id, name or username: executors read these too."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from app.application.cards import OrderCard
from app.application.i18n_text import pick_i18n
from app.application.interactors.conversations import OrderChat
from app.application.models.base import PydanticModel
from app.domain.dispute import Dispute
from app.domain.enums.order import OrderStatus
from app.domain.ledger import LedgerEntry
from app.domain.order import Order
from app.infrastructure.events import message_view


def usd(amount: Decimal) -> str:
    return f"{amount:.2f}"


class WalletOut(PydanticModel):
    hold: str
    available: str


class MeOut(PydanticModel):
    id: int
    name: str
    language: str
    timezone: str | None = None
    roles: list[str]
    balance: str
    hold: str
    executor: WalletOut | None = None


class TimezoneIn(PydanticModel):
    timezone: str = Field(max_length=64)


class OrderBrief(PydanticModel):
    id: int
    code: str  # what people read as the order number
    status: OrderStatus
    product: str
    variant: str
    country: str | None
    total: str
    created_at: datetime
    unread: int = 0  # messages in the order chat the buyer has not read
    action: Literal["confirm", "extension", "dispute", "info"] | None = (
        None  # what waits for him (lists)
    )

    @classmethod
    def of(
        cls,
        order: Order,
        locale: str,
        unread: int = 0,
        action: Literal["confirm", "extension", "dispute", "info"] | None = None,
    ) -> "OrderBrief":
        snap = order.snapshot
        variant = snap.get("variant") or {}
        return cls(
            id=order.id,
            code=order.code,
            status=order.status,
            product=pick_i18n(snap.get("product"), locale),
            variant=pick_i18n(variant.get("title"), locale),
            country=variant.get("country"),
            total=usd(order.price - order.discount),
            created_at=order.created_at,
            unread=unread,
            action=action,
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


class InfoIn(PydanticModel):
    question: str = Field(max_length=300)


class InfoOut(PydanticModel):
    """«Need data»: the question waits for the buyer, who has until `until`; the order is on
    pause meanwhile."""

    question: str
    asked_at: datetime
    until: datetime


class ExtensionStateOut(PydanticModel):
    pending_minutes: int | None  # a request waits for the buyer
    can_request: bool
    options: list[int]


class CancelRequestOut(PydanticModel):
    """A cancel request that waits for the executor: it agrees by itself at `until`."""

    request_id: int
    until: datetime


class CancelAnswerIn(PydanticModel):
    request_id: int
    agree: bool


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
    order_code: str
    status: OrderStatus
    product: str
    variant: str
    country: str | None
    opened_role: str
    awaiting_role: str | None
    awaiting_until: datetime | None
    opened_at: datetime


class MessageOut(PydanticModel):
    """Same fields as the `message` event of the WebSocket (`message_view`)."""

    id: int
    sender_role: str
    mine: bool
    text: str | None
    media_type: str | None
    created_at: datetime


class OrderChatOut(PydanticModel):
    """The order chat as its reader sees it from the order card."""

    conversation_id: int
    unread: int
    last: MessageOut | None

    @classmethod
    def of(cls, chat: OrderChat | None, user_id: int) -> "OrderChatOut | None":
        if chat is None:
            return None
        last = MessageOut(**message_view(chat.last, user_id)) if chat.last else None
        return cls(conversation_id=chat.conversation_id, unread=chat.unread, last=last)


class ExecutorRatingOut(PydanticModel):
    score: float | None  # average, None while nobody rated him
    count: int


class OrderOut(OrderBrief):
    chat: OrderChatOut | None = None
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
    can_ask_cancel: bool = False  # assigned, no dispute, no open request, under the limit
    cancel_request: CancelRequestOut | None = None  # the buyer's own request, waiting
    deadline_at: datetime | None = None  # assigned and accepted: when the executor is due
    info: InfoOut | None = None  # the executor asks for data: answer in the chat
    executor_rating: ExecutorRatingOut | None = None
    can_rate: bool = False  # completed, not rated yet
    rating: int | None = None  # his score, once given
    intro: bool = False  # his only order so far: show «how it works»


class RateIn(PydanticModel):
    score: int


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
    """The tab badges. `orders` and `work` count distinct orders that need the user: an unread
    chat, or something to do (see `orders_action`, `work_action`)."""

    orders: int  # buyer: orders with an unread chat or waiting for him
    support: int
    work: int  # executor: own orders with an unread chat or assigned / a dispute to answer
    tickets: int
    review: int
    disputes: int
    orders_action: int = 0  # buyer: orders to confirm / answer an extension / answer a dispute
    work_action: int = 0  # executor: assigned orders and disputes to answer
    offers: int = 0  # executor: queue orders he may take now


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


class MessagesOut(PydanticModel):
    items: list[MessageOut]  # oldest first
    has_more: bool
    can_post: bool
    code: str  # the order or the ticket the conversation is about, as people read it


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
    code: str
    status: OrderStatus
    product: str
    country: str | None
    earning: str
    deadline_minutes: int


class ExecutorOrderOut(ExecutorOrderBrief):
    deadline_at: datetime | None = None
    accept_until: datetime | None = (
        None  # auto-assigned: confirm until then, the term starts after
    )
    fields: list[CardFieldOut]
    result_form: list[ResultFieldOut] | None = None  # while the order waits for a result
    result: dict[str, str] | None = None  # what the executor handed in
    extension: ExtensionStateOut | None = None  # only while the order is assigned
    cancel_request: CancelRequestOut | None = None  # the buyer asks to cancel: answer it
    info: InfoOut | None = None  # his question waits for the buyer, the order is paused
    can_ask_info: bool = False
    can_dispute: bool = False
    dispute: DisputeOut | None = None
    chat: OrderChatOut | None = None


class ExecutorOrderListItem(PydanticModel):
    id: int
    code: str
    status: OrderStatus
    product: str
    variant: str
    country: str | None
    deadline_at: datetime | None
    unread: int = 0
    # assigned: working; the buyer asks to cancel; a dispute waits for him
    action: Literal["work", "dispute", "cancel", "accept", "paused"] | None = None


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


class HoldDayOut(PydanticModel):
    date: str  # ISO date in the user's time zone
    amount: str


class WalletDetailOut(PydanticModel):
    hold_days: list[HoldDayOut] = []  # what turns available on which day
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
    code: str
    status: str
    order_id: int | None
    order_code: str | None
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
        "code": card.code,
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
