from dataclasses import dataclass
from decimal import Decimal
from html import escape

from aiogram_i18n import I18nContext

from app.application.cards import fmt_duration, render_card
from app.application.i18n_text import fmt_usd, pick_i18n
from app.application.interactors.executor_wallet import WalletSummary
from app.application.interactors.executors import CabinetOverview
from app.application.interactors.fulfillment_work import ExecutorOrderView
from app.application.interactors.stats import Stats
from app.application.models.form_schema import FieldType, FormField
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.presentation.telegram.keyboards.executor import (
    back_to_cabinet,
    balance_keyboard,
    cabinet_keyboard,
    extension_options_keyboard,
    order_back_keyboard,
    order_keyboard,
    orders_keyboard,
    refuse_keyboard,
    result_ask_keyboard,
    wallet_keyboard,
)
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import RenderMode, View
from app.utils.time import datetime_now


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
            online=i18n.get(f"messages-executor-online_{'on' if profile.is_online else 'off'}"),
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
        return View(text=text, reply_markup=cabinet_keyboard(i18n, profile.is_online))

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
        ext = view.extension
        can_extend = (
            order.status is OrderStatus.assigned
            and order.deadline_at is not None
            and order.deadline_at > datetime_now()
            and ext.can_request
        )
        if order.status is OrderStatus.assigned and ext.pending is not None:
            wait = fmt_duration(i18n.get, ext.pending.minutes)
            text += "\n" + i18n.messages.executor.ext_waiting(duration=wait)
        return View(text=text, reply_markup=order_keyboard(i18n, order, page, can_extend))

    def extension_options(self, order_id: int) -> View:
        return View(
            text=self.i18n.messages.executor.ext_pick(id=str(order_id)),
            reply_markup=extension_options_keyboard(self.i18n, order_id),
        )

    def result_ask(
        self,
        order_id: int,
        field: FormField,
        idx: int,
        total: int,
        *,
        current: bool,
        reason: str | None = None,
        files: int = 0,
    ) -> View:
        i18n = self.i18n
        text = i18n.messages.executor.result_ask(
            id=str(order_id),
            step=str(idx + 1),
            total=str(total),
            label=escape(pick_i18n(field.label, i18n.locale)),
        )
        if field.type is FieldType.file:
            many = field.max_files > 1
            text += "\n" + (
                i18n.messages.purchase.hint_files(max=field.max_files)
                if many
                else i18n.messages.purchase.hint_file()
            )
            if many:
                text += "\n" + i18n.messages.purchase.files_progress(n=files, max=field.max_files)
        if reason is not None:
            text = i18n.messages.purchase.invalid(reason=reason) + "\n\n" + text
        return View(
            text=text,
            reply_markup=result_ask_keyboard(i18n, order_id, field, files),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )

    def note(self, key: str, order_id: int, **kwargs: str) -> View:
        """A short message with a way back to the order."""
        return View(
            text=self.i18n.get(key, id=str(order_id), **kwargs),
            reply_markup=order_back_keyboard(self.i18n, order_id),
        )

    def rating(self, stats: Stats) -> View:
        i18n = self.i18n
        text = i18n.messages.executor.rating(
            completed=str(stats.completed),
            failed=str(stats.failed),
            overdue=str(stats.overdue),
            refused=str(stats.refused),
            minutes=f"{stats.avg_minutes:.0f}" if stats.avg_minutes is not None else "-",
            score=f"{stats.avg_score:.2f}" if stats.avg_score is not None else "-",
        )
        return View(text=text, reply_markup=back_to_cabinet(i18n))

    def balance(self, summary: WalletSummary, notice: str | None = None) -> View:
        i18n = self.i18n
        if summary.entries:
            history = "\n".join(
                i18n.messages.balance.entry(
                    date=e.created_at.strftime("%d.%m.%Y"),
                    kind=i18n.get(f"ledger-kind-{e.kind}"),
                    amount=("+" if e.amount > 0 else "") + fmt_usd(e.amount),
                )
                for e in summary.entries
            )
        else:
            history = i18n.messages.balance.history_empty()
        text = i18n.messages.executor.balance(
            hold=fmt_usd(summary.hold),
            available=fmt_usd(summary.available),
            minimum=fmt_usd(summary.minimum),
            history=history,
        )
        if notice:
            text = f"{notice}\n\n{text}"
        return View(text=text, reply_markup=balance_keyboard(i18n))

    def wallet(
        self, summary: WalletSummary, notice_key: str | None = None, *, current: bool = False
    ) -> View:
        i18n = self.i18n
        text = (
            i18n.messages.executor.wallet(address=escape(summary.wallet))
            if summary.wallet
            else i18n.messages.executor.wallet_empty()
        )
        if notice_key:
            text = f"{i18n.get(notice_key)}\n\n{text}"
        return View(
            text=text,
            reply_markup=wallet_keyboard(i18n),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )

    def ask_wallet(self, *, error: bool = False, current: bool = False) -> View:
        text = self.i18n.messages.executor.wallet_ask()
        if error:
            text = self.i18n.messages.executor.wallet_invalid() + "\n\n" + text
        return View(
            text=text,
            reply_markup=back_to_cabinet(self.i18n),
            mode=RenderMode.CURRENT if current else RenderMode.ANSWER,
        )

    def below_minimum(self, minimum: Decimal) -> str:
        return self.i18n.messages.executor.below_minimum(minimum=fmt_usd(minimum))

    def withdrawal_created(self, amount: Decimal) -> str:
        return self.i18n.messages.executor.withdrawal_created(amount=fmt_usd(amount))
