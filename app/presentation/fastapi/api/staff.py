from html import unescape
from typing import Literal

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Query

from app.application.interactors.conversations import ConversationInteractor
from app.application.interactors.disputes import DisputeInteractor
from app.application.interactors.order_review import OrderReviewInteractor
from app.domain.enums.order import OrderStatus
from app.domain.enums.roles import Role
from app.domain.support import Ticket
from app.infrastructure.telegram.effects import Effects
from app.presentation.fastapi.api.auth import CurrentUser, StaffUser
from app.presentation.fastapi.api.schemas import (
    CancelOut,
    DisputeOut,
    DisputeRowOut,
    HandoverIn,
    OrderBrief,
    ReplyRequestIn,
    SendBackIn,
    StaffMemberOut,
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
    rows = await chat.list_tickets(user.id, scope)
    unread = await chat.unread_by_ticket(user.id, [row[0] for row in rows])
    return [
        _ticket_out(ticket, name, conversation_id, user.id, unread.get(ticket.id, 0))
        for ticket, name, conversation_id in rows
    ]


def _ticket_out(
    ticket: Ticket, name: str, conversation_id: int, user_id: int, unread: int
) -> TicketOut:
    return TicketOut(
        id=ticket.id,
        status=ticket.status.value,
        order_id=ticket.order_id,
        buyer_name=unescape(name),
        mine=ticket.manager_id == user_id,
        conversation_id=conversation_id,
        created_at=ticket.created_at,
        unread=unread,
    )


@router.get("/tickets/{ticket_id}")
@inject
async def get_ticket(
    ticket_id: int, user: CurrentUser, chat: FromDishka[ConversationInteractor]
) -> TicketOut:
    """Whoever may read the ticket chat; anyone else gets the same 404 as for a missing one."""
    card = await chat.ticket_card(ticket_id)
    if card is None:
        raise HTTPException(404, "Not found")
    conversation = await chat.ticket_conversation(ticket_id)
    if await chat.reader_role(user.id, conversation) is None:
        raise HTTPException(404, "Not found")
    unread = await chat.unread_by_ticket(user.id, [card[0]])
    return _ticket_out(card[0], card[1], conversation.id, user.id, unread.get(ticket_id, 0))


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
    conversation = await chat.ticket_conversation(ticket_id)
    await effects.ticket_taken(card[0], conversation.id, user.id, user.name)
    return {"conversation_id": conversation.id}


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


@router.get("/staff/managers")
@inject
async def managers(_: StaffUser, chat: FromDishka[ConversationInteractor]) -> list[StaffMemberOut]:
    """Who a ticket can be handed to."""
    return [
        StaffMemberOut(id=u.id, name=unescape(u.name), admin=bool(u.roles & Role.ADMIN))
        for u in await chat.staff()
    ]


@router.post("/tickets/{ticket_id}/handover")
@inject
async def hand_over(
    ticket_id: int,
    body: HandoverIn,
    user: StaffUser,
    chat: FromDishka[ConversationInteractor],
    effects: FromDishka[Effects],
) -> dict[str, bool]:
    ticket, previous = await chat.hand_over(user.id, ticket_id, body.manager_id)
    conversation = await chat.ticket_conversation(ticket_id)
    await effects.ticket_handed_over(ticket, conversation.id, previous)
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
    order_id: int,
    user: StaffUser,
    review: FromDishka[OrderReviewInteractor],
    disputes: FromDishka[DisputeInteractor],
) -> StaffOrderOut:
    view = await review.get(order_id)
    if view is None:
        raise HTTPException(404, "Not found")
    dispute = await disputes.current(order_id)
    return StaffOrderOut(
        **OrderBrief.of(view.order, user.language).model_dump(),
        executor_id=view.order.executor_id,
        executor_alias=view.executor_alias,
        ready_at=view.order.ready_at,
        earning=usd(view.card.earning),
        fields=card_fields(view.card, user.language),
        result=view.text,
        result_files=len(view.files),
        dispute=DisputeOut.of(dispute, staff=True) if dispute else None,
    )


@router.get("/staff/disputes")
@inject
async def staff_disputes(
    user: StaffUser, disputes: FromDishka[DisputeInteractor]
) -> list[DisputeRowOut]:
    rows = []
    for dispute, order in await disputes.open_rows():
        brief = OrderBrief.of(order, user.language)
        rows.append(
            DisputeRowOut(
                order_id=order.id,
                status=order.status,
                product=brief.product,
                variant=brief.variant,
                country=brief.country,
                opened_role=dispute.opened_role,
                awaiting_role=dispute.awaiting_role,
                awaiting_until=dispute.awaiting_until,
                opened_at=dispute.opened_at,
            )
        )
    return rows


@router.post("/staff/orders/{order_id}/dispute/request")
@inject
async def request_reply(
    order_id: int,
    body: ReplyRequestIn,
    user: StaffUser,
    disputes: FromDishka[DisputeInteractor],
    effects: FromDishka[Effects],
) -> dict[str, bool]:
    """Ask the buyer or the executor to answer in the chat: the wait starts again."""
    news = await disputes.request_reply(user.id, order_id, body.side)  # no dispute: 404
    await effects.dispute_reply_requested(news)
    return {"ok": True}


@router.post("/staff/orders/{order_id}/dispute/close")
@inject
async def close_dispute(
    order_id: int,
    user: StaffUser,
    disputes: FromDishka[DisputeInteractor],
    effects: FromDishka[Effects],
) -> dict[str, bool]:
    """Close the dispute without touching the order, which goes on."""
    news = await disputes.close(user.id, order_id)  # already closed: 404
    await effects.dispute_closed(news)
    return {"ok": True}


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
