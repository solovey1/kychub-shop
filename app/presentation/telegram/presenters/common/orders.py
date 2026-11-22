from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from aiogram import html
from aiogram_i18n import I18nContext

from app.application.cards import fmt_duration
from app.application.i18n_text import country_flag, fmt_time, fmt_usd, pick_i18n
from app.application.interactors.cancel_request import CancelState
from app.application.interactors.deadlines import ExtensionAnswer, Pending, extended_deadline
from app.application.interactors.disputes import DisputeNews
from app.application.interactors.info_state import InfoPending
from app.domain.dispute import Dispute
from app.domain.enums.order import OrderStatus
from app.domain.order import Order, OrderEvent
from app.domain.user import User
from app.presentation.telegram.callbacks.executor import CDXOrder
from app.presentation.telegram.callbacks.orders import CDOrders
from app.presentation.telegram.keyboards.common import button, markup
from app.presentation.telegram.keyboards.orders import (
    cancel_confirm_keyboard,
    dispute_ask_keyboard,
    order_back_keyboard,
    order_keyboard,
    orders_keyboard,
    reorder_row,
)
from app.presentation.telegram.presenters.base import BasePresenter, Keys
from app.presentation.telegram.presenters.common.purchase import result_view
from app.presentation.telegram.view.models import View
from app.utils.time import datetime_now

RESULT_SHOWN = 2500

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


def dispute_line(i18n: I18nContext, dispute: Dispute, me: str, tz: str | None) -> str:
    """The banner of an open dispute for the buyer (`me`="buyer") or the executor."""
    if dispute.awaiting_role is None or dispute.awaiting_until is None:
        return i18n.messages.order.dispute()
    who = i18n.get(
        "dispute-from-you"
        if dispute.awaiting_role == me
        else f"dispute-from-{dispute.awaiting_role}"
    )
    return i18n.messages.order.dispute_wait(who=who, time=fmt_time(dispute.awaiting_until, tz))


