from dataclasses import dataclass
from html import escape

from aiogram_i18n import I18nContext

from app.application.cards import render_card
from app.application.i18n_text import pick_i18n
from app.application.interactors.executors import CabinetOverview
from app.application.interactors.fulfillment_work import ExecutorOrderView
from app.application.models.form_schema import FieldType, FormField
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.presentation.telegram.keyboards.executor import (
    cabinet_keyboard,
    order_back_keyboard,
    order_keyboard,
    orders_keyboard,
    refuse_keyboard,
    result_ask_keyboard,
)
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import RenderMode, View


@dataclass(frozen=True)
class ExecutorPresenter(BasePresenter):
    i18n: I18nContext

    def cabinet(self, overview: CabinetOverview) -> View:
        i18n = self.i18n
        profile = overview.profile
        if overview.permissions:
            permissions = "\n".join(
                f"{escape(service)}: {', '.join(countries)}"
                for service, countries in overview.permissions.items()
            )
        else:
            permissions = i18n.messages.executor.no_permissions()
        text = i18n.messages.executor.cabinet(
            alias=escape(profile.alias),
            status=i18n.get(f"messages-executor-status_{'on' if profile.is_active else 'off'}"),
            limit=str(profile.max_parallel_orders),
            percent=(
                f"{profile.percent_override}%"
                if profile.percent_override is not None
                else i18n.messages.executor.percent_service()
            ),
            permissions=permissions,
        )
        return View(text=text, reply_markup=cabinet_keyboard(i18n))

    def text(self, key: str, **kwargs: str) -> View:
        return View(text=self.i18n.get(key, **kwargs))

    def taken(self, order_id: int) -> View:
        return View(
            text=self.i18n.messages.executor.taken(id=str(order_id)),
            reply_markup=refuse_keyboard(self.i18n, order_id),
        )

    def orders(self, orders: list[Order], total: int, page: int) -> View:
        i18n = self.i18n
        text = (
            i18n.messages.executor.orders_title()
            if orders
            else i18n.messages.executor.orders_empty()
        )
        return View(text=text, reply_markup=orders_keyboard(i18n, orders, total, page))

    def order(self, view: ExecutorOrderView, page: int) -> View:
        i18n = self.i18n
        order = view.order
        text = i18n.messages.executor.order(
            card=render_card(i18n.get, i18n.locale, view.card),
            status=i18n.get(f"order-status-{order.status}"),
        )
        if order.deadline_at is not None and order.status is OrderStatus.assigned:
            until = order.deadline_at.strftime("%d.%m.%Y %H:%M")
            text += "\n" + i18n.messages.executor.until(time=until)
        return View(text=text, reply_markup=order_keyboard(i18n, order, page))

    def result_ask(
        self,
        order_id: int,
        field: FormField,
        idx: int,
        total: int,
        *,
        current: bool,
        reason: str | None = None,
    ) -> View:
        i18n = self.i18n
        text = i18n.messages.executor.result_ask(
            id=str(order_id),
            step=str(idx + 1),
            total=str(total),
            label=escape(pick_i18n(field.label, i18n.locale)),
        )
        if field.type is FieldType.file:
            text += "\n" + i18n.messages.purchase.hint_file()
        if reason is not None:
            text = i18n.messages.purchase.invalid(reason=reason) + "\n\n" + text
        return View(
            text=text,
            reply_markup=result_ask_keyboard(i18n, order_id, field),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )

    def note(self, key: str, order_id: int, **kwargs: str) -> View:
        """A short message with a way back to the order."""
        return View(
            text=self.i18n.get(key, id=str(order_id), **kwargs),
            reply_markup=order_back_keyboard(self.i18n, order_id),
        )
