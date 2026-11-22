from decimal import Decimal
from math import ceil

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd, pick_i18n
from app.application.models.form_schema import FieldType, FormField
from app.presentation.telegram.callbacks.balance import CDTopup
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.callbacks.orders import CDOrder
from app.presentation.telegram.callbacks.purchase import CDPurchase
from app.presentation.telegram.keyboards.common import button, markup

PREV_LIMIT = 24  # characters of the previous answer on its button


def _cancel(i18n: I18nContext) -> list[InlineKeyboardButton]:
    return [button(i18n.buttons.cancel(), CDPurchase(action="cancel"), style="danger")]


def back_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.back(), CDPurchase(action="back"))]])


def ask_keyboard(
    i18n: I18nContext, field: FormField, prev: str | None = None, files: int = 0
) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if field.type is FieldType.choice:
        rows += [
            [button(option, CDPurchase(action="choice", value=i))]
            for i, option in enumerate(field.options or [])
        ]
    if prev:
        short = prev if len(prev) <= PREV_LIMIT else prev[: PREV_LIMIT - 1] + "…"
        rows.append([button(i18n.buttons.prev(value=short), CDPurchase(action="prev"))])
    if files:  # several files: finished by this button, or on reaching the limit
        rows.append([button(i18n.buttons.done(), CDPurchase(action="done"), style="success")])
    elif not field.required:
        rows.append([button(i18n.buttons.skip(), CDPurchase(action="skip"))])
    rows.append(_cancel(i18n))
    return markup(rows)


def confirm_keyboard(
    i18n: I18nContext, total: Decimal, balance: Decimal, has_fields: bool
) -> InlineKeyboardMarkup:
    if total <= balance:
        main = button(
            i18n.buttons.pay(amount=fmt_usd(total)), CDPurchase(action="pay"), style="success"
        )
    else:
        missing = total - balance
        main = button(
            i18n.buttons.topup_missing(amount=fmt_usd(missing)),
            CDTopup(amount=ceil(missing)),
            style="success",
        )
    return markup(
        [
            [main],
            [button(i18n.buttons.promo(), CDPurchase(action="promo"))],
            [button(i18n.buttons.edit(), CDPurchase(action="edit"))] if has_fields else [],
            _cancel(i18n),
        ]
    )


def fields_keyboard(i18n: I18nContext, fields: list[FormField]) -> InlineKeyboardMarkup:
    rows = [
        [button(pick_i18n(f.label, i18n.locale), CDPurchase(action="field", value=i))]
        for i, f in enumerate(fields)
    ]
    rows.append([button(i18n.buttons.back(), CDPurchase(action="back"))])
    return markup(rows)


def accepted_keyboard(i18n: I18nContext, order_id: int) -> InlineKeyboardMarkup:
    return markup(
        [
            [button(i18n.buttons.open_order(), CDOrder(id=order_id), style="success")],
            [button(i18n.buttons.menu(), CDMenu())],
        ]
    )


def menu_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.menu(), CDMenu())]])
