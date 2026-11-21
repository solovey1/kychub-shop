from aiogram.types import InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import pick_i18n
from app.application.interactors.catalog import PAGE_SIZE
from app.domain.order import Order
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.callbacks.orders import CDOrder, CDOrders
from app.presentation.telegram.keyboards.common import button, markup, pager


def orders_keyboard(
    i18n: I18nContext, orders: list[Order], total: int, page: int
) -> InlineKeyboardMarkup:
    rows = []
    for order in orders:
        label = i18n.buttons.order_item(
            id=order.id,
            title=pick_i18n(order.snapshot.get("product"), i18n.locale),
            status=i18n.get(f"order-status-{order.status}"),
        )
        rows.append([button(label, CDOrder(id=order.id, page=page))])
    pages = max(1, -(-total // PAGE_SIZE))
    rows.append(pager(page, pages, lambda n: CDOrders(page=n)))
    rows.append([button(i18n.buttons.back(), CDMenu())])
    return markup(rows)


def order_back_keyboard(i18n: I18nContext, page: int) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.back(), CDOrders(page=page))]])
