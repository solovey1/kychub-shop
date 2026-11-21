from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd
from app.presentation.telegram.callbacks.balance import CDBalance
from app.presentation.telegram.callbacks.catalog import CDCategory
from app.presentation.telegram.callbacks.menu import CDLang, CDMenu
from app.presentation.telegram.callbacks.orders import CDOrders
from app.presentation.telegram.keyboards.common import button, markup

LANGUAGES = (("ru", "Русский"), ("en", "English"), ("uk", "Українська"))


def main_menu_keyboard(i18n: I18nContext, balance: Decimal) -> InlineKeyboardMarkup:
    return markup(
        [
            [button(i18n.buttons.catalog(), CDCategory(), style="primary")],
            [
                InlineKeyboardButton(
                    text=i18n.buttons.search(), switch_inline_query_current_chat=""
                )
            ],
            [button(i18n.buttons.orders(), CDOrders())],
            [button(i18n.buttons.balance(amount=fmt_usd(balance)), CDBalance())],
            [button(i18n.buttons.language(), CDLang())],
        ]
    )


def language_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    rows = [[button(title, CDLang(code=code))] for code, title in LANGUAGES]
    rows.append([button(i18n.buttons.back(), CDMenu())])
    return markup(rows)
