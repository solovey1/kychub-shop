from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd
from app.presentation.telegram.callbacks.balance import CDBalance, CDTopup
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.keyboards.common import button, markup

TOPUP_AMOUNTS = (5, 10, 25, 50)


def balance_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup(
        [
            [button(i18n.buttons.topup(), CDBalance(action="topup"), style="primary")],
            [button(i18n.buttons.redeem(), CDBalance(action="promo"))],
            [button(i18n.buttons.back(), CDMenu())],
        ]
    )


def topup_keyboard(i18n: I18nContext, enabled: bool) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if enabled:
        amounts = [button(fmt_usd(Decimal(a)), CDTopup(amount=a)) for a in TOPUP_AMOUNTS]
        rows += [amounts[:2], amounts[2:]]
        rows.append([button(i18n.buttons.topup_custom(), CDBalance(action="custom"))])
    rows.append([button(i18n.buttons.back(), CDBalance())])
    return markup(rows)


def back_to_balance(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.back(), CDBalance())]])
