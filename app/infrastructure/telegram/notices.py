from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from aiogram import html
from aiogram.types import CopyTextButton, InlineKeyboardButton, InlineKeyboardMarkup

from app.application.cards import fmt_duration
from app.application.i18n_text import fmt_usd
from app.application.interactors.cancel_request import AGREE_AFTER, CancelAnswer, CancelAsk
from app.application.interactors.deadlines import (
    ExtensionAnswer,
    ExtensionAsk,
    Reminder,
    extended_deadline,
)
from app.application.interactors.disputes import DisputeNews, DisputeReminder, side_user
from app.application.interactors.info_request import WAIT, InfoAsk, InfoTimeout
from app.application.interactors.payouts import Refunded
from app.domain.order import Order
from app.infrastructure.telegram.notifier import Notifier, Translate
from app.presentation.telegram.callbacks.chat import CDChat
from app.presentation.telegram.callbacks.executor import CDExt, CDXCancel, CDXOrder
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.callbacks.orders import CDOrder
from app.presentation.telegram.keyboards.common import app_button, button, markup
from app.presentation.telegram.keyboards.feedback import rate_keyboard
from app.presentation.telegram.keyboards.orders import deal_rows, extension_keyboard
from app.presentation.telegram.presenters.common.purchase import COPY_LIMIT, FILE_LIMIT
from app.utils.time import datetime_now


def _app_markup(text: str, url: str, path: str) -> InlineKeyboardMarkup | None:
    opener = app_button(text, url, path)
    return markup([[opener]]) if opener else None


def _reply_markup(tr: Translate, url: str, order_id: int, buyer: bool) -> InlineKeyboardMarkup:
    """Under a dispute notice: the chat in the bot, and the order in the Mini App."""
    chat = button(
        tr("buttons-chat_executor" if buyer else "buttons-chat_buyer"),
        CDChat(action="order", id=order_id),
        style="primary",
    )
    path = f"/orders/{order_id}" if buyer else f"/work/order/{order_id}"
    opener = app_button(tr("buttons-open"), url, path)
    return markup([[chat], [opener] if opener else []])


def _deal_markup(tr: Translate, order_id: int) -> InlineKeyboardMarkup:
    return markup([*deal_rows(tr, order_id), [button(tr("buttons-open"), CDOrder(id=order_id))]])


def _open_order(order_id: int) -> Callable[[Translate], InlineKeyboardMarkup]:
    return lambda tr: markup([[button(tr("buttons-open"), CDXOrder(id=order_id))]])


def _buyer_open(order_id: int) -> Callable[[Translate], InlineKeyboardMarkup]:
    return lambda tr: markup([[button(tr("buttons-open_order"), CDOrder(id=order_id))]])


def _result_markup(text: str, order_id: int) -> Callable[[Translate], InlineKeyboardMarkup]:
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
        rows.append(
            [
                button(tr("buttons-open_order"), CDOrder(id=order_id)),
                button(tr("buttons-menu"), CDMenu()),
            ]
        )
        return markup(rows)

    return build


