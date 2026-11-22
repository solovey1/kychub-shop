from __future__ import annotations

from dataclasses import dataclass

from aiogram import html
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CopyTextButton, InlineKeyboardButton
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd, pick_i18n
from app.application.interactors.catalog import VariantView
from app.application.interactors.purchase import Prepared, Quote
from app.application.models.form_schema import FieldType, FormField, split_files
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.domain.user import User
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.keyboards.catalog import variant_name
from app.presentation.telegram.keyboards.common import button, markup
from app.presentation.telegram.keyboards.purchase import (
    accepted_keyboard,
    ask_keyboard,
    back_keyboard,
    confirm_keyboard,
    fields_keyboard,
    menu_keyboard,
)
from app.presentation.telegram.presenters.base import BasePresenter, Keys
from app.presentation.telegram.view.models import RenderMode, View

COPY_LIMIT = 256
FILE_LIMIT = 3500
SEPARATOR = "──────────"
DONE_EFFECT = "5046509860389126442"  # 🎉

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
    i18n: I18nContext,
    header: str,
    text: str,
    back: CallbackData | None = None,
    extra: list[InlineKeyboardButton] | None = None,
) -> tuple[View, bytes | None]:
    """Delivery of a finished order: quoted text + copy button, or a .txt file when it is long."""
    back_row = [
        button(i18n.buttons.menu() if back is None else i18n.buttons.back(), back or CDMenu())
    ]
    extra_rows = [extra] if extra else []
    if len(text) > FILE_LIMIT:
        view = View(
            text=f"{header}\n\n{i18n.messages.purchase.done_file()}",
            reply_markup=markup([*extra_rows, back_row]),
        )
        return view, text.encode("utf-8")
    rows: list[list[InlineKeyboardButton]] = []
    if len(text) <= COPY_LIMIT:
        rows.append(
            [
                InlineKeyboardButton(
                    text=i18n.buttons.copy(), copy_text=CopyTextButton(text=text), style="success"
                )
            ]
        )
    rows.extend([*extra_rows, back_row])
    body = f"{header}\n\n<blockquote>{html.quote(text)}</blockquote>"
    return View(text=body, reply_markup=markup(rows)), None


