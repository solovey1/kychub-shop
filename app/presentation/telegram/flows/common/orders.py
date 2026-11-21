from dataclasses import dataclass
from typing import Any

from app.application.interactors.orders import OrdersInteractor
from app.domain.user import User
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.common.orders import OrdersPresenter
from app.presentation.telegram.view.renderer import Renderer


@dataclass(frozen=True)
class OrdersFlow(BaseFlow):
    user: User
    interactor: OrdersInteractor
    presenter: OrdersPresenter
    renderer: Renderer

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
