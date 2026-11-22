from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Final
from urllib.parse import parse_qs, urlparse

from aiogram.types import InlineKeyboardMarkup, Message

from app.application.errors.shop import ChatForbidden
from app.application.interactors.conversations import ConversationInteractor
from app.application.models.config import AppConfig
from app.application.ports.storages.key_value import KvStorage
from app.application.storage.keys.impl import ActiveConversationKey, ChatHintKey, TicketTipKey
from app.domain.enums.support import ChatRole, ConversationKind
from app.domain.support import Conversation
from app.domain.user import User
from app.infrastructure.telegram.effects import Effects
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.keyboards.chat import ticket_keyboard
from app.presentation.telegram.presenters.common.support import SupportPresenter
from app.presentation.telegram.view.renderer import Renderer

ACTIVE_TTL: Final = timedelta(minutes=30)
HINT_TTL: Final = timedelta(hours=1)
TIP_TTL: Final = timedelta(minutes=10)

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
    effects: Effects
    kv: KvStorage
    presenter: SupportPresenter
    renderer: Renderer
    config: AppConfig

    async def route(self, message: Message) -> None:
        conversation = await self._target(message)
        if conversation is not None:
            await self.send(conversation, message)

    async def send(self, conversation: Conversation, message: Message) -> None:
        """Puts the user's message into the conversation and delivers the copies."""
        text, media, supported = extract(message)
        if not supported:
            return await self._say("messages-chat-unsupported")
        try:
            posted = await self.chat.post(conversation.id, self.user.id, text, media)
        except ChatForbidden:
            return await self._say("messages-chat-forbidden")
        await self.kv.set(ActiveConversationKey(user_id=self.user.id), conversation.id, ACTIVE_TTL)
        delivery = await self.effects.message_posted(posted, message.message_id)
        if posted.ticket_id is not None and posted.sender_role is ChatRole.buyer and self._app_on:
            await self._tip(conversation, posted.ticket_id)
        elif not posted.recipients:
            await self._say("messages-chat-saved")
        elif delivery.delivered == 0:
            await self._say("messages-chat-undelivered")

    @property
    def _app_on(self) -> bool:
        return self.config.server.url.startswith("https://")

    async def _tip(self, conversation: Conversation, ticket_id: int) -> None:
        """The buyer's message is stored and shown to support: say so, at most every 10 minutes."""
        tip = TicketTipKey(user_id=self.user.id)
        if await self.kv.exists(tip):
            return
        await self.kv.set(tip, 1, TIP_TTL)
        await self._say("messages-chat-tip", self._open(conversation, ticket_id, staff=False))

    def _open(
        self, conversation: Conversation, ticket_id: int, *, staff: bool
    ) -> InlineKeyboardMarkup | None:
        return ticket_keyboard(
            self.presenter.i18n.get,
            self.config.server.url,
            conversation.id,
            ticket_id,
            staff=staff,
        )

    async def _by_notice(self, notice: Message) -> tuple[bool, Conversation | None]:
        """A reply to a ticket notice (its button opens `?to=.../<conversation id>`):
        (False, _) for anything else; else the buyer's text goes to that ticket and staff are
        sent to the app (None, the user has been told)."""
        markup = notice.reply_markup
        for b in (b for row in (markup.inline_keyboard if markup else ()) for b in row):
            to = parse_qs(urlparse(b.web_app.url).query).get("to") if b.web_app else None
            if not to:
                continue
            found = await self.chat.get_conversation(int(to[0].rsplit("/", 1)[1]))
            if found is None or found.ticket_id is None:
                break
            role = await self.chat.can_post(self.user.id, found)
            if role is ChatRole.buyer:
                return True, found
            if role is None:
                await self._say("messages-chat-forbidden")
            else:
                await self._say(
                    "messages-chat-use_app", self._open(found, found.ticket_id, staff=True)
                )
            return True, None
        return False, None

    async def _target(self, message: Message) -> Conversation | None:
        """None: the message is not for any conversation and the user has been told."""
        uid = self.user.id
        if message.reply_to_message is not None:
            found = await self.chat.find_by_reply(
                message.chat.id, message.reply_to_message.message_id
            )
            if found is not None:
                if await self.chat.can_post(uid, found) is None:
                    await self._say(self._closed_key(found))
                    return None
                return found
            handled, notice = await self._by_notice(message.reply_to_message)
            if handled:
                return notice
        current = await self.kv.get(ActiveConversationKey(user_id=uid))
        if current is not None:
            conversation = await self.chat.get_conversation(current)
            if conversation is not None:
                if await self.chat.can_post(uid, conversation):
                    return conversation
                if conversation.kind is ConversationKind.order:  # tell once, then forget it
                    await self.kv.delete(ActiveConversationKey(user_id=uid))
                    await self._say("messages-chat-order_closed")
                    return None
        hint = ChatHintKey(user_id=uid)
        if not await self.kv.exists(hint):
            await self.kv.set(hint, 1, HINT_TTL)
            await self._say("messages-chat-hint")
        return None

    @staticmethod
    def _closed_key(conversation: Conversation) -> str:
        if conversation.kind is ConversationKind.order:
            return "messages-chat-order_closed"
        return "messages-chat-forbidden"

    async def _say(self, key: str, markup: InlineKeyboardMarkup | None = None) -> None:
        await self.renderer.apply(self.presenter.note(key, markup))