@dataclass(frozen=True)
class OrdersPresenter(BasePresenter):
    i18n: I18nContext
    user: User

    def _time(self, at: datetime) -> str:
        return fmt_time(at, self.user.timezone)

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
        messages = Keys(self.i18n, "messages-order")
        if step not in at:
            return messages.step_done_notime(name=self._name(step))
        return messages.step_done(name=self._name(step), time=self._time(at[step]))

    def _final(self, status: str, at: dict[str, datetime]) -> str:
        if status not in at:
            return self._name(status)
        time = self._time(at[status])
        return self.i18n.messages.order.step_final(name=self._name(status), time=time)

    def _current(self, order: Order, at: dict[str, datetime]) -> str:
        messages = Keys(self.i18n, "messages-order")
        name = self._name(order.status)
        if order.status is OrderStatus.completed:
            return self._done(order.status, at)
        if order.status is OrderStatus.assigned and order.deadline_at:
            return messages.step_until(name=name, time=self._time(order.deadline_at))
        return messages.step_now(name=name)

    def _executor(self, alias: str, rating: tuple[float | None, int]) -> str:
        """Alias with the average score, or «new executor» while nobody rated him."""
        score, count = rating
        name = html.quote(alias)
        if score is None or count == 0:
            return self.i18n.get("messages-order-executor_new", alias=name)
        return self.i18n.get(
            "messages-order-executor_rated", alias=name, score=f"{score:.1f}", n=count
        )

    def order(
        self,
        order: Order,
        page: int,
        events: list[OrderEvent],
        alias: str | None,
        reorder: bool = False,
        reserved: Decimal = Decimal(0),
        pending: Pending | None = None,
        confirm_at: datetime | None = None,
        dispute: Dispute | None = None,
        cancel: CancelState | None = None,
        rating: tuple[float | None, int] = (None, 0),
        info: InfoPending | None = None,
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
            held="\n" + i18n.messages.order.held(amount=fmt_usd(reserved)) if reserved > 0 else "",
            steps=self._steps(order, events),
            executor="\n\n" + self._executor(alias, rating) if alias else "",
        )
        if pending is not None:
            until = extended_deadline(order, pending.minutes, datetime_now())
            text += "\n\n" + i18n.messages.order.extension(
                duration=fmt_duration(i18n.get, pending.minutes), time=self._time(until)
            )
        if cancel is not None and cancel.pending is not None and dispute is None:
            text += "\n\n" + i18n.messages.order.cancel_wait(
                time=self._time(cancel.pending.agrees_at)
            )
        if info is not None and dispute is None:
            text += "\n\n" + i18n.messages.order.info_wait(
                question=html.quote(info.question), time=self._time(info.until)
            )
        if dispute is not None:
            text += "\n\n" + dispute_line(i18n, dispute, "buyer", self.user.timezone)
        if order.status is OrderStatus.ready and order.result:
            shown = html.quote(str(order.result.get("text", ""))[:RESULT_SHOWN])
            text += "\n\n" + i18n.messages.order.check(
                result=f"<code>{shown}</code>" if shown else "-",
                files=str(len(order.result.get("files", []))),
                time=self._time(confirm_at) if confirm_at else "-",
            )
        if order.status is OrderStatus.completed and order.result:
            return result_view(
                i18n,
                text,
                str(order.result.get("text", "")),
                CDOrders(page=page),
                reorder_row(i18n, order) if reorder else None,
            )
        return View(
            text=text,
            reply_markup=order_keyboard(
                i18n,
                order,
                page,
                reorder,
                pending,
                dispute is not None,
                bool(cancel and cancel.can_request and dispute is None)
                and order.status is OrderStatus.assigned,
                info is not None and dispute is None,
            ),
        ), None

    def dispute_ask(self, order_id: int, page: int) -> View:
        return View(
            text=self.i18n.messages.dispute.ask_reason(id=str(order_id)),
            reply_markup=dispute_ask_keyboard(self.i18n.get, order_id, page),
        )

    def dispute_opened(self, news: DisputeNews, page: int, *, buyer: bool) -> View:
        order = news.order
        until = news.dispute.awaiting_until
        back = (
            order_back_keyboard(self.i18n, page)
            if buyer
            else markup([[button(self.i18n.buttons.back(), CDXOrder(id=order.id))]])
        )
        return View(
            text=self.i18n.messages.dispute.opened(
                id=str(order.id), time=self._time(until) if until else "-"
            ),
            reply_markup=back,
        )

    def dispute_not_accepted(self, order_id: int, page: int) -> View:
        return View(
            text=self.i18n.get("messages-dispute-not_accepted", id=str(order_id)),
            reply_markup=order_back_keyboard(self.i18n, page),
        )

    def executor_back(self, order_id: int) -> View:
        return View(
            text=self.i18n.messages.dispute.cancelled(),
            reply_markup=markup([[button(self.i18n.buttons.back(), CDXOrder(id=order_id))]]),
        )

    def cancel_asked(self, order_id: int, page: int) -> View:
        return View(
            text=self.i18n.messages.order.cancel_asked(id=str(order_id)),
            reply_markup=order_back_keyboard(self.i18n, page),
        )

    def cancel_unavailable(self) -> str:
        return self.i18n.messages.order.cancel_unavailable()

    def confirmed(self, order_id: int, page: int) -> View:
        return View(
            text=self.i18n.messages.order.confirmed(id=str(order_id)),
            reply_markup=order_back_keyboard(self.i18n, page),
        )

    def extension_stale(self) -> str:
        return self.i18n.messages.order.extension_stale()

    def extension_answered(self, answer: ExtensionAnswer) -> View:
        messages = Keys(self.i18n, "messages-order")
        order = answer.order
        if answer.approved and order.deadline_at is not None:
            text = messages.extension_yes(id=str(order.id), time=self._time(order.deadline_at))
        else:
            text = messages.extension_no(id=str(order.id))
        return View(text=text)

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
