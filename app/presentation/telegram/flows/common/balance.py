import logging
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import CallbackQuery, Message

from app.application.errors.base import AppError
from app.application.errors.shop import (
    GatewayUnavailable,
    InvalidAmount,
    PromoError,
    TopupDisabled,
)
from app.application.i18n_text import fmt_usd
from app.application.interactors.balance import BalanceInteractor, parse_money
from app.application.interactors.topup import TopupInteractor
from app.application.ports.telegram.messages_helper import MessageHelper
from app.domain.enums.ledger import PaymentStatus
from app.domain.user import User
from app.presentation.telegram.callbacks.balance import CDBalance, CDCheck, CDPay
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.keyboards.balance import TOPUP_AMOUNTS
from app.presentation.telegram.presenters.common.balance import BalancePresenter
from app.presentation.telegram.states.balance import BalanceForm
from app.presentation.telegram.view.renderer import Renderer

logger: Final[logging.Logger] = logging.getLogger(__name__)

TEST_PROVIDER: Final = "test"


@dataclass(frozen=True)
class BalanceFlow(BaseFlow):
    user: User
    interactor: BalanceInteractor
    topup_interactor: TopupInteractor
    presenter: BalancePresenter
    renderer: Renderer
    helper: MessageHelper
    bot: Bot

    async def show(self, *, current: bool = False, notice: str | None = None) -> Any:
        amount, entries = await self.interactor.summary(self.user.id, 5)
        held = await self.interactor.held(self.user.id)
        return await self.renderer.apply(
            self.presenter.balance(amount, held, entries, current=current, notice=notice)
        )

    async def action(self, cd: CDBalance) -> None:
        fsm = self.helper.fsm
        await fsm.clear()
        match cd.action:
            case "topup":
                await self._topup_screen()
            case "custom":
                if self.topup_interactor.providers:
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

    async def _topup_screen(self) -> None:
        low, high = self.topup_interactor.limits
        amounts = [a for a in TOPUP_AMOUNTS if low <= a <= high]
        await self.renderer.apply(
            self.presenter.topup(bool(self.topup_interactor.providers), amounts)
        )

    async def _methods(self, amount: Decimal, *, current: bool = False) -> None:
        providers = self.topup_interactor.providers
        if not providers:
            return await self._topup_screen()
        await self.renderer.apply(self.presenter.methods(amount, providers, current=current))

    async def topup(self, amount: int) -> Any:
        try:
            await self._methods(self.topup_interactor.validate(Decimal(amount)))
        except InvalidAmount:
            await self._topup_screen()

    async def custom_amount(self, message: Message) -> Any:
        try:
            amount = self.topup_interactor.validate(parse_money(message.text or ""))
        except InvalidAmount:
            low, high = self.topup_interactor.limits
            return await self._ask(
                BalanceForm.amount,
                "messages-topup-custom_ask",
                self.presenter.invalid_amount(low, high),
                current=True,
            )
        await self.helper.fsm.clear()
        await self._methods(amount, current=True)

    async def pay(self, cd: CDPay) -> Any:
        try:
            payment, created = await self.topup_interactor.create(
                self.user.id, Decimal(cd.cents) / 100, cd.provider
            )
        except (InvalidAmount, TopupDisabled):
            return await self._topup_screen()
        except GatewayUnavailable:
            return await self.renderer.apply(self.presenter.gateway_error())
        if cd.provider == TEST_PROVIDER:
            return await self.check(CDCheck(id=payment.id))
        pay_id = self.topup_interactor.binance_pay_id if created.url is None else None
        await self.renderer.apply(self.presenter.invoice(payment, created.url, pay_id))

    async def check(self, cd: CDCheck) -> Any:
        try:
            payment = await self.topup_interactor.get(cd.id)
        except AppError:
            return await self.show()
        if payment.user_id != self.user.id:
            return await self.show()
        payment, _ = await self.topup_interactor.sync(payment.id)
        if payment.status is PaymentStatus.success:
            return await self.show(notice=self.presenter.topup_done(payment.amount))
        update = self.helper.update
        if isinstance(update, CallbackQuery):
            await update.answer(self.presenter.check_result(payment.status), show_alert=True)

    async def redeem(self, message: Message) -> None:
        try:
            bonus = await self.interactor.redeem_bonus(self.user.id, message.text or "")
        except PromoError as e:
            return await self._ask(
                BalanceForm.promo, "messages-redeem-ask", self.presenter.redeem_error(e.code), True
            )
        await self.helper.fsm.clear()
        await self.show(current=True, notice=self.presenter.redeem_done(bonus))

    async def admin_topup(self, args: str | None, token: str) -> None:
        parts = (args or "").split(maxsplit=2)
        try:
            user_id = int(parts[0])
            amount = parse_money(parts[1])
        except (IndexError, ValueError, InvalidAmount):
            return await self._reply("messages-admin-topup_usage")
        comment = parts[2] if len(parts) > 2 else ""
        try:
            entry = await self.interactor.admin_topup(
                self.user.id, user_id, amount, comment, token
            )
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
