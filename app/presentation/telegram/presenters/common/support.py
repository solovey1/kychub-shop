from dataclasses import dataclass

from aiogram_i18n import I18nContext

from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import RenderMode, View


@dataclass(frozen=True)
class SupportPresenter(BasePresenter):
    i18n: I18nContext

    def note(self, key: str, **kwargs: str) -> View:
        """A short answer in a new message, so the conversation above stays where it is."""
        return View(text=self.i18n.get(key, **kwargs), mode=RenderMode.NEW)
