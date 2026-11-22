from typing import Final

from aiogram.types import InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup
from aiogram_i18n import I18nContext

from app.application.i18n_text import pick_i18n
from app.application.interactors.catalog import VariantView
from app.domain.catalog import Product
from app.presentation.telegram.callbacks.balance import CDBalance
from app.presentation.telegram.callbacks.catalog import CDVariant
from app.presentation.telegram.callbacks.executor import CDCabinet
from app.presentation.telegram.callbacks.menu import CDLang, CDMenu
from app.presentation.telegram.keyboards.catalog import variant_name
from app.presentation.telegram.keyboards.common import app_button, button, markup

LANGUAGES = (("ru", "Русский"), ("en", "English"), ("uk", "Українська"))
# the bottom keyboard, row by row; `buttons-nav_<section>` in ftl
NAV_SECTIONS: Final = (("catalog", "orders"), ("balance", "support"))
REORDER_CHARS: Final = 32


def nav_keyboard(i18n: I18nContext) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=i18n.get(f"buttons-nav_{s}")) for s in row]
            for row in NAV_SECTIONS
        ],
        is_persistent=True,
        resize_keyboard=True,
    )


def reorder_label(i18n: I18nContext, view: VariantView, product: Product) -> str:
    parts = (pick_i18n(product.title_i18n, i18n.locale), variant_name(view, i18n.locale))
    title = ", ".join(p for p in parts if p)
    if len(title) > REORDER_CHARS:
        title = title[: REORDER_CHARS - 1].rstrip() + "…"
    return i18n.buttons.reorder(title=title)


def main_menu_keyboard(
    i18n: I18nContext,
    reorders: list[tuple[VariantView, Product]],
    is_executor: bool,
    is_staff: bool,
    server_url: str,
) -> InlineKeyboardMarkup:
    opener = app_button(i18n.buttons.app(), server_url, "/")
    panel = app_button(i18n.buttons.admin(), server_url, "/admin") if is_staff else None
    return markup(
        [
            *[
                [button(reorder_label(i18n, view, product), CDVariant(id=view.variant.id))]
                for view, product in reorders
            ],
            [
                button(i18n.buttons.topup(), CDBalance()),
                button(i18n.buttons.language(), CDLang()),
            ],
            [opener] if opener else [],
            [panel] if panel else [],
            [button(i18n.buttons.cabinet(), CDCabinet())] if is_executor else [],
        ]
    )


def language_keyboard(i18n: I18nContext) -> InlineKeyboardMarkup:
    rows = [[button(title, CDLang(code=code))] for code, title in LANGUAGES]
    rows.append([button(i18n.buttons.back(), CDMenu())])
    return markup(rows)
