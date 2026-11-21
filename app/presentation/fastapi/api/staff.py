from typing import Literal

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Query

from app.application.interactors.conversations import ConversationInteractor
from app.application.interactors.order_review import OrderReviewInteractor
from app.domain.enums.order import OrderStatus
from app.domain.enums.roles import Role
from app.infrastructure.telegram.effects import Effects
from app.presentation.fastapi.api.auth import StaffUser
from app.presentation.fastapi.api.schemas import (
    CancelOut,
    OrderBrief,
    SendBackIn,
    StaffOrderBrief,
    StaffOrderOut,
    TicketOut,
    card_fields,
    usd,
)

router: APIRouter = APIRouter(tags=["staff"])

LIST_LIMIT = 100


@router.get("/tickets")
@inject
async def tickets(
    user: StaffUser,
    chat: FromDishka[ConversationInteractor],
    scope: Literal["open", "mine", "all"] = "open",
) -> list[TicketOut]:
    if scope == "all" and not user.roles & Role.ADMIN:
        raise HTTPException(403, "Forbidden")
    return [
        TicketOut(
            id=ticket.id,
            status=ticket.status.value,
            order_id=ticket.order_id,
            buyer_name=name,
            mine=ticket.manager_id == user.id,
            conversation_id=conversation_id,
            created_at=ticket.created_at,
        )
        for ticket, name, conversation_id in await chat.list_tickets(user.id, scope)
    ]


@router.post("/tickets/{ticket_id}/take")
@inject
async def take_ticket(
    ticket_id: int,
    user: StaffUser,
    chat: FromDishka[ConversationInteractor],
    effects: FromDishka[Effects],
) -> dict[str, int]:
    if not await chat.take_ticket(user.id, ticket_id):  # taken by someone else, closed, missing
        raise HTTPException(409, "Ticket is not available")
    card = await chat.ticket_card(ticket_id)
    assert card is not None
    await effects.ticket_taken(card[0], user.id, user.name)
    return {"conversation_id": (await chat.ticket_conversation(ticket_id)).id}


@router.post("/tickets/{ticket_id}/close")
@inject
async def close_ticket(
    ticket_id: int,
    user: StaffUser,
    chat: FromDishka[ConversationInteractor],
    effects: FromDishka[Effects],
) -> dict[str, bool]:
    ticket = await chat.close_ticket(user.id, ticket_id)  # TicketUnavailable -> 404
    await effects.ticket_closed(ticket, user.id)
    return {"ok": True}


@router.get("/staff/orders")
@inject
async def staff_orders(
    user: StaffUser,
    review: FromDishka[OrderReviewInteractor],
    status: OrderStatus = Query(OrderStatus.ready),
) -> list[StaffOrderBrief]:
    return [
        StaffOrderBrief(
            **OrderBrief.of(order, user.language).model_dump(),
            executor_id=order.executor_id,
            ready_at=order.ready_at,
        )
        for order in await review.list_by_status(status, LIST_LIMIT)
    ]


@router.get("/staff/orders/{order_id}")
@inject
async def staff_order(
    order_id: int, user: StaffUser, review: FromDishka[OrderReviewInteractor]
) -> StaffOrderOut:
    view = await review.get(order_id)
    if view is None:
        raise HTTPException(404, "Not found")
    return StaffOrderOut(
        **OrderBrief.of(view.order, user.language).model_dump(),
        executor_id=view.order.executor_id,
        ready_at=view.order.ready_at,
        earning=usd(view.card.earning),
        fields=card_fields(view.card, user.language),
        result=view.text,
        result_files=len(view.files),
    )


@router.post("/staff/orders/{order_id}/confirm")
@inject
async def confirm(
    order_id: int,
    user: StaffUser,
    review: FromDishka[OrderReviewInteractor],
    effects: FromDishka[Effects],
) -> dict[str, bool]:
    order = await review.confirm(user.id, order_id)  # a second confirm: OrderUnavailable -> 404
    await effects.order_confirmed(order)
    return {"ok": True}


@router.post("/staff/orders/{order_id}/send_back")
@inject
async def send_back(
    order_id: int,
    body: SendBackIn,
    user: StaffUser,
    review: FromDishka[OrderReviewInteractor],
    effects: FromDishka[Effects],
) -> dict[str, bool]:
    comment = body.comment.strip()
    if not comment:
        raise HTTPException(422, "Empty comment")
    order = await review.send_back(user.id, order_id, comment)
    await effects.order_sent_back(order, comment)
    return {"ok": True}


@router.post("/staff/orders/{order_id}/fail")
@inject
async def fail(
    order_id: int,
    user: StaffUser,
    review: FromDishka[OrderReviewInteractor],
    effects: FromDishka[Effects],
) -> CancelOut:
    refund = await review.fail_and_refund(user.id, order_id, "manual")
    await effects.order_failed(refund)
    return CancelOut(order_id=order_id, refunded=usd(refund.amount))
