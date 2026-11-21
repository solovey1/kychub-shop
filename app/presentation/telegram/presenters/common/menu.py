from __future__ import annotations

from dataclasses import dataclass

from aiogram_i18n import I18nContext

from app.domain.user import User
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import View


@dataclass(frozen=True)
class CommonMenuPresenter(BasePresenter):
    i18n: I18nContext

    def greeting(self, user: User) -> View:
        return View(text=self.i18n.messages.greeting(name=user.mention))
