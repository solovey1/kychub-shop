from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd, pick_i18n
from app.application.interactors.catalog import PAGE_SIZE
from app.application.interactors.conversations import CHAT_STATUSES
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.presentation.telegram.callbacks.catalog import CDVariant
from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.callbacks.orders import CDCancel, CDOrder, CDOrders
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


def order_keyboard(
    i18n: I18nContext, order: Order, page: int, reorder: bool = False
) -> InlineKeyboardMarkup:
    rows = []
    if order.status in CHAT_STATUSES:
        rows.append([button(i18n.buttons.chat_executor(), CDChat(action="order", id=order.id))])
    rows.append([button(i18n.buttons.chat_support(), CDChat(action="support", id=order.id))])
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
