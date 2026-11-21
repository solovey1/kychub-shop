import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Final

from aiogram.types import InlineKeyboardMarkup

from app.application.interactors.conversations import Posted
from app.application.ports.storages.key_value import KvStorage
from app.application.storage.keys.impl import TicketOfferKey
from app.infrastructure.telegram.notifier import Notifier, Translate
from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.keyboards.common import button, markup
from app.presentation.telegram.presenters.common.support import preview

logger: Final = logging.getLogger(__name__)

OFFER_TTL: Final = timedelta(days=7)
PREVIEW_CHARS: Final = 500


def _take_keyboard(ticket_id: int) -> Callable[[Translate], InlineKeyboardMarkup]:
    return lambda tr: markup(
        [[button(tr("buttons-take"), CDChat(action="take", id=ticket_id), style="success")]]
    )


@dataclass(frozen=True)
class TicketOffers:
    """Telegram side of a new ticket: the notice with «Take» to every manager and admin, and
    its replacement once the ticket is taken or closed. Call after the commit."""

    notifier: Notifier
    kv: KvStorage

    async def announce(self, posted: Posted) -> None:
        """Only for an open ticket that has not been announced yet. A ticket nobody could be
        told about is announced again with the next message."""
        if not posted.needs_offer or posted.ticket_id is None:
            return
        try:
            await self._announce(posted, posted.ticket_id)
        except Exception:
            logger.exception("announcing ticket %s failed", posted.ticket_id)

    async def _announce(self, posted: Posted, ticket_id: int) -> None:
        key = TicketOfferKey(ticket_id=ticket_id)
        if await self.kv.exists(key):
            return

        def text(tr: Translate, _: str) -> str:
            order = (
                "\n" + tr("messages-ticket-order", id=str(posted.order_id))
                if posted.order_id is not None
                else ""
            )
            return tr(
                "messages-ticket-new",
                id=str(ticket_id),
                name=posted.buyer_name,
                order=order,
                text=preview(tr, posted.text, posted.media, PREVIEW_CHARS),
            )

        sent: list[list[int]] = []
        for staff_id in await self.notifier.executors.staff_ids():
            message = await self.notifier.send(staff_id, text, _take_keyboard(ticket_id))
            if message is not None:
                sent.append([staff_id, message.message_id])
        if sent:
            await self.kv.set(key, sent, ex=OFFER_TTL)

    async def close(
        self, ticket_id: int, key: str, *, except_chat: int | None = None, name: str = ""
    ) -> None:
        """Replace every stored notice with a short note and drop the buttons."""
        offer_key = TicketOfferKey(ticket_id=ticket_id)
        for chat_id, message_id in await self.kv.get(offer_key) or []:
            if chat_id != except_chat:
                await self.notifier.edit(chat_id, message_id, key, id=str(ticket_id), name=name)
        await self.kv.delete(offer_key)
