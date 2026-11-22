from dataclasses import dataclass
from typing import Any

from aiogram.types import CallbackQuery

from app.application.errors.shop import Conflict, OrderUnavailable
from app.application.interactors.deadlines import ExtensionInteractor
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.interactors.orders import OrdersInteractor
from app.application.ports.telegram.messages_helper import MessageHelper
from app.domain.enums.order import OrderStatus
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.presentation.telegram.callbacks.orders import CDCancel, CDDeal, CDExtAnswer
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
    extension: ExtensionInteractor
    review: OrderReviewInteractor
    helper: MessageHelper

    async def list(self, page: int) -> Any:
        orders, total, page = await self.interactor.list_orders(self.user.id, page)
        return await self.renderer.apply(self.presenter.orders(orders, total, page))

    async def show(self, order_id: int, page: int) -> None:
        order = await self.interactor.get(self.user.id, order_id)
        if order is None:
            await self.renderer.apply(self.presenter.not_found(page))
            return
        events = await self.interactor.events(order.id)
        alias = await self.interactor.executor_alias(order)
        reorder = await self.interactor.can_reorder(order.variant_id)
        reserved = await self.interactor.reserved(order)
        pending = await self.interactor.pending_extension(order)
        confirm_at = await self.interactor.confirm_at(order)
        view, file = self.presenter.order(
            order, page, events, alias, reorder, reserved, pending, confirm_at
        )
        await self.renderer.apply(view)
        if file is not None:
            await self.renderer.send_file(f"order-{order.id}.txt", file)
        if order.status is OrderStatus.ready and order.result:
            await self.effects.notices.files(self.user.id, list(order.result.get("files", [])))

    async def deal(self, cd: CDDeal) -> None:
        """The buyer answers a submitted order."""
        if cd.action != "ok":
            return
        try:
            order = await self.review.confirm_by_buyer(self.user.id, cd.id)
        except OrderUnavailable:  # confirmed already (by him, support or the timer), or not his
            return await self.show(cd.id, cd.page)
        await self.renderer.apply(self.presenter.confirmed(order.id, cd.page))
        await self.effects.order_confirmed(order)

    async def answer_extension(self, cd: CDExtAnswer) -> None:
        try:
            answer = await self.extension.answer(self.user.id, cd.id, cd.rid, bool(cd.ok))
        except (Conflict, OrderUnavailable):  # answered already, or the order left the executor
            update = self.helper.update
            if isinstance(update, CallbackQuery):
                await update.answer(self.presenter.extension_stale(), show_alert=True)
            return
        await self.renderer.apply(self.presenter.extension_answered(answer))
        await self.effects.extension_answered(answer)

    async def cancel(self, cd: CDCancel) -> Any:
        if not cd.ok:
            return await self.renderer.apply(self.presenter.cancel_confirm(cd.id, cd.page))
        try:
            refund = await self.interactor.cancel(self.user.id, cd.id)
        except OrderUnavailable:  # taken meanwhile, or not the buyer order
            return await self.show(cd.id, cd.page)
        await self.renderer.apply(self.presenter.cancelled(cd.id, refund.amount, cd.page))
        await self.effects.order_cancelled(cd.id)
