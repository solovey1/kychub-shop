from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Query

from app.application.interactors.admin.orders import PAGE_SIZE, OrdersAdminInteractor
from app.application.interactors.dispatch import DispatchInteractor
from app.application.interactors.order_review import OrderReviewInteractor
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.infrastructure.telegram.effects import Effects
from app.presentation.fastapi.api.admin.schemas import (
    AdminOrderOut,
    AdminOrderPage,
    AdminOrderRow,
    AssignableOut,
    AssignIn,
    OkOut,
    OrderEntryOut,
    OrderEventOut,
    RefundIn,
)
from app.presentation.fastapi.api.auth import StaffUser
from app.presentation.fastapi.api.schemas import CancelOut, OrderBrief, card_fields, usd

router: APIRouter = APIRouter(tags=["admin-orders"])
Orders = FromDishka[OrdersAdminInteractor]


def _row(order: Order, alias: str | None, locale: str) -> AdminOrderRow:
    brief = OrderBrief.of(order, locale)
    return AdminOrderRow(
        id=order.id,
        status=order.status.value,
        product=brief.product,
        variant=brief.variant,
        country=brief.country,
        total=brief.total,
        created_at=order.created_at,
        buyer_id=order.user_id,
        executor_alias=alias,
    )


@router.get("/orders")
@inject
async def orders(
    user: StaffUser,
    interactor: Orders,
    status: OrderStatus | None = None,
    product_id: int | None = None,
    buyer_id: int | None = None,
    executor_id: int | None = None,
    page: int = Query(0, ge=0),
) -> AdminOrderPage:
    items, aliases, total = await interactor.listing(
        status, product_id, buyer_id, executor_id, page
    )
    return AdminOrderPage(
        items=[_row(o, aliases.get(o.executor_id or 0), user.language) for o in items],
        total=total,
        page=page,
        page_size=PAGE_SIZE,
    )


@router.get("/orders/{order_id}")
@inject
async def order(order_id: int, user: StaffUser, interactor: Orders) -> AdminOrderOut:
    d = await interactor.detail(order_id)
    result = d.order.result or {}
    return AdminOrderOut(
        **_row(d.order, d.executor_alias, user.language).model_dump(),
        buyer_name=d.buyer_name,
        executor_id=d.order.executor_id,
        price=usd(d.order.price),
        discount=usd(d.order.discount),
        assigned_at=d.order.assigned_at,
        deadline_at=d.order.deadline_at,
        ready_at=d.order.ready_at,
        completed_at=d.order.completed_at,
        fields=card_fields(d.card, user.language),
        result=str(result.get("text", "")),
        result_files=len(result.get("files", [])),
        events=[
            OrderEventOut(
                id=e.id,
                type=e.type,
                actor_id=e.actor_id,
                payload=e.payload,
                created_at=e.created_at,
            )
            for e in d.events
        ],
        entries=[
            OrderEntryOut(
                id=e.id,
                user_id=e.user_id,
                account=e.account.value,
                kind=e.kind.value,
                amount=usd(e.amount),
                created_at=e.created_at,
            )
            for e in d.entries
        ],
        actions=d.actions,
    )


@router.get("/orders/{order_id}/executors")
@inject
async def assignable(order_id: int, _: StaffUser, interactor: Orders) -> list[AssignableOut]:
    current = (await interactor.detail(order_id)).order.executor_id
    return [
        AssignableOut(
            id=p.user_id,
            alias=p.alias,
            load=load,
            max_parallel=p.max_parallel_orders,
            current=p.user_id == current,
        )
        for p, load in await interactor.assignable(order_id)
    ]


@router.post("/orders/{order_id}/assign")
@inject
async def assign(
    order_id: int,
    body: AssignIn,
    user: StaffUser,
    dispatch: FromDishka[DispatchInteractor],
    effects: FromDishka[Effects],
) -> OkOut:
    result = await dispatch.assign(user.id, order_id, body.executor_id, body.expected_executor_id)
    await effects.order_assigned(result)
    return OkOut()


@router.post("/orders/{order_id}/refund")
@inject
async def refund(
    order_id: int,
    body: RefundIn,
    user: StaffUser,
    review: FromDishka[OrderReviewInteractor],
    effects: FromDishka[Effects],
) -> CancelOut:
    """Failure or cancellation with a refund; the same money path as `/staff/orders/{id}/fail`."""
    result = await review.fail_and_refund(user.id, order_id, body.reason)
    await effects.order_failed(result)
    return CancelOut(order_id=order_id, refunded=usd(result.amount))
