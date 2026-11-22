from __future__ import annotations

from dataclasses import dataclass

from aiogram import html
from aiogram_i18n import I18nContext

from app.application.cards import fmt_duration
from app.application.i18n_text import pick_i18n
from app.application.interactors.catalog import CategoryPage, ProductCard
from app.presentation.telegram.keyboards.catalog import category_keyboard, product_keyboard
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import View


@dataclass(frozen=True)
class CatalogPresenter(BasePresenter):
    i18n: I18nContext

    def category(self, page: CategoryPage) -> View:
        if page.category is None:
            title = self.i18n.messages.catalog.root()
        else:
            title = f"<b>{html.quote(pick_i18n(page.category.title_i18n, self.i18n.locale))}</b>"
        text = title
        if not page.children and not page.products:
            text += "\n\n" + self.i18n.messages.catalog.empty()
        return View(text=text, reply_markup=category_keyboard(self.i18n, page))

    def product(self, card: ProductCard) -> View:
        locale = self.i18n.locale
        product = card.product
        parts = [
            self.i18n.messages.product(title=html.quote(pick_i18n(product.title_i18n, locale)))
        ]
        if description := pick_i18n(product.description_i18n, locale):
            parts.append(html.quote(description))
        if card.deadline_minutes:
            time = fmt_duration(self.i18n.get, card.deadline_minutes)
            parts.append(self.i18n.messages.product.deadline(time=time))
        parts.append(self.i18n.messages.product.choose())
        return View(text="\n\n".join(parts), reply_markup=product_keyboard(self.i18n, card))

    def unavailable(self) -> View:
        return View(text=self.i18n.messages.product.unavailable())