@dataclass(frozen=True)
class OrderNotices:
    """Telegram messages about an order changing hands. Always call after the commit."""

    notifier: Notifier

    async def ready_for_buyer(self, order: Order, until: datetime | None) -> None:
        """The executor is done: the buyer checks the result (and the auto-confirmation starts)."""
        order_id = order.id
        await self.notifier.send(
            order.user_id,
            "messages-order-ready",
            lambda tr: _deal_markup(tr, order_id),
            id=str(order_id),
            time=until or "-",
        )

    async def contacts_blocked(
        self, order_id: int, role: str, alias: str | None, url: str
    ) -> None:
        """Support is told once when somebody keeps trying to pass contacts in an order chat."""
        await self.notifier.staff(
            lambda tr, _: tr(
                "messages-contacts-staff",
                id=str(order_id),
                who=tr(f"dispute-who-{role}") + (f" {html.quote(alias)}" if alias else ""),
            ),
            lambda tr: _app_markup(tr("buttons-order_open"), url, f"/support/review/{order_id}"),
        )

    async def dispute_opened(self, news: DisputeNews, url: str) -> None:
        """Support is told; the other side is asked to answer in the order chat."""
        order_id = news.order.id
        who = news.dispute.opened_role
        await self.notifier.staff(
            lambda tr, _: tr(
                "messages-dispute-staff", id=str(order_id), who=tr(f"dispute-who-{who}")
            ),
            lambda tr: _app_markup(tr("buttons-dispute_open"), url, f"/support/review/{order_id}"),
        )
        await self.ask_reply(news, url, "messages-dispute-reply")

    async def ask_reply(self, news: DisputeNews, url: str, key: str) -> None:
        """To the side the dispute waits for: answer in the chat before the deadline."""
        order, dispute = news.order, news.dispute
        user_id = side_user(order, news.side) if news.side else None
        if user_id is None or dispute.awaiting_until is None:
            return
        order_id, buyer = order.id, user_id == order.user_id
        await self.notifier.send(
            user_id,
            key,
            lambda tr: _reply_markup(tr, url, order_id, buyer),
            id=str(order_id),
            time=dispute.awaiting_until,
        )

    async def dispute_reminder(self, reminder: DisputeReminder, url: str) -> None:
        order, dispute = reminder.order, reminder.dispute
        user_id = side_user(order, dispute.awaiting_role or "")
        if user_id is None or dispute.awaiting_until is None:
            return
        order_id, buyer, left = order.id, user_id == order.user_id, reminder.left_minutes
        until = dispute.awaiting_until
        await self.notifier.send(
            user_id,
            lambda tr, _: tr(
                "messages-dispute-reminder",
                id=str(order_id),
                left=fmt_duration(tr, left),
                time=until,
            ),
            lambda tr: _reply_markup(tr, url, order_id, buyer),
        )

    async def dispute_closed(self, order: Order) -> None:
        for user_id in (order.user_id, order.executor_id):
            if user_id is not None:
                await self.notifier.send(
                    user_id,
                    "messages-dispute-closed",
                    _buyer_open(order.id) if user_id == order.user_id else _open_order(order.id),
                    id=str(order.id),
                )

    async def confirm_reminder(self, order: Order, until: datetime) -> None:
        order_id = order.id
        await self.notifier.send(
            order.user_id,
            "messages-order-confirm_reminder",
            lambda tr: _deal_markup(tr, order_id),
            id=str(order_id),
            time=until,
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
                _result_markup("", order.id),
            )
            await self.notifier.send_file(user_id, f"order-{order.id}.txt", text.encode("utf-8"))
        else:
            body = f"\n\n<code>{html.quote(text)}</code>" if text else ""
            await self.notifier.send(
                user_id,
                lambda tr, _: tr("messages-purchase-done", id=oid) + body,
                _result_markup(text, order.id),
            )
        await self.files(user_id, list(result.get("files", [])))

    async def files(self, user_id: int, file_ids: list[str]) -> None:
        for file_id in file_ids:
            await self.notifier.send_media(user_id, file_id)

    async def confirmed(self, order: Order) -> None:
        if order.executor_id is not None:
            await self.notifier.send(
                order.executor_id,
                "messages-executor-confirmed",
                _open_order(order.id),
                id=str(order.id),
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
            _buyer_open(refund.order_id),
            id=str(refund.order_id),
            amount=fmt_usd(refund.amount),
        )
        if refund.executor_id is not None:
            await self.notifier.send(
                refund.executor_id,
                "messages-executor-order_closed",
                _open_order(refund.order_id),
                id=str(refund.order_id),
            )

    async def reminder(self, reminder: Reminder) -> None:
        order = reminder.order
        if order.executor_id is None or order.deadline_at is None:
            return
        order_id, left = order.id, reminder.left_minutes
        until = order.deadline_at
        await self.notifier.send(
            order.executor_id,
            lambda tr, _: tr(
                "messages-executor-reminder",
                id=str(order_id),
                left=fmt_duration(tr, left),
                time=until,
            ),
            lambda tr: markup(
                [
                    [button(tr("buttons-open_order"), CDXOrder(id=order_id), style="primary")],
                    [button(tr("buttons-ext_ask"), CDExt(action="ask", id=order_id))],
                ]
            ),
        )

    async def extension_asked(self, ask: ExtensionAsk) -> None:
        """To the buyer, who sees the executor's alias at most: never a name or an id."""
        order = ask.order
        order_id, rid, minutes = order.id, ask.request_id, ask.minutes
        until = extended_deadline(order, minutes, datetime_now())
        await self.notifier.send(
            order.user_id,
            lambda tr, _: tr(
                "messages-order-extension_ask",
                id=str(order_id),
                duration=fmt_duration(tr, minutes),
                time=until,
            ),
            lambda tr: extension_keyboard(tr, order_id, rid),
        )

    async def extension_answered(self, answer: ExtensionAnswer) -> None:
        order = answer.order
        if order.executor_id is None or order.deadline_at is None:
            return
        key = "messages-executor-extended" if answer.approved else "messages-executor-ext_declined"
        await self.notifier.send(
            order.executor_id,
            key,
            _open_order(order.id),
            id=str(order.id),
            time=order.deadline_at,
        )

    async def cancel_asked(self, ask: CancelAsk) -> None:
        """To the executor: the buyer asks to cancel; silence for an hour counts as «yes»."""
        order = ask.order
        if order.executor_id is None:
            return
        order_id, rid = order.id, ask.request_id
        await self.notifier.send(
            order.executor_id,
            "messages-executor-cancel_ask",
            lambda tr: markup(
                [
                    [
                        button(
                            tr("buttons-cancel_yes"),
                            CDXCancel(id=order_id, rid=rid, ok=1),
                            style="success",
                        ),
                        button(tr("buttons-cancel_no"), CDXCancel(id=order_id, rid=rid, ok=0)),
                    ],
                    [button(tr("buttons-open_order"), CDXOrder(id=order_id))],
                ]
            ),
            id=str(order_id),
            time=datetime_now() + AGREE_AFTER,
        )

    async def cancel_answered(self, answer: CancelAnswer) -> None:
        order = answer.order
        order_id = order.id
        if answer.agreed and answer.refund is not None:
            await self.notifier.send(
                order.user_id,
                "messages-order-cancel_agreed",
                _buyer_open(order_id),
                id=str(order_id),
                amount=fmt_usd(answer.refund.amount),
            )
            if answer.by_timer and order.executor_id is not None:
                await self.notifier.send(
                    order.executor_id,
                    "messages-executor-cancel_by_timer",
                    _open_order(order_id),
                    id=str(order_id),
                )
            return
        await self.notifier.send(
            order.user_id,
            "messages-order-cancel_declined",
            lambda tr: markup(
                [
                    *deal_rows(tr, order_id, ok=False),
                    [button(tr("buttons-open_order"), CDOrder(id=order_id))],
                ]
            ),
            id=str(order_id),
        )

    def _answer_markup(
        self, url: str, order_id: int, conversation_id: int | None
    ) -> Callable[[Translate], InlineKeyboardMarkup]:
        """«Answer» (the order chat in the bot) and the same chat in the Mini App."""

        def build(tr: Translate) -> InlineKeyboardMarkup:
            path = (
                f"/orders/{order_id}/chat/{conversation_id}"
                if conversation_id
                else f"/orders/{order_id}"
            )
            opener = app_button(tr("buttons-open"), url, path)
            return markup(
                [
                    [
                        button(
                            tr("buttons-info_reply"),
                            CDChat(action="order", id=order_id),
                            style="primary",
                        )
                    ],
                    [opener] if opener else [],
                ]
            )

        return build

    async def info_asked(self, ask: InfoAsk, url: str) -> None:
        """To the buyer: the executor needs data. Only the alias-free question, never a name."""
        order = ask.order
        order_id, question = order.id, html.quote(ask.question)
        until = (order.paused_at or datetime_now()) + WAIT
        await self.notifier.send(
            order.user_id,
            "messages-order-info_ask",
            self._answer_markup(url, order_id, ask.posted.conversation_id),
            id=str(order_id),
            question=question,
            time=until,
        )

    async def info_reminder(self, order: Order, url: str) -> None:
        if order.paused_at is None:
            return
        until = order.paused_at + WAIT
        await self.notifier.send(
            order.user_id,
            "messages-order-info_reminder",
            self._answer_markup(url, order.id, None),
            id=str(order.id),
            time=until,
        )

    async def info_answered(self, order: Order, deadline: datetime) -> None:
        if order.executor_id is None:
            return
        await self.notifier.send(
            order.executor_id,
            "messages-executor-info_answered",
            _open_order(order.id),
            id=str(order.id),
            time=deadline,
        )

    async def info_timed_out(self, timeout: InfoTimeout) -> None:
        order, refund = timeout.order, timeout.refund
        await self.notifier.send(
            order.user_id,
            "messages-order-info_timeout",
            _buyer_open(order.id),
            id=str(order.id),
            amount=fmt_usd(refund.amount),
        )
        if order.executor_id is not None:
            await self.notifier.send(
                order.executor_id,
                "messages-executor-info_timeout",
                _open_order(order.id),
                id=str(order.id),
            )

    async def review_request(self, order: Order) -> None:
        order_id = order.id
        await self.notifier.send(
            order.user_id,
            "messages-feedback-ask",
            lambda tr: rate_keyboard(tr, order_id),
            id=str(order_id),
        )
