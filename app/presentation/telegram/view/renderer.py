from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from aiogram.types import BufferedInputFile, InlineQuery, InlineQueryResultArticle

from app.application.ports.telegram.messages_helper import MessageHelper
from app.presentation.telegram.view.models import RenderMode, View


@dataclass
class Renderer:
    helper: MessageHelper

    async def apply(self, view: View) -> Any:
        if view.mode is RenderMode.NONE or view.text is None:
            return None

        if view.mode is RenderMode.NEW:
            return await self.helper.send_new_message(
                chat_id=view.chat_id,
                message_id=view.message_id,
                text=view.text,
                reply_markup=view.reply_markup,
                delete=view.delete,
                **(view.kwargs or {}),
            )

        if view.mode is RenderMode.CURRENT:
            new, _ = await self.helper.answer_current_message(
                text=view.text, reply_markup=view.reply_markup, **(view.kwargs or {})
            )
            return new

        return await self.helper.answer(
            chat_id=view.chat_id,
            message_id=view.message_id,
            text=view.text,
            reply_markup=view.reply_markup,
            edit=view.edit,
            reply=view.reply,
            delete=view.delete,
            force_edit=view.force_edit,
            **(view.kwargs or {}),
        )

    async def answer_inline(
        self, query: InlineQuery, results: list[InlineQueryResultArticle], next_offset: str
    ) -> None:
        await query.answer(
            results=results,  # type: ignore[arg-type]
            cache_time=5,
            is_personal=True,
            next_offset=next_offset,
        )

    async def send_file(self, filename: str, data: bytes, caption: str | None = None) -> None:
        await self.helper.bot.send_document(
            chat_id=self.helper.get_chat_id(),
            document=BufferedInputFile(data, filename=filename),
            caption=caption,
        )
