from aiogram.enums import ChatType
from aiogram.filters import Filter
from aiogram.types import Message
from aiogram_i18n import I18nContext

from app.presentation.telegram.keyboards.menu import NAV_SECTIONS


class NavTap(Filter):
    """A tap on a bottom-keyboard button, by the label in any locale."""

    async def __call__(self, message: Message, i18n: I18nContext) -> bool | dict[str, str]:
        if not message.text or message.chat.type != ChatType.PRIVATE:
            return False
        for section in (s for row in NAV_SECTIONS for s in row):
            for locale in i18n.core.available_locales:
                if i18n.get(f"buttons-nav_{section}", locale) == message.text:
                    return {"section": section}
        return False
