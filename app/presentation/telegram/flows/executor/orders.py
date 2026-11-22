import logging
from dataclasses import dataclass
from typing import Any, Final

from aiogram.types import CallbackQuery, Message

from app.application.errors.shop import (
    Conflict,
    ContactsBlocked,
    DeadlineExpired,
    InvalidInput,
    OrderUnavailable,
)
from app.application.interactors.cancel_request import CancelRequestInteractor
from app.application.interactors.deadlines import ExtensionInteractor
from app.application.interactors.dispatch import DispatchInteractor
from app.application.interactors.fulfillment_work import FulfillmentWorkInteractor
from app.application.interactors.info_request import InfoRequestInteractor
from app.application.models.form_schema import FieldType, FormSchema
from app.application.ports.telegram.messages_helper import MessageHelper
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.presentation.telegram.callbacks.executor import CDExt, CDOrderAct, CDXCancel, CDXResult
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.flows.common.files import (
    chat_lock,
    finish_files,
    is_straggler,
    take_file,
)
from app.presentation.telegram.presenters.common.purchase import PurchasePresenter
from app.presentation.telegram.presenters.executor.cabinet import ExecutorPresenter
from app.presentation.telegram.states.executor import InfoForm, ResultForm
from app.presentation.telegram.view.models import RenderMode
from app.presentation.telegram.view.renderer import Renderer

logger: Final = logging.getLogger(__name__)


