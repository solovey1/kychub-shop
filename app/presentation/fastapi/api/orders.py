from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Query

from app.application.errors.shop import OrderUnavailable
from app.application.interactors.balance import BalanceInteractor
from app.application.interactors.catalog import PAGE_SIZE
from app.application.interactors.conversations import ConversationInteractor
from app.application.interactors.orders import OrdersInteractor
from app.domain.enums.order import OrderStatus
from app.infrastructure.telegram.effects import Effects
from app.presentation.fastapi.api.auth import CurrentUser
from app.presentation.fastapi.api.schemas import (
    BalanceOut,
    CancelOut,
    LedgerEntryOut,
    OrderBrief,
    OrderListOut,
    OrderOut,
    usd,
)

router: APIRouter = APIRouter(tags=["buyer"])

BALANCE_ENTRIES = 50


@router.get("/orders")
@inject
async def list_orders(
    user: CurrentUser,
    orders: FromDishka[OrdersInteractor],
    chat: FromDishka[ConversationInteractor],
    page: int = Query(0, ge=0),
) -> OrderListOut:
    items, total, page = await orders.list_orders(user.id, page)
    unread = await chat.unread_by_order(user.id, items)
    return OrderListOut(
        items=[OrderBrief.of(order, user.language, unread.get(order.id, 0)) for order in items],
        total=total,
        page=page,
        page_size=PAGE_SIZE,
    )


@router.get("/orders/{order_id}")
@inject
async def get_order(
    order_id: int, user: CurrentUser, orders: FromDishka[OrdersInteractor]
) -> OrderOut:
    order = await orders.get(user.id, order_id)
    if order is None:
        raise HTTPException(404, "Not found")
    done = order.status is OrderStatus.completed and order.result is not None
    result = order.result or {}
    return OrderOut(
        **OrderBrief.of(order, user.language).model_dump(),
        executor_alias=await orders.executor_alias(order),
        result=str(result.get("text", "")) if done else None,
        result_files=len(result.get("files", [])) if done else 0,
        can_cancel=order.status is OrderStatus.in_queue,
    )


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
    return BalanceOut(balance=usd(amount), entries=[LedgerEntryOut.of(entry) for entry in entries])
