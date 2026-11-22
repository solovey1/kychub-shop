from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from aiogram import html
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd
from app.domain.enums.roles import Role
from app.domain.order import Order
from app.domain.user import User
from app.presentation.telegram.keyboards.menu import language_keyboard, main_menu_keyboard
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import View


@dataclass(frozen=True)
class CommonMenuPresenter(BasePresenter):
    i18n: I18nContext

    def greeting(self, user: User, balance: Decimal, active: list[Order], server_url: str) -> View:
        messages = self.i18n.messages.greeting
        line = ""
        if active:
            deadlines = [o.deadline_at for o in active if o.executor_id and o.deadline_at]
            line = "\n" + (
                messages.orders_until(count=len(active), time=min(deadlines).strftime("%H:%M"))
                if deadlines
                else messages.orders(count=len(active))
            )
        return View(
            text=messages(name=html.quote(user.name), balance=fmt_usd(balance), orders=line),
            reply_markup=main_menu_keyboard(
                self.i18n, len(active), bool(user.roles & Role.EXECUTOR), server_url
            ),
        )

    def language(self) -> View:
        return View(text=self.i18n.messages.language(), reply_markup=language_keyboard(self.i18n))
