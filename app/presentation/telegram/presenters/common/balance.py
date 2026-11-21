from dataclasses import dataclass
from decimal import Decimal

from aiogram_i18n import I18nContext

from app.application.i18n_text import fmt_usd
from app.domain.ledger import LedgerEntry
from app.presentation.telegram.keyboards.balance import (
    back_to_balance,
    balance_keyboard,
    topup_keyboard,
)
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import RenderMode, View


@dataclass(frozen=True)
class BalancePresenter(BasePresenter):
    i18n: I18nContext

    @staticmethod
    def _mode(current: bool) -> RenderMode:
        return RenderMode.CURRENT if current else RenderMode.ANSWER

    def balance(
        self,
        amount: Decimal,
        entries: list[LedgerEntry],
        *,
        current: bool = False,
        notice: str | None = None,
    ) -> View:
        i18n = self.i18n
        if entries:
            history = "\n".join(
                i18n.messages.balance.entry(
                    date=e.created_at.strftime("%d.%m.%Y"),
                    kind=i18n.get(f"ledger-kind-{e.kind}"),
                    amount=("+" if e.amount > 0 else "") + fmt_usd(e.amount),
                )
                for e in entries
            )
        else:
            history = i18n.messages.balance.history_empty()
        text = i18n.messages.balance(amount=fmt_usd(amount), history=history)
        if notice:
            text = f"{notice}\n\n{text}"
        return View(text=text, reply_markup=balance_keyboard(i18n), mode=self._mode(current))

    def topup(self, enabled: bool) -> View:
        text = (
            self.i18n.messages.topup.choose() if enabled else self.i18n.messages.topup.disabled()
        )
        return View(text=text, reply_markup=topup_keyboard(self.i18n, enabled))

    def ask(self, key: str, *, error: str | None = None, current: bool = False) -> View:
        text = self.i18n.get(key)
        if error:
            text = f"{error}\n\n{text}"
        return View(text=text, reply_markup=back_to_balance(self.i18n), mode=self._mode(current))

    def topup_done(self, amount: Decimal) -> str:
        return self.i18n.messages.topup.done(amount=fmt_usd(amount))

    def redeem_done(self, amount: Decimal) -> str:
        return self.i18n.messages.redeem.done(amount=fmt_usd(amount))

    def redeem_error(self, code: str) -> str:
        reason = self.i18n.get(f"messages-promo-reason_{code}")
        return self.i18n.messages.redeem.error(reason=reason)

    def invalid_amount(self) -> str:
        return self.i18n.messages.topup.invalid()

    def text(self, key: str, **kwargs: str) -> View:
        return View(text=self.i18n.get(key, **kwargs))

    def notice_for(self, locale: str, amount: Decimal) -> str:
        key = "messages-balance-credited" if amount > 0 else "messages-balance-debited"
        return self.i18n.get(key, locale, amount=fmt_usd(abs(amount)))
