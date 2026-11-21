from dataclasses import dataclass
from typing import Any, Callable

from aiogram import html
from aiogram.types import InlineKeyboardMarkup
from aiogram_i18n import I18nContext

from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import RenderMode, View


def preview(
    tr: Callable[..., str], text: str | None, media: dict[str, Any] | None, limit: int
) -> str:
    """One line for a message in a list: the media type in brackets, then the text."""
    parts = []
    if media:
        parts.append(tr(f"messages-chat-media_{media['type']}"))
    if text:
        parts.append(html.quote(text[:limit] + ("…" if len(text) > limit else "")))
    return " ".join(parts)


@dataclass(frozen=True)
class SupportPresenter(BasePresenter):
    i18n: I18nContext

    def note(self, key: str, markup: InlineKeyboardMarkup | None = None, /, **kwargs: str) -> View:
        """A short answer in a new message, so the conversation above stays where it is."""
        return View(text=self.i18n.get(key, **kwargs), reply_markup=markup, mode=RenderMode.NEW)
