from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import pick_i18n
from app.application.interactors.catalog import PAGE_SIZE
from app.application.interactors.conversations import CHAT_STATUSES
from app.application.models.form_schema import FieldType, FormField
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.callbacks.executor import (
    CDCabinet,
    CDOrderAct,
    CDReview,
    CDXOrder,
    CDXOrders,
    CDXResult,
)
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.keyboards.common import button, markup, pager


def cabinet_keyboard(i18n: I18nContext, online: bool) -> InlineKeyboardMarkup:
    toggle = (
        button(i18n.buttons.go_offline(), CDCabinet(section="offline"))
        if online
        else button(i18n.buttons.go_online(), CDCabinet(section="online"), style="success")
    )
    return markup(
        [
            [toggle],
            [button(i18n.buttons.my_orders(), CDXOrders())],
            [
                button(i18n.buttons.balance_short(), CDCabinet(section="balance")),
                button(i18n.buttons.rating(), CDCabinet(section="rating")),
            ],
            [button(i18n.buttons.payout_wallet(), CDCabinet(section="wallet"))],
            [button(i18n.buttons.back(), CDMenu())],
        ]
    )


def refuse_keyboard(i18n: I18nContext, order_id: int) -> InlineKeyboardMarkup:
    return markup(
        [[button(i18n.buttons.refuse(), CDOrderAct(action="refuse", id=order_id), style="danger")]]
    )


def orders_keyboard(
    i18n: I18nContext, orders: list[Order], total: int, page: int
) -> InlineKeyboardMarkup:
    rows = [
        [
            button(
                i18n.buttons.order_item(
                    id=order.id,
                    title=pick_i18n(order.snapshot.get("product"), i18n.locale),
                    status=i18n.get(f"order-status-{order.status}"),
                ),
                CDXOrder(id=order.id, page=page),
            )
        ]
        for order in orders
    ]
    rows.append(pager(page, max(1, -(-total // PAGE_SIZE)), lambda n: CDXOrders(page=n)))
    rows.append([button(i18n.buttons.back(), CDCabinet())])
    return markup(rows)


def order_keyboard(i18n: I18nContext, order: Order, page: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if order.status is OrderStatus.assigned:
        rows.append(
            [
                button(
                    i18n.buttons.submit_result(),
                    CDXResult(action="start", id=order.id),
                    style="success",
                )
            ]
        )
        rows.append(
            [
                button(
                    i18n.buttons.refuse(), CDOrderAct(action="refuse", id=order.id), style="danger"
                )
            ]
        )
    if order.status in CHAT_STATUSES:
        rows.append([button(i18n.buttons.chat_buyer(), CDChat(action="order", id=order.id))])
    rows.append([button(i18n.buttons.back(), CDXOrders(page=page))])
    return markup(rows)


def result_ask_keyboard(
    i18n: I18nContext, order_id: int, field: FormField
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if field.type is FieldType.choice:
        rows += [
            [button(option, CDXResult(action="choice", id=order_id, value=i))]
            for i, option in enumerate(field.options or [])
        ]
    if not field.required:
        rows.append([button(i18n.buttons.skip(), CDXResult(action="skip", id=order_id))])
    rows.append(
        [button(i18n.buttons.cancel(), CDXResult(action="cancel", id=order_id), style="danger")]
    )
    return markup(rows)


def order_back_keyboard(i18n: I18nContext, order_id: int) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.back(), CDXOrder(id=order_id))]])


def review_keyboard(i18n: I18nContext, order: Order) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if order.status is OrderStatus.ready:
        rows.append(
            [button(i18n.buttons.confirm(), CDReview(action="ok", id=order.id), style="success")]
        )
        rows.append([button(i18n.buttons.send_back(), CDReview(action="back", id=order.id))])
    if order.status in (OrderStatus.ready, OrderStatus.completed):
        rows.append(
            [button(i18n.buttons.fail(), CDReview(action="fail", id=order.id), style="danger")]
        )
    return markup(rows)


def fail_confirm_keyboard(i18n: I18nContext, order_id: int) -> InlineKeyboardMarkup:
    return markup(
        [
            [
                button(
                    i18n.buttons.fail_confirm(),
                    CDReview(action="failok", id=order_id),
                    style="danger",
                )
            ],
            [button(i18n.buttons.back(), CDReview(action="open", id=order_id))],
        ]
    )


def review_cancel_keyboard(i18n: I18nContext, order_id: int) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.cancel(), CDReview(action="open", id=order_id))]])


def back_to_cabinet(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.back(), CDCabinet())]])


def balance_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup(
        [
            [button(i18n.buttons.withdraw(), CDCabinet(section="withdraw"), style="primary")],
            [button(i18n.buttons.back(), CDCabinet())],
        ]
    )


def wallet_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup(
        [
            [button(i18n.buttons.wallet_set(), CDCabinet(section="wallet_set"))],
            [button(i18n.buttons.back(), CDCabinet())],
        ]
    )
