"""Swap plain emoji for the FarmHub custom emoji in outgoing messages and inline buttons."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import TYPE_CHECKING, Any

from aiogram.client.default import Default
from aiogram.client.session.middlewares.base import BaseRequestMiddleware
from aiogram.methods import (
    EditMessageCaption,
    EditMessageReplyMarkup,
    EditMessageText,
    SendDocument,
    SendMessage,
    SendPhoto,
)
from aiogram.types import InlineKeyboardMarkup

if TYPE_CHECKING:
    from aiogram.client.bot import Bot
    from aiogram.client.session.middlewares.base import NextRequestMiddlewareType
    from aiogram.methods import Response, TelegramMethod
    from aiogram.methods.base import TelegramType

IDS_PATH = Path(__file__).resolve().parents[3] / "assets" / "emoji" / "ids.json"
MAX_PER_MESSAGE = 100  # Telegram limit of custom emoji entities in one message
FE0F = "️"
TEXT_METHODS = (SendMessage, EditMessageText)
CAPTION_METHODS = (SendPhoto, SendDocument, EditMessageCaption)
_TAG = re.compile(r"""<(?:[^>"']|"[^"]*"|'[^']*')*>""")
_NAME = re.compile(r"</?\s*([a-zA-Z-]+)")
_VERBATIM = {"code", "pre", "tg-emoji"}


def load_ids(path: Path = IDS_PATH) -> dict[str, str]:
    """Return {emoji without FE0F: custom_emoji_id}; empty when the file is missing or broken."""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {k.replace(FE0F, ""): str(v) for k, v in raw.items() if k.replace(FE0F, "")}


def _pattern(ids: dict[str, str]) -> re.Pattern[str]:
    keys = sorted(ids, key=len, reverse=True)
    return re.compile("(" + "|".join(map(re.escape, keys)) + ")" + FE0F + "?")


def wrap_text(html: str, ids: dict[str, str], pattern: re.Pattern[str] | None = None) -> str:
    """Wrap known emoji in <tg-emoji>, skipping code, pre, tag attributes and wrapped emoji."""
    if not ids:
        return html
    pattern = pattern or _pattern(ids)
    budget = MAX_PER_MESSAGE - html.count("<tg-emoji")

    def sub(m: re.Match[str]) -> str:
        nonlocal budget
        if budget <= 0:
            return m.group(0)
        budget -= 1
        return f'<tg-emoji emoji-id="{ids[m.group(1)]}">{m.group(0)}</tg-emoji>'

    out: list[str] = []
    depth = 0  # open verbatim elements
    pos = 0
    for tag in _TAG.finditer(html):
        chunk = html[pos : tag.start()]
        out.append(chunk if depth else pattern.sub(sub, chunk))
        out.append(tag.group(0))
        pos = tag.end()
        name = _NAME.match(tag.group(0))
        if name and name.group(1).lower() in _VERBATIM:
            depth = max(0, depth + (-1 if tag.group(0).startswith("</") else 1))
    tail = html[pos:]
    out.append(tail if depth else pattern.sub(sub, tail))
    return "".join(out)


def convert_markup(
    markup: InlineKeyboardMarkup, ids: dict[str, str], pattern: re.Pattern[str] | None = None
) -> InlineKeyboardMarkup:
    """Move a leading known emoji of each button into icon_custom_emoji_id."""
    pattern = pattern or _pattern(ids)
    rows = []
    for row in markup.inline_keyboard:
        new_row = []
        for button in row:
            m = pattern.match(button.text)
            if button.icon_custom_emoji_id or not m or not button.text[m.end() :].strip():
                new_row.append(button)
                continue
            new_row.append(
                button.model_copy(
                    update={
                        "text": button.text[m.end() :].lstrip(),
                        "icon_custom_emoji_id": ids[m.group(1)],
                    }
                )
            )
        rows.append(new_row)
    return markup.model_copy(update={"inline_keyboard": rows})


class CustomEmojiMiddleware(BaseRequestMiddleware):
    def __init__(self, ids: dict[str, str]) -> None:
        self.ids = ids
        self.pattern = _pattern(ids) if ids else None

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        if self.pattern is not None:
            self._rewrite(bot, method)
        return await make_request(bot, method)

    def _rewrite(self, bot: Bot, method: Any) -> None:
        if isinstance(method, (*TEXT_METHODS, *CAPTION_METHODS)):
            mode = method.parse_mode
            if isinstance(mode, Default):
                mode = bot.default.parse_mode
            field = "text" if isinstance(method, TEXT_METHODS) else "caption"
            value = getattr(method, field)
            if str(mode).upper() == "HTML" and isinstance(value, str):
                setattr(method, field, wrap_text(value, self.ids, self.pattern))
        elif not isinstance(method, EditMessageReplyMarkup):
            return
        if isinstance(method.reply_markup, InlineKeyboardMarkup):
            method.reply_markup = convert_markup(method.reply_markup, self.ids, self.pattern)


if __name__ == "__main__":
    from aiogram.types import InlineKeyboardButton

    ids = {"✅": "1", "⚠": "2"}
    t = '<tg-emoji emoji-id="1">✅</tg-emoji>'
    assert wrap_text("✅ ok", ids) == t + " ok"
    assert wrap_text("<code>✅</code> ✅", ids) == "<code>✅</code> " + t
    assert wrap_text("<pre>⚠️</pre>", ids) == "<pre>⚠️</pre>"
    assert wrap_text(t, ids) == t
    assert (
        wrap_text("⚠️ x ⚠", ids)
        == '<tg-emoji emoji-id="2">⚠️</tg-emoji> x <tg-emoji emoji-id="2">⚠</tg-emoji>'
    )
    html = '<a href="https://x/?a=✅">&lt;✅&gt;</a> <b>✅</b>'
    assert wrap_text(html, ids) == f'<a href="https://x/?a=✅">&lt;{t}&gt;</a> <b>{t}</b>'
    assert wrap_text("✅" * 101, ids).count("<tg-emoji") == 100
    assert wrap_text("✅", {}) == "✅"
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Pay", callback_data="a"),
                InlineKeyboardButton(text="⚠️Hi ✅", callback_data="b"),
                InlineKeyboardButton(text="✅ Keep", callback_data="c", icon_custom_emoji_id="9"),
                InlineKeyboardButton(text="Plain", callback_data="d"),
            ]
        ]
    )
    b = convert_markup(kb, ids).inline_keyboard[0]
    assert (b[0].text, b[0].icon_custom_emoji_id) == ("Pay", "1")
    assert (b[1].text, b[1].icon_custom_emoji_id) == ("Hi ✅", "2")
    assert (b[2].text, b[2].icon_custom_emoji_id) == ("✅ Keep", "9")
    assert (b[3].text, b[3].icon_custom_emoji_id) == ("Plain", None)
    assert len(load_ids()) > 0
