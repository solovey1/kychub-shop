import logging
from dataclasses import dataclass
from typing import Final

from app.application.errors.shop import OrderUnavailable, TicketUnavailable
from app.application.interactors.conversations import ConversationInteractor
from app.application.ports.storages.key_value import KvStorage
from app.application.ports.telegram.messages_helper import MessageHelper
from app.application.storage.keys.impl import ActiveConversationKey
from app.domain.enums.support import ChatRole
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.flows.common.relay import ACTIVE_TTL
from app.presentation.telegram.keyboards.chat import copy_keyboard
from app.presentation.telegram.presenters.common.support import SupportPresenter
from app.presentation.telegram.view.models import View
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

    async def action(self, cd: CDChat) -> None:
        match cd.action:
            case "support":
                await self.support(cd.id or None)
            case "order":
                await self.order_chat(cd.id)
            case "reply":
                await self.reply(cd.id)
            case "take":
                await self.take(cd.id)
            case "history":
                await self.history(cd.id)
            case "close":
                await self.close(cd.id)

    async def _activate(self, conversation_id: int) -> None:
        await self.kv.set(ActiveConversationKey(user_id=self.user.id), conversation_id, ACTIVE_TTL)

    async def _say(self, key: str, **kwargs: str) -> None:
        await self.renderer.apply(self.presenter.note(key, **kwargs))

    async def support(self, order_id: int | None) -> None:
        await self.helper.fsm.clear()
        try:
            ticket, conversation, created = await self.chat.open_ticket(self.user.id, order_id)
        except OrderUnavailable:
            return await self._say("messages-chat-order_missing")
        await self._activate(conversation.id)
        key = "messages-chat-support_new" if created else "messages-chat-support_again"
        await self._say(key, id=str(ticket.id))

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
        ticket, name = card
        conversation = await self.chat.ticket_conversation(ticket_id)
        await self._activate(conversation.id)
        tr = self.presenter.i18n.get
        await self.renderer.apply(
            View(
                text=tr("messages-ticket-taken", id=str(ticket_id), name=name),
                reply_markup=copy_keyboard(tr, conversation.id, ticket_id, staff=True),
            )
        )
        await self.renderer.apply(self.presenter.history(await self.chat.history(conversation.id)))
        await self.effects.ticket_taken(ticket, self.user.id, self.user.name)

    async def history(self, conversation_id: int) -> None:
        conversation = await self.chat.get_conversation(conversation_id)
        role = await self.chat.can_post(self.user.id, conversation) if conversation else None
        if role not in (ChatRole.manager, ChatRole.admin):
            return await self._say("messages-chat-forbidden")
        await self.renderer.apply(self.presenter.history(await self.chat.history(conversation_id)))

    async def close(self, ticket_id: int) -> None:
        try:
            ticket = await self.chat.close_ticket(self.user.id, ticket_id)
        except TicketUnavailable:
            return await self._say("messages-ticket-unavailable", id=str(ticket_id))
        await self._say("messages-ticket-closed", id=str(ticket_id))
        await self.effects.ticket_closed(ticket, self.user.id)
