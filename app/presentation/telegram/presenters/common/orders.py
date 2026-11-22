from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from aiogram import html
from aiogram_i18n import I18nContext

from app.application.i18n_text import country_flag, fmt_usd, pick_i18n
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.presentation.telegram.callbacks.orders import CDOrders
from app.presentation.telegram.keyboards.orders import (
    cancel_confirm_keyboard,
    order_back_keyboard,
    order_keyboard,
    orders_keyboard,
    reorder_row,
)
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.presenters.common.purchase import result_view
from app.presentation.telegram.view.models import View

_CHAIN = (
    OrderStatus.paid,
    OrderStatus.in_queue,
    OrderStatus.assigned,
    OrderStatus.ready,
    OrderStatus.completed,
)


def _times(events: list[OrderEvent]) -> dict[str, datetime]:
    """When each step was last reached: the payment, then every status change."""
    at: dict[str, datetime] = {}
    for e in events:
        if e.type == "paid":
            at["paid"] = e.created_at
        elif e.type == "status":
            at[str(e.payload.get("to"))] = e.created_at
    return at


@dataclass(frozen=True)
class OrdersPresenter(BasePresenter):
    i18n: I18nContext

    def orders(self, orders: list[Order], total: int, page: int) -> View:
        if not orders:
            return View(
                text=self.i18n.messages.orders.empty(),
                reply_markup=orders_keyboard(self.i18n, [], 0, 0),
            )
        return View(
            text=self.i18n.messages.orders.title(),
            reply_markup=orders_keyboard(self.i18n, orders, total, page),
        )

    def not_found(self, page: int) -> View:
        return View(
            text=self.i18n.messages.orders.not_found(),
            reply_markup=order_back_keyboard(self.i18n, page),
        )

    def _steps(self, order: Order, events: list[OrderEvent]) -> str:
        """Progress: passed steps with their time, the current one, what is still ahead."""
        at = _times(events)
        if order.status not in _CHAIN:  # failed, refunded, cancelled: what was reached, the end
            return "\n".join(
                [*(self._done(s, at) for s in _CHAIN if s in at), self._final(order.status, at)]
            )
        now = _CHAIN.index(order.status)
        lines = []
        for i, step in enumerate(_CHAIN):
            if i < now:
                lines += [self._done(step, at)] if step in at else []
            elif i == now:
                lines.append(self._current(order, at))
            else:
                lines.append(self.i18n.messages.order.step_next(name=self._name(step)))
        return "\n".join(lines)

    def _name(self, step: str) -> str:
        return self.i18n.get(f"order-step-{step}")

    def _done(self, step: str, at: dict[str, datetime]) -> str:
        messages = self.i18n.messages.order
        if step not in at:
            return messages.step_done_notime(name=self._name(step))
        return messages.step_done(name=self._name(step), time=at[step].strftime("%H:%M"))

    def _final(self, status: str, at: dict[str, datetime]) -> str:
        if status not in at:
            return self._name(status)
        time = at[status].strftime("%H:%M")
        return self.i18n.messages.order.step_final(name=self._name(status), time=time)

    def _current(self, order: Order, at: dict[str, datetime]) -> str:
        messages = self.i18n.messages.order
        name = self._name(order.status)
        if order.status is OrderStatus.completed:
            return self._done(order.status, at)
        if order.status is OrderStatus.assigned and order.deadline_at:
            return messages.step_until(name=name, time=order.deadline_at.strftime("%H:%M"))
        return messages.step_now(name=name)

    def order(
        self,
        order: Order,
        page: int,
        events: list[OrderEvent],
        alias: str | None,
        reorder: bool = False,
    ) -> tuple[View, bytes | None]:
        i18n = self.i18n
        snap = order.snapshot
        variant = snap.get("variant") or {}
        variant_name = pick_i18n(variant.get("title"), i18n.locale)
        if country := variant.get("country"):
            variant_name = " ".join(
                x for x in (country_flag(country), variant_name or country) if x
            )
        text = i18n.messages.order(
            id=order.id,
            product=html.quote(pick_i18n(snap.get("product"), i18n.locale)),
            variant=html.quote(variant_name or "-"),
            total=fmt_usd(order.price - order.discount),
            steps=self._steps(order, events),
            executor="\n\n" + i18n.messages.order.executor(alias=html.quote(alias))
            if alias
            else "",
        )
        if order.status is OrderStatus.completed and order.result:
            return result_view(
                i18n,
                text,
                str(order.result.get("text", "")),
                CDOrders(page=page),
                reorder_row(i18n, order) if reorder else None,
            )
        return View(text=text, reply_markup=order_keyboard(i18n, order, page, reorder)), None

    def cancel_confirm(self, order_id: int, page: int) -> View:
        return View(
            text=self.i18n.messages.orders.cancel_confirm(id=str(order_id)),
            reply_markup=cancel_confirm_keyboard(self.i18n, order_id, page),
        )

    def cancelled(self, order_id: int, amount: Decimal, page: int) -> View:
        return View(
            text=self.i18n.messages.orders.cancelled(id=str(order_id), amount=fmt_usd(amount)),
            reply_markup=order_back_keyboard(self.i18n, page),
        )
