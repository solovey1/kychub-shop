from dataclasses import dataclass
from typing import Any

from app.application.errors.shop import OrderUnavailable
from app.application.interactors.orders import OrdersInteractor
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.presentation.telegram.callbacks.orders import CDCancel
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.common.orders import OrdersPresenter
from app.presentation.telegram.view.renderer import Renderer


@dataclass(frozen=True)
class OrdersFlow(BaseFlow):
    user: User
    interactor: OrdersInteractor
    presenter: OrdersPresenter
    renderer: Renderer
    effects: Effects

    async def list(self, page: int) -> Any:
        orders, total, page = await self.interactor.list_orders(self.user.id, page)
        return await self.renderer.apply(self.presenter.orders(orders, total, page))

    async def show(self, order_id: int, page: int) -> None:
        order = await self.interactor.get(self.user.id, order_id)
        if order is None:
            await self.renderer.apply(self.presenter.not_found(page))
            return
        view, file = self.presenter.order(order, page)
        await self.renderer.apply(view)
        if file is not None:
            await self.renderer.send_file(f"order-{order.id}.txt", file)

    async def cancel(self, cd: CDCancel) -> Any:
        if not cd.ok:
            return await self.renderer.apply(self.presenter.cancel_confirm(cd.id, cd.page))
        try:
            refund = await self.interactor.cancel(self.user.id, cd.id)
        except OrderUnavailable:  # taken meanwhile, or not the buyer order
            return await self.show(cd.id, cd.page)
        await self.renderer.apply(self.presenter.cancelled(cd.id, refund.amount, cd.page))
        await self.effects.order_cancelled(cd.id)
