import logging
from dataclasses import dataclass
from typing import Final

from aiogram import Bot, html
from aiogram.exceptions import TelegramAPIError

from app.application.interactors.conversations import ConversationInteractor, Posted, Recipient
from app.domain.enums.support import ChatRole
from app.infrastructure.events import EventHub, message_view
from app.infrastructure.telegram.notifier import Notifier, Translate
from app.presentation.telegram.keyboards.chat import copy_keyboard

logger: Final = logging.getLogger(__name__)

TEXT_LIMIT: Final = 4096
CAPTION_LIMIT: Final = 1024
# stickers and round videos cannot carry a caption: the header goes in its own message
NO_CAPTION: Final = frozenset({"sticker", "video_note"})


@dataclass(frozen=True)
class Delivery:
    delivered: int
    failed: int


def _fit(raw: str, room: int) -> str:
    """HTML-escaped `raw`, cut so that the result is not longer than `room`."""
    size = len(raw)
    while size > 0:
        body = html.quote(raw[:size])
        if len(body) <= room:
            return body
        size = min(size - 1, size * room // len(body))
    return ""


@dataclass(frozen=True)
class Relay:
    """Copies of a stored message to the other side of a conversation, each with a header that
    shows only what that side may know (never the buyer's name to an executor).
    Call after the commit that stored the message; a failed send is logged and counted."""

    bot: Bot
    notifier: Notifier
    chat: ConversationInteractor
    hub: EventHub

    async def deliver(self, posted: Posted, source_message_id: int | None) -> Delivery:
        """`source_message_id`: the sender's own message (media is copied from it); None for a
        text sent from the Mini App. Open Mini App sockets get the message first."""
        await self._publish(posted)
        delivered = failed = 0
        for recipient in posted.recipients:
            try:
                sent = await self._send(posted, recipient, source_message_id)
            except TelegramAPIError:
                logger.info(
                    "could not relay message %s to %s", posted.message_id, recipient.user_id
                )
                failed += 1
                continue
            except Exception:
                logger.exception("relaying message %s failed", posted.message_id)
                failed += 1
                continue
            delivered += 1
            try:
                await self.chat.record_delivery(posted.message_id, recipient.user_id, sent)
            except Exception:
                logger.exception("recording delivery of message %s failed", posted.message_id)
        return Delivery(delivered, failed)

    async def _publish(self, posted: Posted) -> None:
        try:
            message = await self.chat.message(posted.message_id)
            if message is None:
                return
            users = [posted.sender_id, *(r.user_id for r in posted.recipients)]
            await self.hub.publish_each(
                users,
                lambda uid: {
                    "type": "message",
                    "conversation_id": posted.conversation_id,
                    "message": message_view(message, uid),
                },
            )
        except Exception:
            logger.exception("publishing message %s failed", posted.message_id)

    async def _send(
        self, posted: Posted, recipient: Recipient, source_message_id: int | None
    ) -> int:
        tr = await self.notifier.translator(recipient.user_id)
        header = self._header(tr, posted, recipient)
        staff = recipient.role in (ChatRole.manager, ChatRole.admin)
        markup = copy_keyboard(tr, posted.conversation_id, posted.ticket_id, staff=staff)
        if posted.media is None:
            body = _fit(posted.text or "", TEXT_LIMIT - len(header) - 2)
            message = await self.bot.send_message(
                recipient.user_id, f"{header}\n\n{body}", reply_markup=markup
            )
            return message.message_id
        if source_message_id is None:
            raise ValueError("media needs the source message")
        caption: str | None = None
        if posted.media.get("type") in NO_CAPTION:
            await self.bot.send_message(recipient.user_id, header)
        else:
            room = CAPTION_LIMIT - len(header) - 2
            caption = header + (f"\n\n{_fit(posted.text, room)}" if posted.text else "")
        copy = await self.bot.copy_message(
            recipient.user_id,
            from_chat_id=posted.sender_id,
            message_id=source_message_id,
            caption=caption,
            reply_markup=markup,
        )
        return copy.message_id

    @staticmethod
    def _header(tr: Translate, posted: Posted, recipient: Recipient) -> str:
        ref = (
            tr("messages-chat-ref_ticket", id=str(posted.ticket_id))
            if posted.ticket_id is not None
            else tr("messages-chat-ref_order", id=str(posted.order_id))
        )
        match posted.sender_role:
            case ChatRole.buyer if recipient.role is ChatRole.executor:
                return tr("messages-chat-from_buyer", ref=ref)
            case ChatRole.buyer:
                return tr("messages-chat-from_user", name=posted.buyer_name, ref=ref)
            case ChatRole.executor:
                return tr(
                    "messages-chat-from_executor",
                    alias=html.quote(posted.executor_alias or ""),
                    ref=ref,
                )
            case _:
                return tr("messages-chat-from_support", ref=ref)
