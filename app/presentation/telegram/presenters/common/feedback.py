from dataclasses import dataclass
from decimal import Decimal

from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd
from app.presentation.telegram.keyboards.feedback import (
    done_keyboard,
    rate_keyboard,
    tip_cancel_keyboard,
    tip_keyboard,
)
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import RenderMode, View


@dataclass(frozen=True)
class FeedbackPresenter(BasePresenter):
    i18n: I18nContext

    def ask(self, order_id: int) -> View:
        return View(
            text=self.i18n.messages.feedback.ask(id=str(order_id)),
            reply_markup=rate_keyboard(self.i18n.get, order_id),
        )

    def rated(self, order_id: int, score: int) -> View:
        return View(
            text=self.i18n.messages.feedback.rated(id=str(order_id), score=str(score)),
            reply_markup=rate_keyboard(self.i18n.get, order_id, rated=True),
        )

    def tip_choose(self, order_id: int, token: str) -> View:
        return View(
            text=self.i18n.messages.feedback.tip_choose(id=str(order_id)),
            reply_markup=tip_keyboard(self.i18n.get, order_id, token),
        )

    def tip_ask(self, order_id: int, *, error: bool = False, current: bool = False) -> View:
        text = self.i18n.messages.feedback.tip_ask()
        if error:
            text = self.i18n.messages.feedback.tip_invalid() + "\n\n" + text
        return View(
            text=text,
            reply_markup=tip_cancel_keyboard(self.i18n.get, order_id),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )

    def tipped(self, amount: Decimal, *, current: bool = False) -> View:
        return View(
            text=self.i18n.messages.feedback.tipped(amount=fmt_usd(amount)),
            reply_markup=done_keyboard(self.i18n.get),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )

    def note(self, key: str, *, current: bool = False) -> View:
        return View(
            text=self.i18n.get(f"messages-feedback-{key}"),
            reply_markup=done_keyboard(self.i18n.get),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )
