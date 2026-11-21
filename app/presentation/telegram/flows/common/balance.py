import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message

from app.application.errors.base import AppError
from app.application.errors.shop import InvalidAmount, PromoError, TopupDisabled
from app.application.i18n_text import fmt_usd
from app.application.interactors.balance import BalanceInteractor, parse_money
from app.application.ports.telegram.messages_helper import MessageHelper
from app.domain.user import User
from app.presentation.telegram.callbacks.balance import CDBalance
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.common.balance import BalancePresenter
from app.presentation.telegram.states.balance import BalanceForm
from app.presentation.telegram.view.renderer import Renderer

logger: Final[logging.Logger] = logging.getLogger(__name__)


@dataclass(frozen=True)
class BalanceFlow(BaseFlow):
    user: User
    interactor: BalanceInteractor
    presenter: BalancePresenter
    renderer: Renderer
    helper: MessageHelper
    bot: Bot

    async def show(self, *, current: bool = False, notice: str | None = None) -> Any:
        amount, entries = await self.interactor.summary(self.user.id)
        return await self.renderer.apply(
            self.presenter.balance(amount, entries, current=current, notice=notice)
        )

    async def action(self, cd: CDBalance) -> None:
        fsm = self.helper.fsm
        await fsm.clear()
        match cd.action:
            case "topup":
                await self.renderer.apply(
                    self.presenter.topup(self.interactor.test_payments_enabled)
                )
            case "custom":
                if self.interactor.test_payments_enabled:
                    await self._ask(BalanceForm.amount, "messages-topup-custom_ask")
            case "promo":
                await self._ask(BalanceForm.promo, "messages-redeem-ask")
            case _:
                await self.show()

    async def _ask(
        self, state: Any, key: str, error: str | None = None, current: bool = False
    ) -> None:
        fsm = self.helper.fsm
        await fsm.set_state(state)
        if not current:
            await fsm.update_data(message_id=self.helper.find_message_id())
        await self.renderer.apply(self.presenter.ask(key, error=error, current=current))

    async def topup(self, amount: int) -> Any:
        try:
            payment = await self.interactor.test_topup(self.user.id, Decimal(amount))
        except (TopupDisabled, InvalidAmount):
            return await self.renderer.apply(self.presenter.topup(False))
        await self.show(notice=self.presenter.topup_done(payment.amount))

    async def custom_amount(self, message: Message) -> Any:
        try:
            amount = parse_money(message.text or "")
            payment = await self.interactor.test_topup(self.user.id, amount)
        except InvalidAmount:
            return await self._ask(
                BalanceForm.amount,
                "messages-topup-custom_ask",
                self.presenter.invalid_amount(),
                current=True,
            )
        except TopupDisabled:
            await self.helper.fsm.clear()
            return await self.renderer.apply(self.presenter.topup(False))
        await self.helper.fsm.clear()
        await self.show(current=True, notice=self.presenter.topup_done(payment.amount))

    async def redeem(self, message: Message) -> None:
        try:
            bonus = await self.interactor.redeem_bonus(self.user.id, message.text or "")
        except PromoError as e:
            return await self._ask(
                BalanceForm.promo, "messages-redeem-ask", self.presenter.redeem_error(e.code), True
            )
        await self.helper.fsm.clear()
        await self.show(current=True, notice=self.presenter.redeem_done(bonus))

    async def admin_topup(self, args: str | None) -> None:
        parts = (args or "").split(maxsplit=2)
        try:
            user_id = int(parts[0])
            amount = parse_money(parts[1])
        except (IndexError, ValueError, InvalidAmount):
            return await self._reply("messages-admin-topup_usage")
        comment = parts[2] if len(parts) > 2 else ""
        try:
            entry = await self.interactor.admin_topup(self.user.id, user_id, amount, comment)
        except AppError:  # unknown user, would go negative, zero amount
            return await self._reply("messages-admin-topup_failed")
        await self._reply(
            "messages-admin-topup_done",
            amount=fmt_usd(entry.amount),
            user_id=str(user_id),
            balance=fmt_usd(entry.balance_after),
        )
        target = await self.interactor.get_user(user_id)
        if target is not None:
            text = self.presenter.notice_for(target.language, entry.amount)
            try:
                await self.bot.send_message(user_id, text)
            except TelegramAPIError:
                logger.info("could not notify user %s about the balance change", user_id)

    async def _reply(self, key: str, **kwargs: str) -> None:
        await self.renderer.apply(self.presenter.text(key, **kwargs))