@dataclass(frozen=True)
class PurchasePresenter(BasePresenter):
    i18n: I18nContext

    def _variant(self, prep: Prepared) -> str:
        view = VariantView(prep.variant, True, prep.country)
        return html.quote(variant_name(view, self.i18n.locale))

    def _product(self, prep: Prepared) -> str:
        return html.quote(pick_i18n(prep.product.title_i18n, self.i18n.locale))

    def _label(self, field: FormField) -> str:
        return html.quote(pick_i18n(field.label, self.i18n.locale))

    def _value(self, field: FormField, value: str) -> str:
        if field.type is FieldType.file:
            return self.i18n.messages.purchase.files_value(n=len(split_files(value)))
        return html.quote(value) if value else "—"

    def reason(self, error: str) -> str:
        return self.i18n.get(f"messages-purchase-reason_{reason_code(error)}")

    def prev_value(self, field: FormField, prev: dict[str, str]) -> str | None:
        """The answer given last time, if it is still good for this field (files are not)."""
        value = prev.get(field.key)
        if not value:
            return None
        try:
            return field.validate_value(value)
        except ValueError:
            return None

    def _ask_lines(self, field: FormField, files: int) -> list[str]:
        messages = Keys(self.i18n, "messages-purchase")
        if hint := pick_i18n(field.hint, self.i18n.locale):
            lines = [html.quote(hint)]
        elif field.type is FieldType.file:
            lines = [
                messages.hint_files(max=field.max_files)
                if field.max_files > 1
                else messages.hint_file()
            ]
        elif field.type is FieldType.choice:
            lines = [messages.choose(label=self._label(field))]
        else:
            lines = [messages.ask(label=self._label(field))]
        if field.type is FieldType.file and field.max_files > 1:
            lines.append(messages.files_progress(n=files, max=field.max_files))
        return lines

    def card(
        self,
        prep: Prepared,
        answers: dict[str, str],
        idx: int,
        prev: dict[str, str],
        *,
        current: bool,
        reason: str | None = None,
        files: int = 0,
    ) -> View:
        """The live questionnaire: every question with its state, then the current prompt."""
        messages = Keys(self.i18n, "messages-purchase")
        details = ", ".join(x for x in (self._variant(prep), fmt_usd(prep.variant.price)) if x)
        lines = [messages.head(product=self._product(prep), details=details), ""]
        for i, f in enumerate(prep.form.fields):
            label = self._label(f)
            if i == idx:
                lines.append(messages.line_now(label=label))
            elif f.key in answers:
                lines.append(messages.line_done(label=label, value=self._value(f, answers[f.key])))
            elif f.required:
                lines.append(messages.line_next(label=label))
            else:
                lines.append(messages.line_next_optional(label=label))
        field = prep.form.fields[idx]
        lines.append(SEPARATOR)
        lines += self._ask_lines(field, files)
        if reason is not None:
            lines.append(messages.invalid(reason=reason))
        prev_value = self.prev_value(field, prev)
        if prev_value and field.type is FieldType.file:  # the button shows a count, not ids
            prev_value = self._value(field, prev_value)
        return View(
            text="\n".join(lines),
            reply_markup=ask_keyboard(self.i18n, field, prev_value, files),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )

    def prompt(self, field: FormField) -> tuple[str, str]:
        """The short message under the card and the placeholder of the input field."""
        label = pick_i18n(field.label, self.i18n.locale)
        placeholder = pick_i18n(field.placeholder, self.i18n.locale) or label
        return self.i18n.messages.purchase.prompt(label=html.quote(label)), placeholder[:64]

    def confirm(
        self,
        prep: Prepared,
        answers: dict[str, str],
        quote: Quote,
        promo_code: str | None,
        *,
        current: bool,
        promo_error: str | None = None,
        pick: bool = False,
        online: int | None = None,
        first: bool = False,
    ) -> View:
        """The checkout. `pick`: the same text, with the questions as buttons to change one."""
        messages = Keys(self.i18n, "messages-purchase")
        what = ", ".join(x for x in (self._product(prep), self._variant(prep)) if x)
        lines = [messages.confirm_title(), "", what]
        answered = [
            f"{self._label(f)}: {self._value(f, answers[f.key])}"
            for f in prep.form.fields
            if answers.get(f.key)
        ]
        if answered:
            lines.append("<blockquote>" + "\n".join(answered) + "</blockquote>")
        lines.append(messages.line_price(amount=fmt_usd(quote.price)))
        if quote.discount and promo_code:
            code = html.quote(promo_code.upper())
            lines.append(messages.line_discount(code=code, amount=fmt_usd(quote.discount)))
        lines += [
            SEPARATOR,
            messages.line_total(total=fmt_usd(quote.total), balance=fmt_usd(quote.balance)),
        ]
        if quote.total > quote.balance:
            lines.append(messages.line_missing(amount=fmt_usd(quote.total - quote.balance)))
        if online is not None:
            lines.append(messages.line_online(count=online) if online else messages.line_offline())
        if first:
            lines += ["", messages.how_it_works()]
        if promo_error:
            reason = self.i18n.get(f"messages-promo-reason_{promo_error}")
            lines.append(messages.promo_error(reason=reason))
        if pick:
            lines += ["", messages.edit_pick()]
            keyboard = fields_keyboard(self.i18n, prep.form.fields)
        else:
            keyboard = confirm_keyboard(
                self.i18n, quote.total, quote.balance, bool(prep.form.fields)
            )
        return View(
            text="\n".join(lines),
            reply_markup=keyboard,
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )

    def ask_promo(self) -> View:
        return View(
            text=self.i18n.messages.purchase.promo_ask(),
            reply_markup=back_keyboard(self.i18n),
        )

    def simple(self, key: str) -> View:
        return View(
            text=self.i18n.get(f"messages-purchase-{key}"), reply_markup=menu_keyboard(self.i18n)
        )

    def delivered(self, order: Order) -> tuple[View, View | None, bytes | None]:
        """The card turned into a receipt, and the result as a new message when it is ready."""
        messages = Keys(self.i18n, "messages-purchase")
        done = order.status is OrderStatus.completed and bool(order.result)
        if done:
            next_ = messages.next_done()
        elif order.status is OrderStatus.assigned:
            next_ = messages.next_work()
        else:
            next_ = messages.next_queue()
        receipt = View(
            text=messages.accepted(id=order.code, next=next_),
            reply_markup=accepted_keyboard(self.i18n, order.id),
        )
        if not done or not order.result:
            return receipt, None, None
        result, file = result_view(
            self.i18n, messages.done(id=order.code), str(order.result.get("text", ""))
        )
        result.mode = RenderMode.NEW
        result.kwargs = {"message_effect_id": DONE_EFFECT}
        return receipt, result, file

    def admin_manual(self, order: Order, user: User, product_title: str) -> str:
        answers = "\n".join(
            f"{html.quote(k)}: {html.quote(v)}" for k, v in (order.input_data or {}).items()
        )
        return self.i18n.get(
            "messages-purchase-admin_manual",
            "ru",
            id=order.code,
            user=user.mention,
            product=html.quote(product_title),
            answers=answers or "-",
        )
