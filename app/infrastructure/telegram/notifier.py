import logging
from dataclasses import dataclass
from typing import Any, Callable, Final

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.types import BufferedInputFile, InlineKeyboardMarkup, Message
from aiogram_i18n.cores import FluentRuntimeCore

from app.application.ports.repositories.executors import ExecutorsGateway
from app.application.ports.repositories.users import UsersGateway
from app.const import DEFAULT_LOCALE

logger: Final = logging.getLogger(__name__)

Translate = Callable[..., str]
# a ftl key, or a function that renders the whole text from a translator and a locale
Text = str | Callable[[Translate, str], str]
# a ready keyboard, or a function that builds one with the recipient's translator
Markup = InlineKeyboardMarkup | Callable[[Translate], InlineKeyboardMarkup]


@dataclass(frozen=True)
class Notifier:
    """Messages to users in their own language. Telegram errors are logged and swallowed."""

    bot: Bot
    core: FluentRuntimeCore
    users: UsersGateway
    executors: ExecutorsGateway

    async def _locale(self, user_id: int) -> str:
        user = await self.users.get(user_id)
        return user.language if user else DEFAULT_LOCALE

    def _tr(self, locale: str) -> Translate:
        return lambda key, **kw: self.core.get(key, locale, **kw)

    def _render(self, locale: str, key: Text, kwargs: dict[str, Any]) -> str:
        if callable(key):
            return key(self._tr(locale), locale)
        return self.core.get(key, locale, **kwargs)

    def _markup(self, locale: str, markup: Markup | None) -> InlineKeyboardMarkup | None:
        return markup(self._tr(locale)) if callable(markup) else markup

    async def send(
        self, user_id: int, key: Text, reply_markup: Markup | None = None, **kwargs: Any
    ) -> Message | None:
        try:
            locale = await self._locale(user_id)
            return await self.bot.send_message(
                user_id,
                self._render(locale, key, kwargs),
                reply_markup=self._markup(locale, reply_markup),
            )
        except TelegramAPIError:
            logger.info("could not notify user %s", user_id)
        except Exception:
            logger.exception("notification to user %s failed", user_id)
        return None

    async def edit(
        self,
        chat_id: int,
        message_id: int,
        key: Text,
        reply_markup: Markup | None = None,
        **kwargs: Any,
    ) -> bool:
        """Replaces the text; the keyboard is removed unless a new one is given."""
        try:
            locale = await self._locale(chat_id)
            await self.bot.edit_message_text(
                self._render(locale, key, kwargs),
                chat_id=chat_id,
                message_id=message_id,
                reply_markup=self._markup(locale, reply_markup),
            )
            return True
        except TelegramAPIError:
            logger.info("could not edit message %s in chat %s", message_id, chat_id)
        except Exception:
            logger.exception("editing message %s in chat %s failed", message_id, chat_id)
        return False

    async def staff(self, key: Text, reply_markup: Markup | None = None, **kwargs: Any) -> None:
        """Every admin and manager, in private."""
        for user_id in await self.executors.staff_ids():
            await self.send(user_id, key, reply_markup, **kwargs)

    async def send_file(self, user_id: int, filename: str, data: bytes) -> None:
        try:
            await self.bot.send_document(user_id, BufferedInputFile(data, filename=filename))
        except TelegramAPIError:
            logger.info("could not send a file to user %s", user_id)

    async def send_media(self, user_id: int, file_id: str) -> None:
        """A stored Telegram file id: tried as a document, then as a photo."""
        try:
            try:
                await self.bot.send_document(user_id, file_id)
            except TelegramBadRequest:
                await self.bot.send_photo(user_id, file_id)
        except TelegramAPIError:
            logger.info("could not send a file to user %s", user_id)
