from dataclasses import dataclass
from decimal import Decimal

from aiogram import html
from aiogram_i18n import I18nContext

from app.application.i18n_text import country_flag, fmt_usd, pick_i18n
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.presentation.telegram.callbacks.orders import CDOrders
from app.presentation.telegram.keyboards.orders import (
    cancel_confirm_keyboard,
    executors_keyboard,
    order_back_keyboard,
    order_keyboard,
    orders_keyboard,
)
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.presenters.common.purchase import result_view
from app.presentation.telegram.view.models import View


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

    def order(self, order: Order, page: int) -> tuple[View, bytes | None]:
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
            status=i18n.get(f"order-status-{order.status}"),
            date=order.created_at.strftime("%d.%m.%Y %H:%M"),
            total=fmt_usd(order.price - order.discount),
        )
        if order.status is OrderStatus.completed and order.result:
            return result_view(i18n, text, str(order.result.get("text", "")), CDOrders(page=page))
        return View(text=text, reply_markup=order_keyboard(i18n, order, page)), None

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

    def executors(self, rows: list[tuple[str, int]]) -> View:
        i18n = self.i18n
        if rows:
            body = "\n".join(
                i18n.messages.orders.executor_line(alias=html.quote(alias), count=str(count))
                for alias, count in rows
            )
            text = i18n.messages.orders.executors_title() + "\n\n" + body
        else:
            text = i18n.messages.orders.executors_empty()
        return View(text=text, reply_markup=executors_keyboard(i18n))
