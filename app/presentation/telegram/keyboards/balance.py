from decimal import Decimal

from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd
from app.presentation.telegram.callbacks.balance import CDBalance, CDCheck, CDPay, CDTopup
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.callbacks.purchase import CDPurchase
from app.presentation.telegram.keyboards.common import button, markup

TOPUP_AMOUNTS = (5, 10, 25, 50)


def balance_keyboard(i18n: I18nContext, resume: bool = False) -> InlineKeyboardMarkup:
    return markup(
        [
            [button(i18n.buttons.resume_checkout(), CDPurchase(action="back"), style="success")]
            if resume
            else [],
            [button(i18n.buttons.topup(), CDBalance(action="topup"), style="primary")],
            [button(i18n.buttons.redeem(), CDBalance(action="promo"))],
            [button(i18n.buttons.back(), CDMenu())],
        ]
    )


def topup_keyboard(i18n: I18nContext, enabled: bool, amounts: list[int]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    if enabled:
        buttons = [button(fmt_usd(Decimal(a)), CDTopup(amount=a)) for a in amounts]
        rows += [buttons[:2], buttons[2:]]
        rows.append([button(i18n.buttons.topup_custom(), CDBalance(action="custom"))])
    rows.append([button(i18n.buttons.back(), CDBalance())])
    return markup(rows)


def methods_keyboard(i18n: I18nContext, providers: list[str], cents: int) -> InlineKeyboardMarkup:
    rows = [
        [button(i18n.get(f"buttons-provider_{code}"), CDPay(provider=code, cents=cents))]
        for code in providers
    ]
    rows.append([button(i18n.buttons.back(), CDBalance(action="topup"))])
    return markup(rows)


def invoice_keyboard(
    i18n: I18nContext, payment_id: int, url: str | None, copy: list[tuple[str, str]]
) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text=i18n.buttons.pay_invoice(), url=url)]] if url else []
    rows += [[InlineKeyboardButton(text=t, copy_text=CopyTextButton(text=v))] for t, v in copy]
    rows.append([button(i18n.buttons.check_payment(), CDCheck(id=payment_id), style="primary")])
    rows.append([button(i18n.buttons.back(), CDBalance())])
    return markup(rows)


def back_to_balance(i18n: I18nContext) -> InlineKeyboardMarkup:
    return markup([[button(i18n.buttons.back(), CDBalance())]])
