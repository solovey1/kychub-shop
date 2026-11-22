from dataclasses import dataclass
from typing import Any

from aiogram.types import CallbackQuery, Message

from app.application.errors.shop import Conflict, OrderUnavailable
from app.application.interactors.cancel_request import CancelRequestInteractor, cancel_state
from app.application.interactors.deadlines import ExtensionInteractor
from app.application.interactors.disputes import DisputeInteractor
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.interactors.orders import OrdersInteractor
from app.application.ports.telegram.messages_helper import MessageHelper
from app.domain.enums.order import OrderStatus
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.presentation.telegram.callbacks.orders import (
    CDCancel,
    CDCancelAsk,
    CDDeal,
    CDExtAnswer,
)
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.common.orders import OrdersPresenter
from app.presentation.telegram.states.support import DisputeForm
from app.presentation.telegram.view.renderer import Renderer


@dataclass(frozen=True)
class OrdersFlow(BaseFlow):
    user: User
    interactor: OrdersInteractor
    presenter: OrdersPresenter
    renderer: Renderer
    effects: Effects
    extension: ExtensionInteractor
    cancel_requests: CancelRequestInteractor
    review: OrderReviewInteractor
    disputes: DisputeInteractor
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
        dispute = await self.interactor.dispute(order)
        cancel = cancel_state(events)
        view, file = self.presenter.order(
            order,
            page,
            events,
            alias,
            reorder,
            reserved,
            pending,
            confirm_at,
            dispute,
            cancel,
            await self.interactor.executor_rating(order),
        )
        await self.renderer.apply(view)
        if file is not None:
            await self.renderer.send_file(f"order-{order.id}.txt", file)
        if order.status is OrderStatus.ready and order.result:
            await self.effects.notices.files(self.user.id, list(order.result.get("files", [])))

    async def deal(self, cd: CDDeal) -> None:
        """The buyer answers a submitted order; the buyer or the executor calls support."""
        match cd.action:
            case "ok":
                await self._ok(cd)
            case "ask":
                await self.helper.fsm.set_state(DisputeForm.reason)
                await self.helper.fsm.update_data(order_id=cd.id, page=cd.page)
                await self.renderer.apply(self.presenter.dispute_ask(cd.id, cd.page))
            case "skip":
                await self._open_dispute(cd.id, cd.page, None)
            case "cancel":
                await self.helper.fsm.clear()
                await self._back(cd.id, cd.page)

    async def dispute_reason(self, message: Message) -> None:
        data = await self.helper.fsm.get_data()
        order_id = data.get("order_id")
        if order_id is None or not (message.text or "").strip():
            return
        await self._open_dispute(order_id, int(data.get("page", 0)), message.text)

    async def _ok(self, cd: CDDeal) -> None:
        try:
            order = await self.review.confirm_by_buyer(self.user.id, cd.id)
        except OrderUnavailable:  # confirmed already (by him, support or the timer), or not his
            return await self.show(cd.id, cd.page)
        await self.renderer.apply(self.presenter.confirmed(order.id, cd.page))
        await self.effects.order_confirmed(order, ask_rating=True)

    async def _open_dispute(self, order_id: int, page: int, reason: str | None) -> None:
        await self.helper.fsm.clear()
        try:
            news = await self.disputes.open(self.user.id, order_id, reason)
        except Conflict as e:
            if e.code == "not_accepted":  # an auto-assigned order nobody accepted yet
                await self.renderer.apply(self.presenter.dispute_not_accepted(order_id, page))
                return
            return await self._back(order_id, page)  # one is open already
        except OrderUnavailable:  # not his order, or it is no longer in work
            return await self._back(order_id, page)
        buyer = news.order.user_id == self.user.id
        await self.renderer.apply(self.presenter.dispute_opened(news, page, buyer=buyer))
        await self.effects.dispute_opened(news)

    async def _back(self, order_id: int, page: int) -> None:
        """To the order card: the buyer's here, the executor's is in his cabinet."""
        if await self.interactor.get(self.user.id, order_id) is not None:
            return await self.show(order_id, page)
        await self.renderer.apply(self.presenter.executor_back(order_id))

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

    async def ask_cancel(self, cd: CDCancelAsk) -> None:
        """The buyer asks the executor of an assigned order to agree to a cancellation."""
        try:
            ask = await self.cancel_requests.request(self.user.id, cd.id)
        except (Conflict, OrderUnavailable):  # pending, spent, a dispute, or the order moved on
            update = self.helper.update
            if isinstance(update, CallbackQuery):
                await update.answer(self.presenter.cancel_unavailable(), show_alert=True)
            return await self.show(cd.id, cd.page)
        await self.renderer.apply(self.presenter.cancel_asked(cd.id, cd.page))
        await self.effects.cancel_asked(ask)

    async def cancel(self, cd: CDCancel) -> Any:
        if not cd.ok:
            return await self.renderer.apply(self.presenter.cancel_confirm(cd.id, cd.page))
        try:
            refund = await self.interactor.cancel(self.user.id, cd.id)
        except OrderUnavailable:  # taken meanwhile, or not the buyer order
            return await self.show(cd.id, cd.page)
        await self.renderer.apply(self.presenter.cancelled(cd.id, refund.amount, cd.page))
        await self.effects.order_cancelled(cd.id)
