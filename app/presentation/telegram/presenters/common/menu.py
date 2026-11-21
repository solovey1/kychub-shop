from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from aiogram_i18n import I18nContext

from app.domain.enums.roles import Role
from app.domain.user import User
from app.presentation.telegram.keyboards.menu import language_keyboard, main_menu_keyboard
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import View


@dataclass(frozen=True)
class CommonMenuPresenter(BasePresenter):
    i18n: I18nContext

    def greeting(self, user: User, balance: Decimal) -> View:
        return View(
            text=self.i18n.messages.greeting(name=user.mention),
            reply_markup=main_menu_keyboard(self.i18n, balance, bool(user.roles & Role.EXECUTOR)),
        )

    def language(self) -> View:
        return View(text=self.i18n.messages.language(), reply_markup=language_keyboard(self.i18n))
