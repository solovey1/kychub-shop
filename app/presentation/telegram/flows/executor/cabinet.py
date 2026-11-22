import logging
from dataclasses import dataclass
from typing import Any, Final

from aiogram.types import Message

from app.application.errors.shop import BelowMinimum, InvalidInput, WalletNotSet
from app.application.interactors.executor_wallet import ExecutorWalletInteractor
from app.application.interactors.executors import ExecutorCabinetInteractor
from app.application.interactors.stats import ExecutorStats
from app.application.ports.telegram.messages_helper import MessageHelper
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.presentation.telegram.callbacks.executor import CDCabinet
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.executor.cabinet import ExecutorPresenter
from app.presentation.telegram.states.executor import WalletForm
from app.presentation.telegram.view.renderer import Renderer

logger: Final = logging.getLogger(__name__)


@dataclass(frozen=True)
class CabinetFlow(BaseFlow):
    user: User
    interactor: ExecutorCabinetInteractor
    stats: ExecutorStats
    wallet: ExecutorWalletInteractor
    presenter: ExecutorPresenter
    renderer: Renderer
    helper: MessageHelper
    effects: Effects

    async def section(self, cd: CDCabinet) -> Any:
        await self.helper.fsm.clear()
        match cd.section:
            case "balance":
                return await self.balance()
            case "rating":
                return await self.renderer.apply(
                    self.presenter.rating(await self.stats.stats(self.user.id))
                )
            case "wallet":
                return await self.renderer.apply(
                    self.presenter.wallet(await self.wallet.summary(self.user.id))
                )
            case "wallet_set":
                await self.helper.fsm.set_state(WalletForm.address)
                return await self.renderer.apply(self.presenter.ask_wallet())
            case "withdraw":
                return await self.withdraw()
            case "online" | "offline":
                return await self.set_online(cd.section == "online")
            case _:
                return await self.show()

    async def show(self) -> Any:
        overview = await self.interactor.overview(self.user.id)
        if overview is None:
            return await self.renderer.apply(self.presenter.text("messages-executor-no_profile"))
        return await self.renderer.apply(self.presenter.cabinet(overview))

    async def set_online(self, online: bool) -> Any:
        changed = await self.interactor.set_online(self.user.id, online)
        await self.show()
        if changed and online:  # after the cabinet: the offers arrive below it
            await self.effects.executor_online(self.user.id)
        elif changed:
            await self.effects.executor_offline(self.user.id)

    async def balance(self, notice: str | None = None) -> Any:
        summary = await self.wallet.summary(self.user.id)
        return await self.renderer.apply(self.presenter.balance(summary, notice))

    async def set_wallet(self, message: Message) -> Any:
        try:
            await self.wallet.set_wallet(self.user.id, message.text or "")
        except InvalidInput:
            return await self.renderer.apply(self.presenter.ask_wallet(error=True, current=True))
        await self.helper.fsm.clear()
        summary = await self.wallet.summary(self.user.id)
        await self.renderer.apply(
            self.presenter.wallet(
                summary, notice_key="messages-executor-wallet_saved", current=True
            )
        )

    async def withdraw(self) -> Any:
        try:
            withdrawal = await self.wallet.withdraw(self.user.id)
        except WalletNotSet:
            return await self.renderer.apply(
                self.presenter.text("messages-executor-wallet_missing")
            )
        except BelowMinimum:
            summary = await self.wallet.summary(self.user.id)
            return await self.renderer.apply(
                self.presenter.balance(summary, self.presenter.below_minimum(summary.minimum))
            )
        await self.balance(self.presenter.withdrawal_created(withdrawal.amount))
        await self.effects.withdrawal_created(self.user, withdrawal)
