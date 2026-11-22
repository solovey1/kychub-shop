from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Query

from app.application.errors.shop import OrderUnavailable
from app.application.interactors.attention import AttentionInteractor
from app.application.interactors.balance import BalanceInteractor
from app.application.interactors.cancel_request import CancelRequestInteractor, cancel_state
from app.application.interactors.catalog import PAGE_SIZE
from app.application.interactors.conversations import ConversationInteractor
from app.application.interactors.deadlines import ExtensionInteractor, extended_deadline
from app.application.interactors.disputes import DISPUTE_STATUSES, DisputeInteractor
from app.application.interactors.feedback import ReviewInteractor
from app.application.interactors.info_state import pending_info
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.interactors.orders import OrdersInteractor
from app.domain.enums.order import OrderStatus
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.presentation.fastapi.api.auth import CurrentUser
from app.presentation.fastapi.api.schemas import (
    BalanceOut,
    CancelOut,
    CancelRequestOut,
    DisputeIn,
    DisputeOut,
    ExecutorRatingOut,
    ExtensionAnswerIn,
    ExtensionAskOut,
    InfoOut,
    LedgerEntryOut,
    OrderBrief,
    OrderChatOut,
    OrderListOut,
    OrderOut,
    RateIn,
    usd,
)
from app.utils.time import datetime_now

router: APIRouter = APIRouter(tags=["buyer"])

BALANCE_ENTRIES = 50


@router.get("/orders")
@inject
async def list_orders(
    user: CurrentUser,
    orders: FromDishka[OrdersInteractor],
    chat: FromDishka[ConversationInteractor],
    attention: FromDishka[AttentionInteractor],
    page: int = Query(0, ge=0),
) -> OrderListOut:
    items, total, page = await orders.list_orders(user.id, page)
    unread = await chat.unread_by_order(user.id, items)
    actions = await attention.buyer_actions(items)
    return OrderListOut(
        items=[
            OrderBrief.of(order, user.language, unread.get(order.id, 0), actions.get(order.id))
            for order in items
        ],
        total=total,
        page=page,
        page_size=PAGE_SIZE,
    )


async def _order(
    order_id: int, user: User, orders: OrdersInteractor, chat: ConversationInteractor
) -> OrderOut:
    order = await orders.get(user.id, order_id)
    if order is None:
        raise HTTPException(404, "Not found")
    pending = await orders.pending_extension(order)
    done = order.status in (OrderStatus.ready, OrderStatus.completed) and order.result is not None
    result = order.result or {}
    reserved = await orders.reserved(order)
    dispute = await orders.dispute(order)
    events = await orders.events(order_id)
    cancel = cancel_state(events)
    info = pending_info(order, events) if dispute is None else None
    score = await orders.rating(order)
    avg, count = await orders.executor_rating(order)
    asking = order.status is OrderStatus.assigned and dispute is None
    return OrderOut(
        **OrderBrief.of(order, user.language).model_dump(),
        executor_alias=await orders.executor_alias(order),
        chat=OrderChatOut.of(await chat.order_chat_summary(user.id, order_id), user.id),
        result=str(result.get("text", "")) if done else None,
        result_files=len(result.get("files", [])) if done else 0,
        can_cancel=order.status is OrderStatus.in_queue,
        can_confirm=order.status is OrderStatus.ready and dispute is None,
        can_dispute=order.status in DISPUTE_STATUSES
        and dispute is None
        and order.accept_until is None,
        dispute=DisputeOut.of(dispute) if dispute else None,
        confirm_at=await orders.confirm_at(order),
        reserved=usd(reserved) if reserved > 0 else None,
        extension=ExtensionAskOut(
            request_id=pending.request_id,
            minutes=pending.minutes,
            until=extended_deadline(order, pending.minutes, datetime_now()),
        )
        if pending is not None and order.deadline_at is not None
        else None,
        deadline_at=order.deadline_at if order.status is OrderStatus.assigned else None,
        info=InfoOut(question=info.question, asked_at=info.asked_at, until=info.until)
        if info
        else None,
        executor_rating=ExecutorRatingOut(score=avg, count=count) if order.executor_id else None,
        can_rate=order.status is OrderStatus.completed
        and order.executor_id is not None
        and score is None,
        rating=score,
        intro=await orders.count(user.id) == 1,
        can_ask_cancel=asking and cancel.can_request,
        cancel_request=CancelRequestOut(
            request_id=cancel.pending.request_id, until=cancel.pending.agrees_at
        )
        if asking and cancel.pending is not None
        else None,
    )


