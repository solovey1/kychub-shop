from dataclasses import dataclass
from typing import Callable

from aiogram import html
from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup

from app.application.i18n_text import fmt_usd
from app.application.interactors.payouts import Refunded
from app.domain.order import Order
from app.infrastructure.telegram.notifier import Notifier, Translate
from app.presentation.telegram.callbacks.executor import CDReview, CDXOrder
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.keyboards.common import button, markup
from app.presentation.telegram.keyboards.feedback import rate_keyboard
from app.presentation.telegram.presenters.common.purchase import COPY_LIMIT, FILE_LIMIT


def _open_review(order_id: int) -> Callable[[Translate], InlineKeyboardMarkup]:
    return lambda tr: markup(
        [[button(tr("buttons-open"), CDReview(action="open", id=order_id), style="primary")]]
    )


def _open_order(order_id: int) -> Callable[[Translate], InlineKeyboardMarkup]:
    return lambda tr: markup([[button(tr("buttons-open"), CDXOrder(id=order_id))]])


def _result_markup(text: str) -> Callable[[Translate], InlineKeyboardMarkup]:
    def build(tr: Translate) -> InlineKeyboardMarkup:
        rows: list[list[InlineKeyboardButton]] = []
        if text and len(text) <= COPY_LIMIT:
            rows.append(
                [
                    InlineKeyboardButton(
                        text=tr("buttons-copy"),
                        copy_text=CopyTextButton(text=text),
                        style="primary",
                    )
                ]
            )
        rows.append([button(tr("buttons-menu"), CDMenu())])
        return markup(rows)

    return build


@dataclass(frozen=True)
class OrderNotices:
    """Telegram messages about an order changing hands. Always call after the commit."""

    notifier: Notifier

    async def ready_for_review(self, order: Order) -> None:
        await self.notifier.staff(
            "messages-review-ready", _open_review(order.id), id=str(order.id)
        )

    async def deliver(self, order: Order) -> None:
        """The result, to the buyer: code block with a copy button, or a file when it is long."""
        result = order.result or {}
        text = str(result.get("text", ""))
        user_id = order.user_id
        oid = str(order.id)
        if len(text) > FILE_LIMIT:
            await self.notifier.send(
                user_id,
                lambda tr, _: (
                    tr("messages-purchase-done", id=oid)
                    + "\n\n"
                    + tr("messages-purchase-done_file")
                ),
                _result_markup(""),
            )
            await self.notifier.send_file(user_id, f"order-{order.id}.txt", text.encode("utf-8"))
        else:
            body = f"\n\n<code>{html.quote(text)}</code>" if text else ""
            await self.notifier.send(
                user_id,
                lambda tr, _: tr("messages-purchase-done", id=oid) + body,
                _result_markup(text),
            )
        await self.files(user_id, list(result.get("files", [])))

    async def files(self, user_id: int, file_ids: list[str]) -> None:
        for file_id in file_ids:
            await self.notifier.send_media(user_id, file_id)

    async def confirmed(self, order: Order) -> None:
        if order.executor_id is not None:
            await self.notifier.send(
                order.executor_id, "messages-executor-confirmed", id=str(order.id)
            )

    async def sent_back(self, order: Order, comment: str) -> None:
        if order.executor_id is not None:
            await self.notifier.send(
                order.executor_id,
                "messages-executor-sent_back",
                _open_order(order.id),
                id=str(order.id),
                comment=html.quote(comment),
            )

    async def refunded(self, refund: Refunded) -> None:
        await self.notifier.send(
            refund.buyer_id,
            "messages-order-refunded",
            id=str(refund.order_id),
            amount=fmt_usd(refund.amount),
        )
        if refund.executor_id is not None:
            await self.notifier.send(
                refund.executor_id, "messages-executor-order_closed", id=str(refund.order_id)
            )

    async def review_request(self, order: Order) -> None:
        order_id = order.id
        await self.notifier.send(
            order.user_id,
            "messages-feedback-ask",
            lambda tr: rate_keyboard(tr, order_id),
            id=str(order_id),
        )
