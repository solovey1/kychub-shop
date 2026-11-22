from dataclasses import dataclass
from typing import Any

from aiogram_i18n import I18nContext
from aiogram_i18n.cores import FluentRuntimeCore

from app.application.interactors.balance import BalanceInteractor
from app.application.interactors.orders import OrdersInteractor
from app.application.models.config import AppConfig
from app.application.ports.telegram.messages_helper import MessageHelper
from app.domain.user import User
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.flows.common.nav import ScreenTracker
from app.presentation.telegram.presenters.common.menu import CommonMenuPresenter
from app.presentation.telegram.view.models import RenderMode
from app.presentation.telegram.view.renderer import Renderer


@dataclass(frozen=True)
class CommonMenuFlow(BaseFlow):
    user: User
    balance: BalanceInteractor
    orders: OrdersInteractor
    config: AppConfig
    presenter: CommonMenuPresenter
    renderer: Renderer
    i18n: I18nContext
    core: FluentRuntimeCore
    helper: MessageHelper
    screens: ScreenTracker

    async def _card(self, *, new: bool = False) -> Any:
        amount = await self.balance.balance(self.user.id)
        held = await self.balance.held(self.user.id)
        active = await self.orders.active(self.user.id)
        reorders = await self.orders.reorderable(self.user.id)
        view = self.presenter.greeting(
            self.user, amount, held, active, reorders, self.config.server.url
        )
        if new:
            view.mode = RenderMode.NEW
        return await self.renderer.apply(view)

    async def greeting(self) -> Any:
        return await self._card()

    async def start(self) -> None:
        """A short message carries the bottom keyboard (only a new message can), then the card."""
        await self.screens.drop()
        await self.helper.bot.send_message(
            self.helper.get_chat_id(),
            self.presenter.welcome(self.user),
            reply_markup=self.presenter.nav(),
        )
        await self._card(new=True)
        await self.screens.track(self.renderer.last_sent)

    async def language(self) -> Any:
        return await self.renderer.apply(self.presenter.language())

    async def set_language(self, code: str) -> Any:
        if code not in self.core.available_locales:
            return await self.language()
        await self.i18n.set_locale(code)  # UserManager persists it, the context switches over
        await (
            self.helper.delete()
        )  # the language screen; the bottom labels change with a new start
        return await self.start()
