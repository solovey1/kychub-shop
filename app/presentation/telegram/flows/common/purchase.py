import logging
from dataclasses import dataclass
from typing import Any, Final
from uuid import uuid4

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram.types import ForceReply, Message

from app.application.errors.base import InsufficientFunds
from app.application.errors.shop import InvalidInput, OutOfStock, ProductUnavailable, PromoError
from app.application.i18n_text import pick_i18n
from app.application.interactors.dispatch import DispatchInteractor
from app.application.interactors.purchase import Prepared, PurchaseInteractor
from app.application.models.config import AppConfig
from app.application.models.form_schema import FieldType
from app.application.ports.telegram.messages_helper import MessageHelper
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.domain.user import User
from app.infrastructure.telegram.offers import OfferService
from app.presentation.telegram.callbacks.purchase import CDPurchase
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.common.purchase import PurchasePresenter
from app.presentation.telegram.states.purchase import PurchaseForm
from app.presentation.telegram.view.models import RenderMode, View
from app.presentation.telegram.view.renderer import Renderer

logger: Final[logging.Logger] = logging.getLogger(__name__)


@dataclass(frozen=True)
class PurchaseFlow(BaseFlow):
    """One card message is edited through the questions and the checkout (FSM data:
    variant_id, idx, answers, promo_code, prev, message_id, prompt_id, editing, purchase_token)."""

    user: User
    interactor: PurchaseInteractor
    presenter: PurchasePresenter
    renderer: Renderer
    helper: MessageHelper
    bot: Bot
    config: AppConfig
    dispatcher: DispatchInteractor
    offers: OfferService

    async def _render(self, view: View) -> None:
        result = await self.renderer.apply(view)
        if isinstance(result, Message):
            await self.helper.fsm.update_data(message_id=result.message_id)

    async def _say(self, key: str, *, current: bool = False) -> None:
        view = self.presenter.simple(key)
        if current:
            view.mode = RenderMode.CURRENT
        await self._render(view)

    async def _drop_prompt(self) -> None:
        """Removes the short message that carries the input placeholder."""
        fsm = self.helper.fsm
        prompt_id = (await fsm.get_data()).get("prompt_id")
        if prompt_id:
            await self.helper.delete(message_id=prompt_id)
            await fsm.update_data(prompt_id=None)

    async def _end(self) -> None:
        await self._drop_prompt()
        await self.helper.fsm.clear()

    async def _send_prompt(self, prep: Prepared, idx: int) -> None:
        field = prep.form.fields[idx]
        if field.type is FieldType.choice:  # answered with buttons, nothing to type
            return
        text, placeholder = self.presenter.prompt(field)
        message = await self.bot.send_message(
            self.helper.get_chat_id(),
            text,
            reply_markup=ForceReply(input_field_placeholder=placeholder),
        )
        await self.helper.fsm.update_data(prompt_id=message.message_id)

    async def _load(
        self, *, current: bool = False, silent: bool = False
    ) -> tuple[Prepared, dict[str, Any]] | None:
        data = await self.helper.fsm.get_data()
        if "variant_id" not in data:
            if not silent:
                await self._say("expired", current=current)
            return None
        try:
            return await self.interactor.prepare(data["variant_id"]), data
        except OutOfStock:
            await self._end()
            await self._say("out_of_stock", current=current)
        except ProductUnavailable:
            await self._end()
            await self._say("unavailable", current=current)
        return None

    async def start(self, variant_id: int) -> None:
        await self._end()
        try:
            prep = await self.interactor.prepare(variant_id)
        except OutOfStock:
            return await self._say("out_of_stock")
        except ProductUnavailable:
            return await self._say("unavailable")
        prev = (
            await self.interactor.previous_answers(self.user.id, prep.product.id)
            if prep.form.fields
            else {}
        )
        await self.helper.fsm.update_data(
            variant_id=variant_id,
            idx=0,
            answers={},
            promo_code=None,
            prev=prev,
            editing=False,
            message_id=self.helper.find_message_id(),
        )
        await self._step(prep, current=False)

    async def _step(self, prep: Prepared, *, current: bool, reason: str | None = None) -> None:
        fsm = self.helper.fsm
        data = await fsm.get_data()
        idx = data["idx"]
        if idx >= len(prep.form.fields):
            return await self._confirm(prep, current=current)
        await fsm.set_state(PurchaseForm.answer)
        await self._render(
            self.presenter.card(
                prep, data["answers"], idx, data.get("prev", {}), current=current, reason=reason
            )
        )
        await self._drop_prompt()
        await self._send_prompt(prep, idx)

    async def _accept(
        self, prep: Prepared, data: dict[str, Any], value: str, *, current: bool
    ) -> None:
        field = prep.form.fields[data["idx"]]
        # a changed answer goes straight back to the checkout
        idx = len(prep.form.fields) if data.get("editing") else data["idx"] + 1
        await self.helper.fsm.update_data(
            answers={**data["answers"], field.key: value}, idx=idx, editing=False
        )
        await self._step(prep, current=current)

    async def answer_message(self, message: Message) -> None:
        ctx = await self._load(current=True)
        if ctx is None:
            return
        prep, data = ctx
        field = prep.form.fields[data["idx"]]
        reason: str | None = None
        value = ""
        if field.type is FieldType.file:
            if message.document:
                value = message.document.file_id
            elif message.photo:
                value = message.photo[-1].file_id
            else:
                reason = self.presenter.reason("not_file")
        elif not message.text:
            reason = self.presenter.reason("not_text")
        else:
            try:
                value = field.validate_value(message.text)
            except ValueError as e:
                reason = self.presenter.reason(str(e))
        if reason is not None:
            return await self._step(prep, current=True, reason=reason)
        await self._accept(prep, data, value, current=True)

    async def _confirm(
        self,
        prep: Prepared,
        *,
        current: bool,
        promo_error: str | None = None,
        pick: bool = False,
    ) -> None:
        fsm = self.helper.fsm
        await self._drop_prompt()
        data = await fsm.get_data()
        promo_code: str | None = data.get("promo_code")
        quote = await self.interactor.quote(self.user.id, prep.variant.id, promo_code)
        if quote.promo_error:
            promo_error, promo_code = quote.promo_error, None
            await fsm.update_data(promo_code=None)
        # new token per shown screen: the price on it may differ from the previous one
        await fsm.update_data(purchase_token=uuid4().hex)
        await fsm.set_state(None)
        await self._render(
            self.presenter.confirm(
                prep,
                data["answers"],
                quote,
                promo_code,
                current=current,
                promo_error=promo_error,
                pick=pick,
            )
        )

    async def action(self, cd: CDPurchase) -> None:
        if cd.action == "cancel":
            await self._end()
            return await self._say("cancelled")
        if cd.action == "pay":
            return await self.pay()
        ctx = await self._load()
        if ctx is None:
            return
        prep, data = ctx
        fields = prep.form.fields
        match cd.action:
            case "promo":
                await self.helper.fsm.set_state(PurchaseForm.promo)
                await self._render(self.presenter.ask_promo())
            case "back":
                await self._confirm(prep, current=False)
            case "edit":
                await self._confirm(prep, current=False, pick=True)
            case "field" if 0 <= cd.value < len(fields):
                await self.helper.fsm.update_data(idx=cd.value, editing=True)
                await self._step(prep, current=False)
            case "choice" | "skip" | "prev" if data["idx"] < len(fields):
                await self._pick(prep, data, cd)

    async def _pick(self, prep: Prepared, data: dict[str, Any], cd: CDPurchase) -> None:
        """An answer given with a button: an option, "skip" or the previous answer."""
        field = prep.form.fields[data["idx"]]
        options = field.options or []
        if cd.action == "choice":
            value = options[cd.value] if 0 <= cd.value < len(options) else None
        elif cd.action == "prev":
            value = self.presenter.prev_value(field, data.get("prev", {}))
        else:
            value = "" if not field.required else None
        if value is not None:
            await self._accept(prep, data, field.validate_value(value), current=False)

    async def apply_promo(self, message: Message) -> None:
        ctx = await self._load(current=True)
        if ctx is None:
            return
        prep, _ = ctx
        await self.helper.fsm.update_data(promo_code=(message.text or "").strip() or None)
        await self._confirm(prep, current=True)

    async def pay(self) -> None:
        ctx = await self._load(silent=True)  # a repeated tap after success must not overwrite it
        if ctx is None:
            return
        prep, data = ctx
        token = data.get("purchase_token")
        if not token:
            return await self._say("expired")
        quote = await self.interactor.quote(self.user.id, prep.variant.id, data.get("promo_code"))
        if quote.promo_error or quote.total > quote.balance:
            return await self._confirm(prep, current=False)  # shows what changed
        try:
            order = await self.interactor.purchase(
                self.user.id,
                prep.variant.id,
                data["answers"],
                data.get("promo_code"),
                token,
            )
        except InsufficientFunds:
            return await self._confirm(prep, current=False)
        except OutOfStock:
            await self._end()
            return await self._say("out_of_stock")
        except (ProductUnavailable, InvalidInput):
            await self._end()
            return await self._say("unavailable")
        except PromoError as e:
            await self.helper.fsm.update_data(promo_code=None)
            return await self._confirm(prep, current=False, promo_error=e.code)
        await self.helper.fsm.clear()
        await self._deliver(order)
        await self._dispatch(order)

    async def _deliver(self, order: Order) -> None:
        receipt, result, file = self.presenter.delivered(order)
        await self.renderer.apply(receipt)
        if result is not None:
            await self.renderer.apply(result)
        if file is not None:
            await self.renderer.send_file(f"order-{order.id}.txt", file)
        if order.snapshot.get("type") == "manual":
            title = pick_i18n(order.snapshot.get("product"), "ru")
            text = self.presenter.admin_manual(order, self.user, title)
            try:
                await self.bot.send_message(self.config.common.admin_chat_id, text)
            except TelegramAPIError:
                logger.exception("could not notify admins about order %s", order.id)

    async def _dispatch(self, order: Order) -> None:
        """Offer a queued order to executors. The buyer already has their confirmation."""
        if order.status is not OrderStatus.in_queue:
            return
        try:
            await self.offers.announce(await self.dispatcher.dispatch(order.id))
        except Exception:
            logger.exception("dispatching order %s failed", order.id)
