from aiogram.filters.callback_data import CallbackData
from aiogram.types import DisabledButton, InlineKeyboardButton, InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import country_flag, fmt_usd, pick_i18n
from app.application.interactors.catalog import CategoryPage, ProductCard, VariantView
from app.presentation.telegram.callbacks.catalog import CDCategory, CDProduct, CDVariant
from app.presentation.telegram.callbacks.menu import CDMenu
from app.presentation.telegram.keyboards.common import button, markup, pager


def variant_label(view: VariantView, locale: str) -> str:
    v = view.variant
    name = pick_i18n(view.country.title_i18n, locale) if view.country else ""
    name = name or pick_i18n(v.title_i18n, locale)
    flag = country_flag(v.country_code)
    prefix = " ".join(x for x in (flag, name) if x)
    price = fmt_usd(v.price)
    return f"{prefix} — {price}" if prefix else price


def category_keyboard(i18n: I18nContext, page: CategoryPage) -> InlineKeyboardMarkup:
    rows = [
        [button(pick_i18n(c.title_i18n, i18n.locale), CDCategory(id=c.id))] for c in page.children
    ]
    rows += [
        [button(pick_i18n(p.title_i18n, i18n.locale), CDProduct(id=p.id))] for p in page.products
    ]
    cat = page.category
    back: CallbackData = CDMenu()
    if cat is not None:
        rows.append(pager(page.page, page.pages, lambda n: CDCategory(id=cat.id, page=n)))
        back = CDCategory(id=cat.parent_id or 0)
    rows.append([button(i18n.buttons.back(), back)])
    return markup(rows)


def product_keyboard(i18n: I18nContext, card: ProductCard) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for view in card.variants:
        label = variant_label(view, i18n.locale)
        if view.in_stock:
            rows.append([button(label, CDVariant(id=view.variant.id))])
        else:
            text = i18n.buttons.out_of_stock(label=label)
            rows.append([InlineKeyboardButton(text=text, disabled=DisabledButton())])
    rows.append([button(i18n.buttons.back(), CDCategory(id=card.product.category_id))])
    return markup(rows)
