from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Query

from app.application.errors.shop import ExecutorNotFound, OrderUnavailable
from app.application.i18n_text import pick_i18n
from app.application.interactors.attention import AttentionInteractor
from app.application.interactors.cancel_request import CancelRequestInteractor
from app.application.interactors.catalog import PAGE_SIZE
from app.application.interactors.conversations import ConversationInteractor
from app.application.interactors.deadlines import EXTENSION_MINUTES, ExtensionInteractor
from app.application.interactors.dispatch import DispatchInteractor
from app.application.interactors.disputes import DISPUTE_STATUSES, DisputeInteractor
from app.application.interactors.executor_wallet import ExecutorWalletInteractor
from app.application.interactors.executors import ExecutorCabinetInteractor
from app.application.interactors.fulfillment_work import FulfillmentWorkInteractor
from app.application.interactors.stats import ExecutorStats
from app.application.models.form_schema import FormSchema
from app.domain.enums.order import OrderStatus
from app.infrastructure.telegram.effects import Effects
from app.presentation.fastapi.api.auth import ExecutorUser
from app.presentation.fastapi.api.schemas import (
    CancelAnswerIn,
    CancelRequestOut,
    DisputeIn,
    DisputeOut,
    ExecutorOrderBrief,
    ExecutorOrderListItem,
    ExecutorOrderListOut,
    ExecutorOrderOut,
    ExtensionRequestIn,
    ExtensionStateOut,
    LedgerEntryOut,
    OnlineIn,
    OnlineOut,
    OrderChatOut,
    ResultFieldOut,
    ResultIn,
    StatsOut,
    WalletDetailOut,
    WalletIn,
    WithdrawalOut,
    card_brief,
    card_fields,
    usd,
)
from app.utils.time import datetime_now

router: APIRouter = APIRouter(prefix="/executor", tags=["executor"])


def _form(form: FormSchema, locale: str) -> list[ResultFieldOut]:
    return [
        ResultFieldOut(
            key=f.key,
            label=pick_i18n(f.label, locale),
            type=f.type.value,
            required=f.required,
            options=f.options,
            max_length=f.max_length,
        )
        for f in form.fields
    ]


async def _order(
    order_id: int,
    user_id: int,
    locale: str,
    work: FulfillmentWorkInteractor,
    chat: ConversationInteractor,
) -> ExecutorOrderOut:
    view = await work.get(user_id, order_id)
    if view is None:  # not his order looks like a missing one
        raise HTTPException(404, "Not found")
    form = None
    if view.order.status is OrderStatus.assigned:
        form = _form(await work.result_form(user_id, order_id), locale)
    result = view.order.result
    assigned = view.order.status is OrderStatus.assigned
    ext = view.extension
    return ExecutorOrderOut(
        **card_brief(view.card, view.order.status, locale),
        deadline_at=view.order.deadline_at,
        accept_until=view.order.accept_until if assigned else None,
        fields=card_fields(view.card, locale),
        result_form=form,
        result=dict(result.get("fields", {})) if result else None,
        extension=ExtensionStateOut(
            pending_minutes=ext.pending.minutes if ext.pending else None,
            can_request=ext.can_request
            and view.order.deadline_at is not None
            and view.order.deadline_at > datetime_now(),
            options=list(EXTENSION_MINUTES),
        )
        if assigned
        else None,
        cancel_request=CancelRequestOut(
            request_id=view.cancel.pending.request_id, until=view.cancel.pending.agrees_at
        )
        if assigned and view.dispute is None and view.cancel.pending is not None
        else None,
        can_dispute=view.order.status in DISPUTE_STATUSES and view.dispute is None,
        dispute=DisputeOut.of(view.dispute) if view.dispute else None,
        chat=OrderChatOut.of(await chat.order_chat_summary(user_id, order_id), user_id),
    )


@router.get("/online")
@inject
async def get_online(
    user: ExecutorUser, cabinet: FromDishka[ExecutorCabinetInteractor]
) -> OnlineOut:
    overview = await cabinet.overview(user.id)
    if overview is None:
        raise HTTPException(404, "Not found")
    return OnlineOut(online=overview.profile.is_online)


