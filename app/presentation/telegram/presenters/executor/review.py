from dataclasses import dataclass
from html import escape

from aiogram_i18n import I18nContext

from app.application.cards import render_card
from app.application.interactors.order_review import ReviewView
from app.presentation.telegram.keyboards.executor import (
    fail_confirm_keyboard,
    review_cancel_keyboard,
    review_keyboard,
)
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import RenderMode, View

RESULT_SHOWN = 2500


@dataclass(frozen=True)
class ReviewPresenter(BasePresenter):
    i18n: I18nContext

    def card(self, view: ReviewView, notice_key: str | None = None) -> View:
        i18n = self.i18n
        order = view.order
        text = render_card(i18n.get, i18n.locale, view.card)
        text += "\n\n" + i18n.messages.review.status(
            status=i18n.get(f"order-status-{order.status}")
        )
        if view.text:
            shown = escape(view.text[:RESULT_SHOWN])
            text += "\n\n" + i18n.messages.review.result(result=shown)
        if view.files:
            text += "\n" + i18n.messages.review.files(count=str(len(view.files)))
        if notice_key:
            text = f"{i18n.get(notice_key)}\n\n{text}"
        return View(text=text, reply_markup=review_keyboard(i18n, order))

    def ask_comment(self, order_id: int, code: str) -> View:
        return View(
            text=self.i18n.messages.review.ask_comment(id=code),
            reply_markup=review_cancel_keyboard(self.i18n, order_id),
        )

    def fail_confirm(self, order_id: int, code: str) -> View:
        return View(
            text=self.i18n.messages.review.fail_confirm(id=code),
            reply_markup=fail_confirm_keyboard(self.i18n, order_id),
        )

    def text(self, key: str, code: str, *, current: bool = False) -> View:
        return View(
            text=self.i18n.get(key, id=code),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )
