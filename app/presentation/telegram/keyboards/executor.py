from aiogram.types import InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.presentation.telegram.callbacks.executor import CDOrderAct
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.keyboards.common import button, markup


def cabinet_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.back(), CDMenu())]])


def refuse_keyboard(i18n: I18nContext, order_id: int) -> InlineKeyboardMarkup:
    return markup(
        [[button(i18n.buttons.refuse(), CDOrderAct(action="refuse", id=order_id), style="danger")]]
    )
