from dataclasses import dataclass
from decimal import Decimal
from typing import Any
from uuid import uuid4

from aiogram.types import Message

from app.application.errors.base import InsufficientFunds, LedgerConflict
from app.application.errors.shop import AlreadyRated, InvalidAmount, OrderUnavailable
from app.application.i18n_text import fmt_usd
from app.application.interactors.balance import parse_money
from app.application.interactors.feedback import ReviewInteractor, TipInteractor
from app.application.ports.telegram.messages_helper import MessageHelper
from app.domain.user import User
from app.infrastructure.telegram.notifier import Notifier
from app.presentation.telegram.callbacks.feedback import CDRate, CDTip
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.common.feedback import FeedbackPresenter
from app.presentation.telegram.states.feedback import TipForm
from app.presentation.telegram.view.renderer import Renderer


@dataclass(frozen=True)
class FeedbackFlow(BaseFlow):
    user: User
    reviews: ReviewInteractor
    tips: TipInteractor
    presenter: FeedbackPresenter
    renderer: Renderer
    helper: MessageHelper
    notifier: Notifier

    async def rate(self, cd: CDRate) -> Any:
        await self.helper.fsm.clear()
        if cd.score == 0:
            return await self.renderer.apply(self.presenter.ask(cd.id))
        try:
            await self.reviews.rate(self.user.id, cd.id, cd.score)
        except AlreadyRated:
            return await self.renderer.apply(self.presenter.note("already_rated"))
        except OrderUnavailable:
            return await self.renderer.apply(self.presenter.note("unavailable"))
        await self.renderer.apply(self.presenter.rated(cd.id, cd.score))

    async def tip(self, cd: CDTip) -> Any:
        fsm = self.helper.fsm
        if cd.c == 0:  # a new token per shown screen
            await fsm.clear()
            token = uuid4().hex[:12]
            return await self.renderer.apply(self.presenter.tip_choose(cd.id, token))
        if cd.c < 0:
            await fsm.set_state(TipForm.amount)
            await fsm.update_data(order_id=cd.id, token=cd.t or uuid4().hex[:12])
            return await self.renderer.apply(self.presenter.tip_ask(cd.id))
        await self._tip(cd.id, Decimal(cd.c) / 100, cd.t, current=False)

    async def custom_amount(self, message: Message) -> Any:
        data = await self.helper.fsm.get_data()
        if "order_id" not in data:
            return
        try:
            amount = parse_money(message.text or "")
        except InvalidAmount:
            return await self.renderer.apply(
                self.presenter.tip_ask(data["order_id"], error=True, current=True)
            )
        await self._tip(data["order_id"], amount, data["token"], current=True)

    async def _tip(self, order_id: int, amount: Decimal, token: str, *, current: bool) -> Any:
        try:
            executor_id = await self.tips.tip(self.user.id, order_id, amount, token)
        except InvalidAmount:
            return await self.renderer.apply(
                self.presenter.tip_ask(order_id, error=True, current=current)
            )
        except InsufficientFunds:
            await self.helper.fsm.clear()
            return await self.renderer.apply(self.presenter.note("tip_funds", current=current))
        except LedgerConflict:  # the same screen was used for a different amount
            await self.helper.fsm.clear()
            return await self.renderer.apply(self.presenter.note("tip_done", current=current))
        except OrderUnavailable:
            await self.helper.fsm.clear()
            return await self.renderer.apply(self.presenter.note("unavailable", current=current))
        await self.helper.fsm.clear()
        await self.renderer.apply(self.presenter.tipped(amount, current=current))
        await self.notifier.send(
            executor_id, "messages-executor-tip", id=str(order_id), amount=fmt_usd(amount)
        )
