from dataclasses import dataclass

from app.application.errors.shop import OrderUnavailable
from app.application.interactors.dispatch import DispatchInteractor
from app.domain.user import User
from app.infrastructure.telegram.offers import OfferService
from app.presentation.telegram.callbacks.executor import CDOrderAct
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.executor.cabinet import ExecutorPresenter
from app.presentation.telegram.view.renderer import Renderer


@dataclass(frozen=True)
class ExecutorOrdersFlow(BaseFlow):
    user: User
    dispatcher: DispatchInteractor
    offers: OfferService
    presenter: ExecutorPresenter
    renderer: Renderer

    async def action(self, cd: CDOrderAct) -> None:
        match cd.action:
            case "take":
                await self.take(cd.id)
            case "refuse":
                await self.refuse(cd.id)

    async def take(self, order_id: int) -> None:
        if not await self.dispatcher.take(self.user.id, order_id):
            return await self._say("messages-executor-take_failed", order_id)
        await self.renderer.apply(self.presenter.taken(order_id))
        await self.offers.close(
            order_id, "messages-executor-offer_taken", except_chat=self.user.id
        )

    async def refuse(self, order_id: int) -> None:
        try:
            result = await self.dispatcher.refuse(self.user.id, order_id)
        except OrderUnavailable:
            return await self._say("messages-executor-refuse_failed", order_id)
        await self._say("messages-executor-refused", order_id)
        await self.offers.announce(result)

    async def _say(self, key: str, order_id: int) -> None:
        await self.renderer.apply(self.presenter.text(key, id=str(order_id)))