@router.get("/orders/{order_id}")
@inject
async def get_order(
    order_id: int,
    user: CurrentUser,
    orders: FromDishka[OrdersInteractor],
    chat: FromDishka[ConversationInteractor],
) -> OrderOut:
    return await _order(order_id, user, orders, chat)


@router.post("/orders/{order_id}/extension")
@inject
async def answer_extension(
    order_id: int,
    body: ExtensionAnswerIn,
    user: CurrentUser,
    orders: FromDishka[OrdersInteractor],
    chat: FromDishka[ConversationInteractor],
    extension: FromDishka[ExtensionInteractor],
    effects: FromDishka[Effects],
) -> OrderOut:
    """Conflict `extension_stale` (409): the request is gone, nothing changed."""
    answer = await extension.answer(user.id, order_id, body.request_id, body.approve)
    await effects.extension_answered(answer)
    return await _order(order_id, user, orders, chat)


@router.post("/orders/{order_id}/cancel-request")
@inject
async def ask_cancel(
    order_id: int,
    user: CurrentUser,
    orders: FromDishka[OrdersInteractor],
    chat: FromDishka[ConversationInteractor],
    cancel_requests: FromDishka[CancelRequestInteractor],
    effects: FromDishka[Effects],
) -> OrderOut:
    """Ask the executor of an assigned order to agree to a cancellation. Conflict
    `cancel_pending` / `cancel_limit` / `dispute_open` (409); not his order, or not assigned:
    404."""
    try:
        ask = await cancel_requests.request(user.id, order_id)
    except OrderUnavailable:
        raise HTTPException(404, "Not found") from None
    await effects.cancel_asked(ask)
    return await _order(order_id, user, orders, chat)


@router.post("/orders/{order_id}/confirm")
@inject
async def confirm_order(
    order_id: int,
    user: CurrentUser,
    orders: FromDishka[OrdersInteractor],
    chat: FromDishka[ConversationInteractor],
    review: FromDishka[OrderReviewInteractor],
    effects: FromDishka[Effects],
) -> OrderOut:
    """The buyer: everything is fine. Confirmed already (by him, support or the timer): 404;
    a dispute is open: 409 `dispute_open`."""
    order = await review.confirm_by_buyer(user.id, order_id)
    await effects.order_confirmed(order, ask_rating=True)
    return await _order(order_id, user, orders, chat)


@router.post("/orders/{order_id}/rate")
@inject
async def rate_order(
    order_id: int,
    body: RateIn,
    user: CurrentUser,
    orders: FromDishka[OrdersInteractor],
    chat: FromDishka[ConversationInteractor],
    reviews: FromDishka[ReviewInteractor],
) -> OrderOut:
    """1..5 stars for a completed order. Rated already: 400 `AlreadyRated`; a wrong score: 422;
    not his order, or not completed: 404."""
    await reviews.rate(user.id, order_id, body.score)
    return await _order(order_id, user, orders, chat)


@router.post("/orders/{order_id}/dispute")
@inject
async def open_dispute(
    order_id: int,
    body: DisputeIn,
    user: CurrentUser,
    orders: FromDishka[OrdersInteractor],
    chat: FromDishka[ConversationInteractor],
    disputes: FromDishka[DisputeInteractor],
    effects: FromDishka[Effects],
) -> OrderOut:
    """Call support. Conflict `dispute_open` (409); somebody else's order, or one that is not
    assigned / submitted: 404."""
    news = await disputes.open(user.id, order_id, body.reason)
    await effects.dispute_opened(news)
    return await _order(order_id, user, orders, chat)


@router.post("/orders/{order_id}/cancel")
@inject
async def cancel_order(
    order_id: int,
    user: CurrentUser,
    orders: FromDishka[OrdersInteractor],
    effects: FromDishka[Effects],
) -> CancelOut:
    try:
        refund = await orders.cancel(user.id, order_id)
    except OrderUnavailable:  # not yours, or taken meanwhile
        raise HTTPException(404, "Not found") from None
    await effects.order_cancelled(order_id)
    return CancelOut(order_id=order_id, refunded=usd(refund.amount))


@router.get("/balance")
@inject
async def balance(user: CurrentUser, interactor: FromDishka[BalanceInteractor]) -> BalanceOut:
    amount, entries = await interactor.summary(user.id, BALANCE_ENTRIES)
    held = await interactor.held(user.id)
    return BalanceOut(
        balance=usd(amount),
        hold=usd(held),
        entries=[LedgerEntryOut.of(entry) for entry in entries],
    )
