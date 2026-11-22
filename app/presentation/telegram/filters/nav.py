from aiogram.enums import ChatType
from aiogram.filters import Filter
from aiogram.types import Message
from aiogram_i18n.cores import FluentRuntimeCore
from dishka import AsyncContainer

from app.presentation.telegram.keyboards.menu import NAV_SECTIONS


class NavTap(Filter):
    """A tap on a bottom-keyboard button, by the label in any locale.

    Filters run before the i18n middleware, so the core comes from the dishka container."""

    async def __call__(
        self, message: Message, dishka_container: AsyncContainer
    ) -> bool | dict[str, str]:
        if not message.text or message.chat.type != ChatType.PRIVATE:
            return False
        core = await dishka_container.get(FluentRuntimeCore)
        for section in (s for row in NAV_SECTIONS for s in row):
            for locale in core.available_locales:
                if core.get(f"buttons-nav_{section}", locale) == message.text:
                    return {"section": section}
        return False
