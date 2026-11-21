from dataclasses import dataclass
from html import escape

from aiogram_i18n import I18nContext

from app.application.interactors.executors import CabinetOverview
from app.presentation.telegram.keyboards.executor import cabinet_keyboard
from app.presentation.telegram.presenters.base import BasePresenter
from app.presentation.telegram.view.models import View


@dataclass(frozen=True)
class ExecutorPresenter(BasePresenter):
    i18n: I18nContext

    def cabinet(self, overview: CabinetOverview) -> View:
        i18n = self.i18n
        profile = overview.profile
        if overview.permissions:
            permissions = "\n".join(
                f"{escape(service)}: {', '.join(countries)}"
                for service, countries in overview.permissions.items()
            )
        else:
            permissions = i18n.messages.executor.no_permissions()
        text = i18n.messages.executor.cabinet(
            alias=escape(profile.alias),
            status=i18n.get(f"messages-executor-status_{'on' if profile.is_active else 'off'}"),
            limit=str(profile.max_parallel_orders),
            percent=(
                f"{profile.percent_override}%"
                if profile.percent_override is not None
                else i18n.messages.executor.percent_service()
            ),
            permissions=permissions,
        )
        return View(text=text, reply_markup=cabinet_keyboard(i18n))

    def text(self, key: str, **kwargs: str) -> View:
        return View(text=self.i18n.get(key, **kwargs))
