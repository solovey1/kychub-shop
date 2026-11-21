from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Final

from aiogram.types import Message

from app.application.errors.shop import ChatForbidden
from app.application.interactors.conversations import ConversationInteractor
from app.application.ports.storages.key_value import KvStorage
from app.application.storage.keys.impl import ActiveConversationKey, ChatHintKey
from app.domain.support import Conversation
from app.domain.user import User
from app.infrastructure.telegram.relay import Relay
from app.infrastructure.telegram.ticket_offers import TicketOffers
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.common.support import SupportPresenter
from app.presentation.telegram.view.renderer import Renderer

ACTIVE_TTL: Final = timedelta(minutes=30)
HINT_TTL: Final = timedelta(hours=1)

# Message attribute -> stored media type; the file id of a photo is its largest size
_MEDIA: Final = (
    "photo",
    "document",
    "video",
    "voice",
    "audio",
    "animation",
    "sticker",
    "video_note",
)


def extract(message: Message) -> tuple[str | None, dict[str, Any] | None, bool]:
    """(text or caption, {"type", "file_id"}, supported)."""
    if message.text:
        return message.text, None, True
    for kind in _MEDIA:
        item = getattr(message, kind)
        if item:
            file = item[-1] if kind == "photo" else item
            return message.caption, {"type": kind, "file_id": file.file_id}, True
    return None, None, False


@dataclass(frozen=True)
class RelayFlow(BaseFlow):
    """Where a free-form private message goes (spec 15): a reply to a copy, else the current
    conversation, else nowhere. Only used while the user is in no FSM state."""

    user: User
    chat: ConversationInteractor
    relay: Relay
    offers: TicketOffers
    kv: KvStorage
    presenter: SupportPresenter
    renderer: Renderer

    async def route(self, message: Message) -> None:
        conversation = await self._target(message)
        if conversation is None:
            return
        text, media, supported = extract(message)
        if not supported:
            return await self._say("messages-chat-unsupported")
        try:
            posted = await self.chat.post(conversation.id, self.user.id, text, media)
        except ChatForbidden:
            return await self._say("messages-chat-forbidden")
        await self.kv.set(ActiveConversationKey(user_id=self.user.id), conversation.id, ACTIVE_TTL)
        delivery = await self.relay.deliver(posted, message.message_id)
        await self.offers.announce(posted)
        if not posted.recipients:
            await self._say("messages-chat-saved")
        elif delivery.delivered == 0:
            await self._say("messages-chat-undelivered")

    async def _target(self, message: Message) -> Conversation | None:
        """None: the message is not for any conversation and the user has been told."""
        uid = self.user.id
        if message.reply_to_message is not None:
            found = await self.chat.find_by_reply(
                message.chat.id, message.reply_to_message.message_id
            )
            if found is not None:
                if await self.chat.can_post(uid, found) is None:
                    await self._say("messages-chat-forbidden")
                    return None
                return found
        current = await self.kv.get(ActiveConversationKey(user_id=uid))
        if current is not None:
            conversation = await self.chat.get_conversation(current)
            if conversation is not None and await self.chat.can_post(uid, conversation):
                return conversation
        hint = ChatHintKey(user_id=uid)
        if not await self.kv.exists(hint):
            await self.kv.set(hint, 1, HINT_TTL)
            await self._say("messages-chat-hint")
        return None

    async def _say(self, key: str) -> None:
        await self.renderer.apply(self.presenter.note(key))