@router.put("/online")
@inject
async def set_online(
    body: OnlineIn,
    user: ExecutorUser,
    cabinet: FromDishka[ExecutorCabinetInteractor],
    effects: FromDishka[Effects],
) -> OnlineOut:
    changed = await cabinet.set_online(user.id, body.online)
    if changed is None:
        raise HTTPException(404, "Not found")
    if changed and body.online:
        await effects.executor_online(user.id)
    elif changed:
        await effects.executor_offline(user.id)
    return OnlineOut(online=body.online)


@router.get("/queue")
@inject
async def queue(
    user: ExecutorUser, dispatcher: FromDishka[DispatchInteractor]
) -> list[ExecutorOrderBrief]:
    """Only what he may take now: no permission means an empty list."""
    return [
        ExecutorOrderBrief(**card_brief(card, OrderStatus.in_queue, user.language))
        for card in await dispatcher.queue_for(user.id)
    ]


@router.post("/orders/{order_id}/take")
@inject
async def take(
    order_id: int,
    user: ExecutorUser,
    dispatcher: FromDishka[DispatchInteractor],
    work: FromDishka[FulfillmentWorkInteractor],
    chat: FromDishka[ConversationInteractor],
    effects: FromDishka[Effects],
) -> ExecutorOrderOut:
    if not await dispatcher.take(user.id, order_id):  # gone, taken, not permitted, at the limit
        raise HTTPException(409, "Order is not available")
    await effects.order_taken(order_id, user.id)
    return await _order(order_id, user.id, user.language, work, chat)


@router.get("/orders")
@inject
async def my_orders(
    user: ExecutorUser,
    work: FromDishka[FulfillmentWorkInteractor],
    chat: FromDishka[ConversationInteractor],
    attention: FromDishka[AttentionInteractor],
    page: int = Query(0, ge=0),
) -> ExecutorOrderListOut:
    orders, total, page = await work.my_orders(user.id, page)
    unread = await chat.unread_by_order(user.id, orders)
    actions = await attention.executor_actions(orders)
    items = []
    for order in orders:
        variant = order.snapshot.get("variant") or {}
        items.append(
            ExecutorOrderListItem(
                id=order.id,
                status=order.status,
                product=pick_i18n(order.snapshot.get("product"), user.language),
                variant=pick_i18n(variant.get("title"), user.language),
                country=variant.get("country"),
                deadline_at=order.deadline_at,
                unread=unread.get(order.id, 0),
                action=actions.get(order.id),
            )
        )
    return ExecutorOrderListOut(items=items, total=total, page=page, page_size=PAGE_SIZE)


@router.get("/orders/{order_id}")
@inject
async def get_order(
    order_id: int,
    user: ExecutorUser,
    work: FromDishka[FulfillmentWorkInteractor],
    chat: FromDishka[ConversationInteractor],
) -> ExecutorOrderOut:
    return await _order(order_id, user.id, user.language, work, chat)


@router.post("/orders/{order_id}/accept")
@inject
async def accept(
    order_id: int,
    user: ExecutorUser,
    dispatcher: FromDishka[DispatchInteractor],
    work: FromDishka[FulfillmentWorkInteractor],
    chat: FromDishka[ConversationInteractor],
    effects: FromDishka[Effects],
) -> ExecutorOrderOut:
    """Confirm an auto-assigned order; its term starts now. 404: the time ran out and the order
    went back to the queue, or it is not his."""
    try:
        await dispatcher.accept(user.id, order_id)
    except OrderUnavailable:
        raise HTTPException(404, "Not found") from None
    await effects.order_accepted(order_id)
    return await _order(order_id, user.id, user.language, work, chat)


@router.post("/orders/{order_id}/refuse")
@inject
async def refuse(
    order_id: int,
    user: ExecutorUser,
    dispatcher: FromDishka[DispatchInteractor],
    effects: FromDishka[Effects],
) -> dict[str, bool]:
    try:
        result = await dispatcher.refuse(user.id, order_id)
    except OrderUnavailable:
        raise HTTPException(404, "Not found") from None
    await effects.order_refused(result)
    return {"ok": True}


