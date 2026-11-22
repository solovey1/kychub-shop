import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Callable, Final

from aiogram.types import InlineKeyboardMarkup

from app.application.cards import OrderCard, render_card
from app.application.interactors.cards import CardBuilder
from app.application.interactors.dispatch import DispatchResult
from app.application.models.form_schema import split_files
from app.application.ports.repositories.orders import OrdersGateway
from app.application.ports.storages.key_value import KvStorage
from app.application.storage.keys.impl import OrderOfferKey
from app.infrastructure.events import EventHub
from app.infrastructure.telegram.notifier import Notifier, Translate
from app.presentation.telegram.callbacks.executor import CDOrderAct, CDXOrder
from app.presentation.telegram.callbacks.orders import CDCancel, CDOrder
from app.presentation.telegram.keyboards.common import button, markup

logger: Final = logging.getLogger(__name__)

OFFER_TTL: Final = timedelta(days=1)


def _take_keyboard(order_id: int) -> Callable[[Translate], InlineKeyboardMarkup]:
    def build(tr: Translate) -> InlineKeyboardMarkup:
        return markup(
            [[button(tr("buttons-take"), CDOrderAct(action="take", id=order_id), style="success")]]
        )

    return build


def _text(key: str, card: OrderCard, **kwargs: object) -> Callable[[Translate, str], str]:
    return lambda tr, locale: tr(key, card=render_card(tr, locale, card), **kwargs)


def _refuse_keyboard(
    order_id: int, accept: bool = False
) -> Callable[[Translate], InlineKeyboardMarkup]:
    def build(tr: Translate) -> InlineKeyboardMarkup:
        return markup(
            [
                [
                    button(
                        tr("buttons-accept"),
                        CDOrderAct(action="accept", id=order_id),
                        style="success",
                    )
                ]
                if accept
                else [],
                [
                    button(
                        tr("buttons-refuse"),
                        CDOrderAct(action="refuse", id=order_id),
                        style="danger",
                    )
                ],
                [button(tr("buttons-open_order"), CDXOrder(id=order_id))],
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
    hub: EventHub

    async def announce(self, result: DispatchResult) -> None:
        try:
            await self._announce(result)
        except Exception:
            logger.exception("announcing dispatch of order %s failed", result.order_id)
        await self._publish(result)

    async def send_files(self, order_id: int, executor_id: int) -> None:
        """The files the buyer attached to the order (the fields he may see), to the executor."""
        try:
            order = await self.orders.get(order_id)
            if order is None:
                return
            card = await self.cards.build(order, executor_id)
            for f in card.fields:
                if f.is_file:
                    for file_id in split_files(f.value):
                        await self.notifier.send_media(executor_id, file_id)
        except Exception:
            logger.exception("sending the files of order %s failed", order_id)

    async def _publish(self, result: DispatchResult) -> None:
        """Open Mini Apps: the executors who may take the order, the people whose order moved."""
        try:
            if result.kind == "skipped":
                return
            order = await self.orders.get(result.order_id)
            if order is None:
                return
            users = {order.user_id}
            if result.released_executor_id is not None:
                users.add(result.released_executor_id)
            if result.kind == "assigned":
                users.update(result.executor_ids)
            await self.hub.publish(
                users,
                {"type": "order", "order_id": order.id, "status": order.status.value},
            )
            if result.kind == "offer":
                await self.hub.publish(result.executor_ids, {"type": "queue"})
        except Exception:
            logger.exception("publishing dispatch of order %s failed", result.order_id)

    async def _tell_released(self, result: DispatchResult) -> None:
        """The executor who just lost the order: it went overdue, or he did not accept it."""
        key = {"overdue": "messages-executor-overdue", "ignored": "messages-executor-ignored"}.get(
            result.release_reason or ""
        )
        if result.released_executor_id is not None and key is not None:
            await self.notifier.send(
                result.released_executor_id,
                key,
                id=await self.notifier.order_code(result.order_id),
            )

    async def _announce(self, result: DispatchResult) -> None:
        order_id = result.order_id
        await self._tell_released(result)
        if result.kind in ("skipped", "none"):
            if result.kind == "none" and result.first_no_executor:
                await self.notifier.staff(
                    "messages-executor-no_executor", id=await self.notifier.order_code(order_id)
                )
                await self._tell_buyer_waiting(order_id)
            return
        order = await self.orders.get(order_id)
        if order is None:
            return
        if result.kind == "assigned":
            executor_id = result.executor_ids[0]
            card = await self.cards.build(order, executor_id)
            if order.accept_until is not None:  # auto-assigned: he has to confirm
                await self.notifier.send(
                    executor_id,
                    _text("messages-executor-assigned_accept", card, time=order.accept_until),
                    _refuse_keyboard(order_id, accept=True),
                )
            else:
                await self.notifier.send(
                    executor_id,
                    _text("messages-executor-assigned", card),
                    _refuse_keyboard(order_id),
                )
            await self.send_files(order_id, executor_id)
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

    async def _tell_buyer_waiting(self, order_id: int) -> None:
        order = await self.orders.get(order_id)
        if order is None:
            return
        await self.notifier.send(
            order.user_id,
            "messages-order-waiting",
            lambda tr: markup(
                [
                    [button(tr("buttons-open_order"), CDOrder(id=order_id), style="primary")],
                    [button(tr("buttons-cancel_refund"), CDCancel(id=order_id), style="danger")],
                ]
            ),
            id=order.code,
        )

    async def close(self, order_id: int, key: str, *, except_chat: int | None = None) -> None:
        """Replace every stored proposal of the order with a short note and drop the buttons."""
        offer_key = OrderOfferKey(order_id=order_id)
        code = await self.notifier.order_code(order_id)
        for chat_id, message_id in await self.kv.get(offer_key) or []:
            if chat_id != except_chat:
                await self.notifier.edit(chat_id, message_id, key, id=code)
        await self.kv.delete(offer_key)
