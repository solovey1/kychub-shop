from typing import Callable

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd, pick_i18n
from app.application.interactors.catalog import PAGE_SIZE
from app.application.interactors.conversations import CHAT_STATUSES
from app.application.interactors.deadlines import Pending
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.presentation.telegram.callbacks.catalog import CDVariant
from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.callbacks.orders import (
    CDCancel,
    CDCancelAsk,
    CDDeal,
    CDExtAnswer,
    CDOrder,
    CDOrders,
)
from app.presentation.telegram.keyboards.common import button, markup, pager


def orders_keyboard(
    i18n: I18nContext, orders: list[Order], total: int, page: int
) -> InlineKeyboardMarkup:
    rows = []
    for order in orders:
        label = i18n.buttons.order_item(
            icon=i18n.get(f"order-icon-{order.status}"),
            id=order.id,
            title=pick_i18n(order.snapshot.get("product"), i18n.locale),
            total=fmt_usd(order.price - order.discount),
        )
        rows.append([button(label, CDOrder(id=order.id, page=page))])
    pages = max(1, -(-total // PAGE_SIZE))
    rows.append(pager(page, pages, lambda n: CDOrders(page=n)))
    rows.append([button(i18n.buttons.back(), CDMenu())])
    return markup(rows)


def order_back_keyboard(i18n: I18nContext, page: int) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.back(), CDOrders(page=page))]])


def reorder_row(i18n: I18nContext, order: Order) -> list[InlineKeyboardButton]:
    return [button(i18n.buttons.reorder_again(), CDVariant(id=order.variant_id))]


def extension_keyboard(tr: Callable[..., str], order_id: int, rid: int) -> InlineKeyboardMarkup:
    return markup(
        [
            [
                button(
                    tr("buttons-ext_yes"),
                    CDExtAnswer(id=order_id, rid=rid, ok=1),
                    style="success",
                ),
                button(tr("buttons-ext_no"), CDExtAnswer(id=order_id, rid=rid, ok=0)),
            ]
        ]
    )


def deal_rows(
    tr: Callable[..., str], order_id: int, page: int = 0, *, ok: bool = True, ask: bool = True
) -> list[list[InlineKeyboardButton]]:
    """What a side of an order in work may do: «all good» (a submitted order, the buyer) and
    «call support»."""
    rows = []
    if ok:
        ok_data = CDDeal(action="ok", id=order_id, page=page)
        rows.append([button(tr("buttons-deal_ok"), ok_data, style="success")])
    if ask:
        rows.append([button(tr("buttons-deal_ask"), CDDeal(action="ask", id=order_id, page=page))])
    return rows


def dispute_ask_keyboard(tr: Callable[..., str], order_id: int, page: int) -> InlineKeyboardMarkup:
    return markup(
        [
            [button(tr("buttons-deal_skip"), CDDeal(action="skip", id=order_id, page=page))],
            [button(tr("buttons-cancel"), CDDeal(action="cancel", id=order_id, page=page))],
        ]
    )


def order_keyboard(
    i18n: I18nContext,
    order: Order,
    page: int,
    reorder: bool = False,
    pending: Pending | None = None,
    dispute: bool = False,
    can_ask_cancel: bool = False,
    info: bool = False,
) -> InlineKeyboardMarkup:
    rows = []
    if order.status is OrderStatus.ready or (order.status in CHAT_STATUSES and not dispute):
        rows += deal_rows(
            i18n.get, order.id, page, ok=order.status is OrderStatus.ready, ask=not dispute
        )
    if pending is not None:
        rows += extension_keyboard(i18n.get, order.id, pending.request_id).inline_keyboard
    if order.status in CHAT_STATUSES:
        chat = i18n.buttons.info_reply() if info else i18n.buttons.chat_executor()
        rows.append(
            [button(chat, CDChat(action="order", id=order.id), style="primary" if info else None)]
        )
    else:  # in work, support comes through the dispute (or is already in it)
        rows.append([button(i18n.buttons.chat_support(), CDChat(action="support", id=order.id))])
    if can_ask_cancel:
        rows.append([button(i18n.buttons.cancel_ask(), CDCancelAsk(id=order.id, page=page))])
    if reorder:
        rows.append(reorder_row(i18n, order))
    if order.status is OrderStatus.in_queue:  # nobody has taken it yet
        rows.append(
            [button(i18n.buttons.cancel_order(), CDCancel(id=order.id, page=page), style="danger")]
        )
    rows.append([button(i18n.buttons.back(), CDOrders(page=page))])
    return markup(rows)


def cancel_confirm_keyboard(i18n: I18nContext, order_id: int, page: int) -> InlineKeyboardMarkup:
    return markup(
        [
            [
                button(
                    i18n.buttons.cancel_confirm(),
                    CDCancel(id=order_id, page=page, ok=1),
                    style="danger",
                )
            ],
            [button(i18n.buttons.back(), CDOrder(id=order_id, page=page))],
        ]
    )
