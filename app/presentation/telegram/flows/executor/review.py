import logging
from dataclasses import dataclass
from typing import Awaitable, Final

from aiogram.types import Message

from app.application.errors.shop import OrderUnavailable
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.ports.telegram.messages_helper import MessageHelper
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.infrastructure.telegram.notices import OrderNotices
from app.presentation.telegram.callbacks.executor import CDReview
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.executor.review import ReviewPresenter
from app.presentation.telegram.states.executor import ReviewForm
from app.presentation.telegram.view.renderer import Renderer

logger: Final = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReviewFlow(BaseFlow):
    user: User
    interactor: OrderReviewInteractor
    presenter: ReviewPresenter
    notices: OrderNotices
    effects: Effects
    renderer: Renderer
    helper: MessageHelper

    async def action(self, cd: CDReview) -> None:
        await self.helper.fsm.clear()
        match cd.action:
            case "open":
                await self.open(cd.id)
            case "ok":
                await self.confirm(cd.id)
            case "back":
                await self.helper.fsm.set_state(ReviewForm.comment)
                await self.helper.fsm.update_data(order_id=cd.id)
                await self.renderer.apply(self.presenter.ask_comment(cd.id))
            case "fail":
                await self.renderer.apply(self.presenter.fail_confirm(cd.id))
            case "failok":
                await self.fail(cd.id)

    async def open(self, order_id: int, notice_key: str | None = None) -> None:
        view = await self.interactor.get(order_id)
        if view is None:
            return await self._say("messages-review-missing", order_id)
        await self.renderer.apply(self.presenter.card(view, notice_key))
        await self.notices.files(self.user.id, view.files)

    async def confirm(self, order_id: int) -> None:
        try:
            order = await self.interactor.confirm(self.user.id, order_id)
        except OrderUnavailable:
            return await self._say("messages-review-unavailable", order_id)
        await self.open(order_id, "messages-review-confirmed")
        await self.effects.order_confirmed(order)

    async def send_back(self, message: Message) -> None:
        data = await self.helper.fsm.get_data()
        order_id = data.get("order_id")
        comment = (message.text or "").strip()
        if order_id is None or not comment:
            return
        await self.helper.fsm.clear()
        try:
            order = await self.interactor.send_back(self.user.id, order_id, comment[:1000])
        except OrderUnavailable:
            return await self._say("messages-review-unavailable", order_id, current=True)
        await self._say("messages-review-sent_back", order_id, current=True)
        await self.effects.order_sent_back(order, comment[:1000])

    async def fail(self, order_id: int) -> None:
        try:
            refund = await self.interactor.fail_and_refund(self.user.id, order_id, "manual")
        except OrderUnavailable:
            return await self._say("messages-review-unavailable", order_id)
        await self._say("messages-review-failed", order_id)
        await self.effects.order_failed(refund)

    async def _say(self, key: str, order_id: int, *, current: bool = False) -> None:
        await self.renderer.apply(self.presenter.text(key, order_id, current=current))

    @staticmethod
    async def _safe(call: Awaitable[object], order_id: int) -> None:
        try:
            await call
        except Exception:
            logger.exception("notification about order %s failed", order_id)
