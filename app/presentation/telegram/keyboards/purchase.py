from decimal import Decimal

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd
from app.application.models.form_schema import FieldType, FormField
from app.presentation.telegram.callbacks.balance import CDBalance
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.callbacks.purchase import CDPurchase
from app.presentation.telegram.keyboards.common import button, markup


def _cancel(i18n: I18nContext) -> list[InlineKeyboardButton]:
    return [button(i18n.buttons.cancel(), CDPurchase(action="cancel"), style="danger")]


def cancel_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup([_cancel(i18n)])


def ask_keyboard(i18n: I18nContext, field: FormField) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if field.type is FieldType.choice:
        rows += [
            [button(option, CDPurchase(action="choice", value=i))]
            for i, option in enumerate(field.options or [])
        ]
    if not field.required:
        rows.append([button(i18n.buttons.skip(), CDPurchase(action="skip"))])
    rows.append(_cancel(i18n))
    return markup(rows)


def confirm_keyboard(i18n: I18nContext, total: Decimal) -> InlineKeyboardMarkup:
    return markup(
        [
            [
                button(
                    i18n.buttons.pay(amount=fmt_usd(total)),
                    CDPurchase(action="pay"),
                    style="success",
                )
            ],
            [button(i18n.buttons.promo(), CDPurchase(action="promo"))],
            _cancel(i18n),
        ]
    )


def insufficient_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup(
        [
            [button(i18n.buttons.topup(), CDBalance(action="topup"), style="primary")],
            [button(i18n.buttons.menu(), CDMenu())],
        ]
    )


def menu_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.menu(), CDMenu())]])
