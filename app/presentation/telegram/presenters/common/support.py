from dataclasses import dataclass
from typing import Any, Callable

from aiogram import html
from aiogram_i18n import I18nContext

from app.domain.enums.support import ChatRole
from app.domain.support import Message
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import RenderMode, View

HISTORY_CHARS = 3500


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

    def note(self, key: str, **kwargs: str) -> View:
        """A short answer in a new message, so the conversation above stays where it is."""
        return View(text=self.i18n.get(key, **kwargs), mode=RenderMode.NEW)

    def history(self, messages: list[Message]) -> View:
        tr = self.i18n.get
        if not messages:
            return View(text=tr("messages-chat-history_empty"), mode=RenderMode.NEW)
        lines: list[str] = []
        size = 0
        for m in reversed(messages):  # keep the newest when it does not fit
            who = tr(
                "messages-chat-who_buyer"
                if m.sender_role == ChatRole.buyer
                else "messages-chat-who_support"
            )
            line = tr(
                "messages-chat-history_line",
                time=m.created_at.strftime("%d.%m %H:%M"),
                who=who,
                text=preview(tr, m.text, m.media, 300),
            )
            if size + len(line) > HISTORY_CHARS:
                break
            lines.append(line)
            size += len(line) + 1
        body = "\n".join(reversed(lines))
        return View(text=f"{tr('messages-chat-history_title')}\n\n{body}", mode=RenderMode.NEW)
