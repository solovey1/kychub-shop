from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from aiogram import html
from aiogram.types import ReplyKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_time, fmt_usd
from app.application.interactors.catalog import VariantView
from app.domain.catalog import Product
from app.domain.enums.roles import Role
from app.domain.order import Order
from app.domain.user import User
from app.presentation.telegram.keyboards.menu import (
    language_keyboard,
    main_menu_keyboard,
    nav_keyboard,
)
from app.presentation.telegram.presenters.base import BasePresenter, Keys
from app.presentation.telegram.view.models import View

# who sees the «Управление» tab of the Mini App (mirrors webapp/src/admin/access.ts)
STAFF: Role = (
    Role.OWNER
    | Role.ADMIN
    | Role.MANAGER
    | Role.CAN_CATALOG
    | Role.CAN_FINANCE
    | Role.CAN_USERS
    | Role.CAN_BROADCAST
)


@dataclass(frozen=True)
class CommonMenuPresenter(BasePresenter):
    i18n: I18nContext

    def welcome(self, user: User) -> str:
        return self.i18n.messages.welcome(name=html.quote(user.name))

    def greeting(
        self,
        user: User,
        balance: Decimal,
        held: Decimal,
        active: list[Order],
        reorders: list[tuple[VariantView, Product]],
        server_url: str,
    ) -> View:
        messages = Keys(self.i18n, "messages-greeting")
        line = ""
        if active:
            deadlines = [o.deadline_at for o in active if o.executor_id and o.deadline_at]
            line = "\n" + (
                messages.orders_until(
                    count=len(active), time=fmt_time(min(deadlines), user.timezone)
                )
                if deadlines
                else messages.orders(count=len(active))
            )
        return View(
            text=messages(balance=fmt_usd(balance), held=self._held(held), orders=line),
            reply_markup=main_menu_keyboard(
                self.i18n,
                reorders,
                bool(user.roles & Role.EXECUTOR),
                bool(user.roles & STAFF),
                server_url,
            ),
        )

    def _held(self, held: Decimal) -> str:
        return "\n" + self.i18n.messages.held(amount=fmt_usd(held)) if held > 0 else ""

    def nav(self) -> ReplyKeyboardMarkup:
        return nav_keyboard(self.i18n)

    def language(self) -> View:
        return View(text=self.i18n.messages.language(), reply_markup=language_keyboard(self.i18n))