@dataclass(frozen=True)
class ExecutorOrdersFlow(BaseFlow):
    user: User
    dispatcher: DispatchInteractor
    extensions: ExtensionInteractor
    cancel_requests: CancelRequestInteractor
    info_requests: InfoRequestInteractor
    work: FulfillmentWorkInteractor
    effects: Effects
    presenter: ExecutorPresenter
    purchase_presenter: PurchasePresenter
    renderer: Renderer
    helper: MessageHelper

    async def action(self, cd: CDOrderAct) -> None:
        match cd.action:
            case "take":
                await self.take(cd.id)
            case "accept":
                await self.accept(cd.id)
            case "refuse":
                await self.refuse(cd.id)
            case "info":
                await self.info_start(cd.id)

    async def take(self, order_id: int) -> None:
        if not await self.dispatcher.take(self.user.id, order_id):
            return await self._say("messages-executor-take_failed", order_id)
        await self.renderer.apply(self.presenter.taken(order_id, await self.work.code(order_id)))
        await self.effects.order_taken(order_id, self.user.id)

    async def accept(self, order_id: int) -> None:
        """«I take it» under an auto-assignment: the deadline starts now."""
        try:
            await self.dispatcher.accept(self.user.id, order_id)
        except OrderUnavailable:  # the time ran out and the order went back to the queue
            return await self._say("messages-executor-accept_failed", order_id)
        await self.renderer.apply(
            self.presenter.note(
                "messages-executor-accepted", order_id, await self.work.code(order_id)
            )
        )
        await self.effects.order_accepted(order_id)

    async def refuse(self, order_id: int) -> None:
        await self.helper.fsm.clear()
        try:
            result = await self.dispatcher.refuse(self.user.id, order_id)
        except OrderUnavailable:
            return await self._say("messages-executor-refuse_failed", order_id)
        await self._say("messages-executor-refused", order_id)
        await self.effects.order_refused(result)

    async def info_start(self, order_id: int) -> None:
        """«Need data»: the next text of the executor is the question to the buyer."""
        fsm = self.helper.fsm
        await fsm.clear()
        view = await self.work.get(self.user.id, order_id)
        if view is None or not view.can_ask_info:
            return await self._say("messages-executor-info_failed", order_id)
        await fsm.set_state(InfoForm.question)
        await fsm.update_data(order_id=order_id)
        await self.renderer.apply(
            self.presenter.info_ask(order_id, await self.work.code(order_id))
        )

    async def info_question(self, message: Message) -> None:
        data = await self.helper.fsm.get_data()
        order_id = data.get("order_id")
        if order_id is None:
            return
        try:
            ask = await self.info_requests.ask(self.user.id, order_id, message.text or "")
        except InvalidInput as e:
            if isinstance(e, ContactsBlocked):
                await self.effects.contacts_blocked(e)
                key = "messages-executor-info_blocked"
            else:
                key = "messages-executor-info_invalid"
            await self.renderer.apply(
                self.presenter.info_ask(
                    order_id, await self.work.code(order_id), error=key, current=True
                )
            )
            return
        except (Conflict, OrderUnavailable, DeadlineExpired):
            await self.helper.fsm.clear()
            return await self._say("messages-executor-info_failed", order_id)
        await self.helper.fsm.clear()
        await self.renderer.apply(
            self.presenter.note(
                "messages-executor-info_sent", order_id, await self.work.code(order_id)
            )
        )
        await self.effects.info_asked(ask)

    async def extension(self, cd: CDExt) -> None:
        if cd.action == "ask":
            await self.renderer.apply(
                self.presenter.extension_options(cd.id, await self.work.code(cd.id))
            )
            return
        try:
            ask = await self.extensions.request(self.user.id, cd.id, cd.value)
        except (Conflict, OrderUnavailable, DeadlineExpired, InvalidInput):
            await self._say("messages-executor-ext_failed", cd.id)
            return
        await self.effects.extension_asked(ask)
        await self.show(cd.id, 0)

    async def cancel_answer(self, cd: CDXCancel) -> None:
        """The executor answers the buyer's request to cancel the order."""
        try:
            answer = await self.cancel_requests.answer(self.user.id, cd.id, cd.rid, bool(cd.ok))
        except (Conflict, OrderUnavailable):  # the timer agreed first, handed in, a dispute
            update = self.helper.update
            if isinstance(update, CallbackQuery):
                await update.answer(self.presenter.i18n.get("messages-executor-cancel_stale"))
            return await self.show(cd.id, 0)
        await self.effects.cancel_answered(answer)
        if answer.agreed:
            return await self._say("messages-executor-cancel_agreed", cd.id)
        await self._say("messages-executor-cancel_declined", cd.id)
        await self.show(cd.id, 0)

    async def _say(self, key: str, order_id: int) -> None:
        await self.renderer.apply(self.presenter.text(key, id=await self.work.code(order_id)))

    async def list(self, page: int) -> Any:
        orders, total, page = await self.work.my_orders(self.user.id, page)
        return await self.renderer.apply(self.presenter.orders(orders, total, page))

    async def show(self, order_id: int, page: int) -> None:
        await self.helper.fsm.clear()
        view = await self.work.get(self.user.id, order_id)
        if view is None:
            return await self._say("messages-executor-order_missing", order_id)
        await self.renderer.apply(self.presenter.order(view, page))

    # result submission, one question per field of the product result schema

    async def result_action(self, cd: CDXResult) -> None:
        if cd.action == "start":
            return await self._start(cd.id)
        if cd.action == "cancel":
            return await self.show(cd.id, 0)
        if cd.action == "done":
            return await self._done()
        ctx = await self._load()
        if ctx is None:
            return
        form, data = ctx
        field = form.fields[data["idx"]]
        value = ""
        if cd.action == "choice":
            options = field.options or []
            if not 0 <= cd.value < len(options):
                return
            value = options[cd.value]
        elif field.required:  # skip
            return
        await self._accept(form, data, value, current=False)

    async def _done(self) -> None:
        """The "Done" button of a field with several files."""
        async with chat_lock(self.helper.get_chat_id()):
            ctx = await self._load()
            if ctx is None:
                return
            form, data = ctx
            if data["idx"] >= len(form.fields) or not data.get("files"):
                return
            value = await finish_files(self.helper.fsm, data)
            await self._accept(form, data, value, current=False)

    async def _start(self, order_id: int) -> None:
        fsm = self.helper.fsm
        await fsm.clear()
        try:
            form = await self.work.result_form(self.user.id, order_id)
        except OrderUnavailable:
            return await self._say("messages-executor-refuse_failed", order_id)
        await fsm.update_data(
            order_id=order_id,
            idx=0,
            answers={},
            files=[],
            group=None,
            group_open=None,
            message_id=self.helper.find_message_id(),
        )
        await self._step(form, order_id, current=False)

    async def _load(self) -> tuple[FormSchema, dict[str, Any]] | None:
        fsm = self.helper.fsm
        data = await fsm.get_data()
        if "order_id" not in data:
            return None
        try:
            return await self.work.result_form(self.user.id, data["order_id"]), data
        except OrderUnavailable:
            await fsm.clear()
            await self._say("messages-executor-refuse_failed", data["order_id"])
            return None

    async def _step(
        self,
        form: FormSchema,
        order_id: int,
        *,
        current: bool,
        reason: str | None = None,
    ) -> None:
        fsm = self.helper.fsm
        data = await fsm.get_data()
        idx = data["idx"]
        if idx >= len(form.fields):
            return await self._finish(order_id)
        await fsm.set_state(ResultForm.answer)
        view = self.presenter.result_ask(
            order_id,
            await self.work.code(order_id),
            form.fields[idx],
            idx,
            len(form.fields),
            current=current,
            reason=reason,
            files=len(data.get("files", [])),
        )
        result = await self.renderer.apply(view)
        if isinstance(result, Message):
            await fsm.update_data(message_id=result.message_id)

    async def _accept(
        self, form: FormSchema, data: dict[str, Any], value: str, *, current: bool
    ) -> None:
        field = form.fields[data["idx"]]
        answers = {**data["answers"], field.key: value}
        await self.helper.fsm.update_data(
            answers=answers, idx=data["idx"] + 1, files=[], group_open=None
        )
        await self._step(form, data["order_id"], current=current)

    async def answer_message(self, message: Message) -> None:
        async with chat_lock(self.helper.get_chat_id()):
            await self._answer_message(message)

    async def _answer_message(self, message: Message) -> None:
        ctx = await self._load()
        if ctx is None:
            return
        form, data = ctx
        field = form.fields[data["idx"]]
        reason: str | None = None
        value = ""
        if is_straggler(message, data):  # the rest of an album that already answered
            return
        if field.type is FieldType.file:
            status, value = await take_file(self.helper.fsm, message, field, data)
            if status == "wrong":
                reason = self.purchase_presenter.reason("not_file")
            elif status == "more":
                return await self._step(form, data["order_id"], current=True)
        elif not message.text:
            reason = self.purchase_presenter.reason("not_text")
        else:
            try:
                value = field.validate_value(message.text)
            except ValueError as e:
                reason = self.purchase_presenter.reason(str(e))
        if reason is not None:
            return await self._step(form, data["order_id"], current=True, reason=reason)
        await self._accept(form, data, value, current=True)

    async def _finish(self, order_id: int) -> None:
        fsm = self.helper.fsm
        answers = (await fsm.get_data())["answers"]
        try:
            order = await self.work.submit(self.user.id, order_id, answers)
        except OrderUnavailable:
            await fsm.clear()
            return await self._say("messages-executor-refuse_failed", order_id)
        except DeadlineExpired:
            await fsm.clear()
            return await self._say("messages-executor-deadline_passed", order_id)
        except InvalidInput:
            await fsm.clear()
            return await self._say("messages-executor-result_invalid", order_id)
        await fsm.clear()
        view = self.presenter.note(
            "messages-executor-submitted", order_id, await self.work.code(order_id)
        )
        view.mode = RenderMode.ANSWER
        await self.renderer.apply(view)
        await self.effects.result_submitted(order)
