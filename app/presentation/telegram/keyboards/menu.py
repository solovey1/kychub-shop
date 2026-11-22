from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.presentation.telegram.callbacks.balance import CDBalance
from app.presentation.telegram.callbacks.catalog import CDCategory
from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.callbacks.executor import CDCabinet
from app.presentation.telegram.callbacks.menu import CDLang, CDMenu
from app.presentation.telegram.callbacks.orders import CDOrders
from app.presentation.telegram.keyboards.common import app_button, button, markup

LANGUAGES = (("ru", "Русский"), ("en", "English"), ("uk", "Українська"))


def main_menu_keyboard(
    i18n: I18nContext, active_orders: int, is_executor: bool, server_url: str
) -> InlineKeyboardMarkup:
    orders = i18n.buttons.orders_n(count=active_orders) if active_orders else i18n.buttons.orders()
    opener = app_button(i18n.buttons.app(), server_url, "/")
    return markup(
        [
            [
                button(i18n.buttons.catalog(), CDCategory(), style="success"),
                InlineKeyboardButton(
                    text=i18n.buttons.search(), switch_inline_query_current_chat=""
                ),
            ],
            [
                button(orders, CDOrders()),
                button(i18n.buttons.topup(), CDBalance()),
            ],
            [
                button(i18n.buttons.support(), CDChat(action="support")),
                button(i18n.buttons.language(), CDLang()),
            ],
            [opener] if opener else [],
            [button(i18n.buttons.cabinet(), CDCabinet())] if is_executor else [],
        ]
    )


def language_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    rows = [[button(title, CDLang(code=code))] for code, title in LANGUAGES]
    rows.append([button(i18n.buttons.back(), CDMenu())])
    return markup(rows)
