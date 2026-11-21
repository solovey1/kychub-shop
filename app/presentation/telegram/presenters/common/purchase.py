from __future__ import annotations

from dataclasses import dataclass

from aiogram import html
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CopyTextButton, InlineKeyboardButton
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd, pick_i18n
from app.application.interactors.catalog import VariantView
from app.application.interactors.purchase import Prepared, Quote
from app.application.models.form_schema import FieldType, FormField
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.domain.user import User
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.keyboards.catalog import variant_label
from app.presentation.telegram.keyboards.common import button, markup
from app.presentation.telegram.keyboards.purchase import (
    ask_keyboard,
    cancel_keyboard,
    confirm_keyboard,
    insufficient_keyboard,
    menu_keyboard,
)
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import RenderMode, View

COPY_LIMIT = 256
FILE_LIMIT = 3500

_REASONS = {
    "value is required": "required",
    "value is too long": "too_long",
    "invalid email": "email",
    "invalid number": "number",
    "value is not among options": "choice",
    "value does not match the required format": "format",
    "control characters are not allowed": "control",
    "not_file": "not_file",
    "not_text": "not_text",
}


def reason_code(error: str) -> str:
    return _REASONS.get(error, "format")


def result_view(
    i18n: I18nContext, header: str, text: str, back: CallbackData | None = None
) -> tuple[View, bytes | None]:
    """Delivery of a finished order: <code> text + copy button, or a .txt file when it is long."""
    back_row = [
        button(i18n.buttons.menu() if back is None else i18n.buttons.back(), back or CDMenu())
    ]
    if len(text) > FILE_LIMIT:
        view = View(
            text=f"{header}\n\n{i18n.messages.purchase.done_file()}",
            reply_markup=markup([back_row]),
        )
        return view, text.encode("utf-8")
    rows: list[list[InlineKeyboardButton]] = []
    if len(text) <= COPY_LIMIT:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.buttons.copy(), copy_text=CopyTextButton(text=text), style="primary"
                )
            ]
        )
    rows.append(back_row)
    view = View(text=f"{header}\n\n<code>{html.quote(text)}</code>", reply_markup=markup(rows))
    return view, None


@dataclass(frozen=True)
class PurchasePresenter(BasePresenter):
    i18n: I18nContext

    def _head(self, prep: Prepared) -> tuple[str, str]:
        locale = self.i18n.locale
        product = html.quote(pick_i18n(prep.product.title_i18n, locale))
        variant = html.quote(variant_label(VariantView(prep.variant, True, prep.country), locale))
        return product, variant

    def reason(self, error: str) -> str:
        return self.i18n.get(f"messages-purchase-reason_{reason_code(error)}")

    def ask(
        self,
        prep: Prepared,
        idx: int,
        *,
        current: bool,
        reason: str | None = None,
    ) -> View:
        field: FormField = prep.form.fields[idx]
        product, variant = self._head(prep)
        text = self.i18n.messages.purchase.ask(
            product=product,
            variant=variant,
            step=idx + 1,
            total=len(prep.form.fields),
            label=html.quote(pick_i18n(field.label, self.i18n.locale)),
        )
        if field.type is FieldType.file:
            text += "\n" + self.i18n.messages.purchase.hint_file()
        if reason is not None:
            text = self.i18n.messages.purchase.invalid(reason=reason) + "\n\n" + text
        return View(
            text=text,
            reply_markup=ask_keyboard(self.i18n, field),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )

    def confirm(
        self,
        prep: Prepared,
        answers: dict[str, str],
        quote: Quote,
        promo_code: str | None,
        *,
        current: bool,
        promo_error: str | None = None,
    ) -> View:
        i18n = self.i18n
        product, variant = self._head(prep)
        lines = [i18n.messages.purchase.confirm_title(), "", product, variant]
        for field in prep.form.fields:
            if field.type is FieldType.file or field.key not in answers:
                continue
            label = html.quote(pick_i18n(field.label, i18n.locale))
            lines.append(f"{label}: {html.quote(answers[field.key])}")
        lines.append("")
        if promo_code and quote.promo_code_id is not None:
            lines.append(i18n.messages.purchase.line_promo(code=html.quote(promo_code.upper())))
        lines.append(i18n.messages.purchase.line_price(amount=fmt_usd(quote.price)))
        if quote.discount:
            lines.append(i18n.messages.purchase.line_discount(amount=fmt_usd(quote.discount)))
        lines.append(i18n.messages.purchase.line_total(amount=fmt_usd(quote.total)))
        lines.append(i18n.messages.purchase.line_balance(amount=fmt_usd(quote.balance)))
        if promo_error:
            reason = i18n.get(f"messages-promo-reason_{promo_error}")
            lines += ["", i18n.messages.purchase.promo_error(reason=reason)]
        return View(
            text="\n".join(lines),
            reply_markup=confirm_keyboard(i18n, quote.total),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )

    def ask_promo(self) -> View:
        return View(
            text=self.i18n.messages.purchase.promo_ask(),
            reply_markup=cancel_keyboard(self.i18n),
        )

    def insufficient(self, quote: Quote) -> View:
        missing = quote.total - quote.balance
        return View(
            text=self.i18n.messages.purchase.insufficient(
                total=fmt_usd(quote.total),
                balance=fmt_usd(quote.balance),
                missing=fmt_usd(missing),
            ),
            reply_markup=insufficient_keyboard(self.i18n),
        )

    def simple(self, key: str) -> View:
        return View(
            text=self.i18n.get(f"messages-purchase-{key}"), reply_markup=menu_keyboard(self.i18n)
        )

    def delivered(self, order: Order) -> tuple[View, bytes | None]:
        if order.status is OrderStatus.completed and order.result:
            header = self.i18n.messages.purchase.done(id=order.id)
            return result_view(self.i18n, header, str(order.result.get("text", "")))
        view = View(
            text=self.i18n.messages.purchase.accepted(id=order.id),
            reply_markup=menu_keyboard(self.i18n),
        )
        return view, None

    def admin_manual(self, order: Order, user: User, product_title: str) -> str:
        answers = "\n".join(
            f"{html.quote(k)}: {html.quote(v)}" for k, v in (order.input_data or {}).items()
        )
        return self.i18n.get(
            "messages-purchase-admin_manual",
            "ru",
            id=order.id,
            user=user.mention,
            product=html.quote(product_title),
            answers=answers or "-",
        )
