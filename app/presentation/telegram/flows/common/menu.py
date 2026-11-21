from dataclasses import dataclass
from typing import Any

from aiogram_i18n import I18nContext
from aiogram_i18n.cores import FluentRuntimeCore

from app.application.interactors.balance import BalanceInteractor
from app.domain.user import User
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.common.menu import CommonMenuPresenter
from app.presentation.telegram.view.renderer import Renderer


@dataclass(frozen=True)
class CommonMenuFlow(BaseFlow):
    user: User
    balance: BalanceInteractor
    presenter: CommonMenuPresenter
    renderer: Renderer
    i18n: I18nContext
    core: FluentRuntimeCore

    async def greeting(self) -> Any:
        amount = await self.balance.balance(self.user.id)
        return await self.renderer.apply(self.presenter.greeting(self.user, amount))

    async def language(self) -> Any:
        return await self.renderer.apply(self.presenter.language())

    async def set_language(self, code: str) -> Any:
        if code not in self.core.available_locales:
            return await self.language()
        await self.i18n.set_locale(code)  # UserManager persists it, the context switches over
        return await self.greeting()
