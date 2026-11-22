import logging
from dataclasses import dataclass
from typing import Final

from aiogram.types import Message

from app.application.errors.shop import OrderUnavailable, TicketUnavailable
from app.application.interactors.conversations import ConversationInteractor
from app.application.models.config import AppConfig
from app.application.ports.storages.key_value import KvStorage
from app.application.ports.telegram.messages_helper import MessageHelper
from app.application.storage.keys.impl import ActiveConversationKey, TicketTipKey
from app.domain.enums.support import ChatRole
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.flows.common.relay import ACTIVE_TTL, RelayFlow, extract
from app.presentation.telegram.keyboards.chat import (
    support_keyboard,
    ticket_keyboard,
    write_keyboard,
)
from app.presentation.telegram.presenters.common.support import SupportPresenter
from app.presentation.telegram.states.support import SupportForm
from app.presentation.telegram.view.renderer import Renderer

logger: Final = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChatFlow(BaseFlow):
    """Buttons of support tickets and order chats."""

    user: User
    chat: ConversationInteractor
    kv: KvStorage
    effects: Effects
    presenter: SupportPresenter
    renderer: Renderer
    helper: MessageHelper
    config: AppConfig
    relay: RelayFlow

    async def action(self, cd: CDChat) -> None:
        match cd.action:
            case "support":
                await self.support(cd.id or None)
            case "write":
                await self.write(cd.id)
            case "order":
                await self.order_chat(cd.id)
            case "reply":
                await self.reply(cd.id)
            case "take":
                await self.take(cd.id)
            case "close":
                await self.close(cd.id)

    async def _activate(self, conversation_id: int) -> None:
        await self.kv.set(ActiveConversationKey(user_id=self.user.id), conversation_id, ACTIVE_TTL)

    async def _say(self, key: str, **kwargs: str) -> None:
        await self.renderer.apply(self.presenter.note(key, **kwargs))

    async def support(self, order_id: int | None) -> None:
        """The support screen. Nothing is created here: the ticket comes with the first message."""
        await self.helper.fsm.clear()
        try:
            current = await self.chat.current_ticket(self.user.id, order_id)
        except OrderUnavailable:
            return await self._say("messages-chat-order_missing")
        tr = self.presenter.i18n.get
        order = tr("messages-support-order", id=str(order_id)) + "\n" if order_id else ""
        if current is None:
            view = self.presenter.screen(
                "messages-support", support_keyboard(tr, order_id or 0), order=order
            )
        else:
            ticket, conversation = current
            await self._activate(conversation.id)  # plain messages go to this ticket
            markup = ticket_keyboard(
                tr, self.config.server.url, conversation.id, ticket.id, staff=False, close=True
            )
            view = self.presenter.screen(
                "messages-support-open", markup, order=order, id=str(ticket.id)
            )
        await self.renderer.apply(view)

    async def write(self, order_id: int) -> None:
        fsm = self.helper.fsm
        await fsm.clear()
        await fsm.set_state(SupportForm.message)
        await fsm.update_data(order_id=order_id, prompt_id=self.helper.find_message_id())
        tr = self.presenter.i18n.get
        await self.renderer.apply(
            self.presenter.screen("messages-support-write", write_keyboard(tr))
        )

    async def first_message(self, message: Message) -> None:
        """The first message makes the ticket (the only way to get one) and goes into it."""
        if not extract(message)[2]:
            return await self._say("messages-chat-unsupported")
        data = await self.helper.fsm.get_data()
        try:
            _, conversation, _ = await self.chat.open_ticket(
                self.user.id, data.get("order_id") or None
            )
        except OrderUnavailable:
            await self.helper.fsm.clear()
            return await self._say("messages-chat-order_missing")
        await self.helper.fsm.clear()
        if prompt_id := data.get("prompt_id"):
            await self.helper.delete(message_id=prompt_id)
        await self.kv.delete(TicketTipKey(user_id=self.user.id))  # the "sent" note shows now
        await self._activate(conversation.id)
        await self.relay.send(conversation, message)

    async def order_chat(self, order_id: int) -> None:
        await self.helper.fsm.clear()
        try:
            conversation = await self.chat.order_conversation(self.user.id, order_id)
        except OrderUnavailable:
            return await self._say("messages-chat-order_missing")
        role = await self.chat.can_post(self.user.id, conversation)
        participants = await self.chat.participants(conversation)
        if role is None or participants is None:
            return await self._say("messages-chat-forbidden")
        if role is ChatRole.buyer and participants.counterpart_id is None:
            return await self._say("messages-chat-no_executor")
        await self._activate(conversation.id)
        key = (
            "messages-chat-order_executor"
            if role is ChatRole.executor
            else "messages-chat-order_buyer"
        )
        await self._say(key, id=str(order_id))

    async def reply(self, conversation_id: int) -> None:
        await self.helper.fsm.clear()
        conversation = await self.chat.get_conversation(conversation_id)
        if conversation is None or await self.chat.can_post(self.user.id, conversation) is None:
            return await self._say("messages-chat-forbidden")
        await self._activate(conversation.id)
        await self._say("messages-chat-reply_open")

    async def take(self, ticket_id: int) -> None:
        if not await self.chat.take_ticket(self.user.id, ticket_id):
            return await self._say("messages-ticket-take_failed", id=str(ticket_id))
        card = await self.chat.ticket_card(ticket_id)
        assert card is not None
        conversation = await self.chat.ticket_conversation(ticket_id)
        await self.effects.ticket_taken(card[0], conversation.id, self.user.id, self.user.name)

    async def close(self, ticket_id: int) -> None:
        try:
            ticket = await self.chat.close_ticket(self.user.id, ticket_id)
        except TicketUnavailable:
            return await self._say("messages-ticket-unavailable", id=str(ticket_id))
        await self._say("messages-ticket-closed", id=str(ticket_id))
        await self.effects.ticket_closed(ticket, self.user.id)
