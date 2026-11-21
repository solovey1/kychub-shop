import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Final

from aiogram.types import InlineKeyboardMarkup

from app.application.cards import OrderCard, render_card
from app.application.interactors.cards import CardBuilder
from app.application.interactors.dispatch import DispatchResult
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.storages.key_value import KvStorage
from app.application.storage.keys.impl import OrderOfferKey
from app.infrastructure.telegram.notifier import Notifier, Translate
from app.presentation.telegram.callbacks.executor import CDOrderAct
from app.presentation.telegram.keyboards.common import button, markup

logger: Final = logging.getLogger(__name__)

OFFER_TTL: Final = timedelta(days=1)


def _take_keyboard(order_id: int) -> Callable[[Translate], InlineKeyboardMarkup]:
    def build(tr: Translate) -> InlineKeyboardMarkup:
        return markup(
            [[button(tr("buttons-take"), CDOrderAct(action="take", id=order_id), style="success")]]
        )

    return build


def _text(key: str, card: OrderCard) -> Callable[[Translate, str], str]:
    return lambda tr, locale: tr(key, card=render_card(tr, locale, card))


def _refuse_keyboard(order_id: int) -> Callable[[Translate], InlineKeyboardMarkup]:
    def build(tr: Translate) -> InlineKeyboardMarkup:
        return markup(
            [
                [
                    button(
                        tr("buttons-refuse"),
                        CDOrderAct(action="refuse", id=order_id),
                        style="danger",
                    )
                ]
            ]
        )

    return build


@dataclass(frozen=True)
class OfferService:
    """Telegram side of a dispatch: proposals to executors, assignment notices, staff alerts.
    Call after the transaction that produced the result has been committed."""

    notifier: Notifier
    kv: KvStorage
    orders: OrdersGateway
    cards: CardBuilder

    async def announce(self, result: DispatchResult) -> None:
        try:
            await self._announce(result)
        except Exception:
            logger.exception("announcing dispatch of order %s failed", result.order_id)

    async def _announce(self, result: DispatchResult) -> None:
        order_id = result.order_id
        if result.released_executor_id is not None and result.release_reason == "overdue":
            await self.notifier.send(
                result.released_executor_id, "messages-executor-overdue", id=str(order_id)
            )
        if result.kind in ("skipped", "none"):
            if result.kind == "none" and result.first_no_executor:
                await self.notifier.staff("messages-executor-no_executor", id=str(order_id))
            return
        order = await self.orders.get(order_id)
        if order is None:
            return
        if result.kind == "assigned":
            executor_id = result.executor_ids[0]
            card = await self.cards.build(order, executor_id)
            await self.notifier.send(
                executor_id, _text("messages-executor-assigned", card), _refuse_keyboard(order_id)
            )
            return
        key = OrderOfferKey(order_id=order_id)
        sent: list[list[int]] = await self.kv.get(key) or []
        already = {chat_id for chat_id, _ in sent}
        for executor_id in result.executor_ids:
            if executor_id in already:
                continue
            card = await self.cards.build(order, executor_id)
            message = await self.notifier.send(
                executor_id, _text("messages-executor-offer", card), _take_keyboard(order_id)
            )
            if message is not None:
                sent.append([executor_id, message.message_id])
        await self.kv.set(key, sent, ex=OFFER_TTL)

    async def close(self, order_id: int, key: str, *, except_chat: int | None = None) -> None:
        """Replace every stored proposal of the order with a short note and drop the buttons."""
        offer_key = OrderOfferKey(order_id=order_id)
        for chat_id, message_id in await self.kv.get(offer_key) or []:
            if chat_id != except_chat:
                await self.notifier.edit(chat_id, message_id, key, id=str(order_id))
        await self.kv.delete(offer_key)