@router.post("/orders/{order_id}/result")
@inject
async def submit_result(
    order_id: int,
    body: ResultIn,
    user: ExecutorUser,
    work: FromDishka[FulfillmentWorkInteractor],
    chat: FromDishka[ConversationInteractor],
    effects: FromDishka[Effects],
) -> ExecutorOrderOut:
    """Text fields only: a file field of the result form cannot be filled from the Mini App."""
    order = await work.submit(user.id, order_id, body.fields)  # OrderUnavailable -> 404
    await effects.result_submitted(order)
    return await _order(order_id, user.id, user.language, work, chat)


@router.post("/orders/{order_id}/dispute")
@inject
async def open_dispute(
    order_id: int,
    body: DisputeIn,
    user: ExecutorUser,
    work: FromDishka[FulfillmentWorkInteractor],
    chat: FromDishka[ConversationInteractor],
    disputes: FromDishka[DisputeInteractor],
    effects: FromDishka[Effects],
) -> ExecutorOrderOut:
    """Call support. Conflict `dispute_open` (409); not his order, or one not in work: 404."""
    news = await disputes.open(user.id, order_id, body.reason)
    await effects.dispute_opened(news)
    return await _order(order_id, user.id, user.language, work, chat)


@router.post("/orders/{order_id}/extension")
@inject
async def request_extension(
    order_id: int,
    body: ExtensionRequestIn,
    user: ExecutorUser,
    work: FromDishka[FulfillmentWorkInteractor],
    chat: FromDishka[ConversationInteractor],
    extension: FromDishka[ExtensionInteractor],
    effects: FromDishka[Effects],
) -> ExecutorOrderOut:
    """Conflict `extension_pending` / `extension_limit` (409); a passed deadline is a 400."""
    ask = await extension.request(user.id, order_id, body.minutes)
    await effects.extension_asked(ask)
    return await _order(order_id, user.id, user.language, work, chat)


@router.post("/orders/{order_id}/cancel-request")
@inject
async def answer_cancel(
    order_id: int,
    body: CancelAnswerIn,
    user: ExecutorUser,
    work: FromDishka[FulfillmentWorkInteractor],
    chat: FromDishka[ConversationInteractor],
    cancel_requests: FromDishka[CancelRequestInteractor],
    effects: FromDishka[Effects],
) -> ExecutorOrderOut:
    """The buyer's request to cancel: agree or keep working. Conflict `cancel_stale` (409): the
    request is gone, nothing changed; not his order: 404."""
    try:
        answer = await cancel_requests.answer(user.id, order_id, body.request_id, body.agree)
    except OrderUnavailable:
        raise HTTPException(404, "Not found") from None
    await effects.cancel_answered(answer)
    return await _order(order_id, user.id, user.language, work, chat)


@router.get("/stats")
@inject
async def stats(user: ExecutorUser, interactor: FromDishka[ExecutorStats]) -> StatsOut:
    return StatsOut(**vars(await interactor.stats(user.id)))


async def _wallet(user_id: int, wallet: ExecutorWalletInteractor) -> WalletDetailOut:
    try:
        summary = await wallet.summary(user_id)
    except ExecutorNotFound:
        raise HTTPException(404, "Not found") from None
    return WalletDetailOut(
        hold=usd(summary.hold),
        available=usd(summary.available),
        wallet=summary.wallet,
        minimum=usd(summary.minimum),
        entries=[LedgerEntryOut.of(e) for e in summary.entries],
    )


@router.get("/balance")
@inject
async def balance(
    user: ExecutorUser, wallet: FromDishka[ExecutorWalletInteractor]
) -> WalletDetailOut:
    return await _wallet(user.id, wallet)


@router.put("/wallet")
@inject
async def set_wallet(
    body: WalletIn, user: ExecutorUser, wallet: FromDishka[ExecutorWalletInteractor]
) -> WalletDetailOut:
    await wallet.set_wallet(user.id, body.address)  # InvalidInput -> 422
    return await _wallet(user.id, wallet)


@router.post("/withdraw")
@inject
async def withdraw(
    user: ExecutorUser,
    wallet: FromDishka[ExecutorWalletInteractor],
    effects: FromDishka[Effects],
) -> WithdrawalOut:
    withdrawal = await wallet.withdraw(user.id)  # WalletNotSet / BelowMinimum -> 400
    await effects.withdrawal_created(user, withdrawal)
    return WithdrawalOut(
        id=withdrawal.id, amount=usd(withdrawal.amount), address=withdrawal.address
    )
