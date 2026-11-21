from dataclasses import dataclass
from typing import Any

from app.application.interactors.executors import ExecutorCabinetInteractor
from app.domain.user import User
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.executor.cabinet import ExecutorPresenter
from app.presentation.telegram.view.renderer import Renderer


@dataclass(frozen=True)
class CabinetFlow(BaseFlow):
    user: User
    interactor: ExecutorCabinetInteractor
    presenter: ExecutorPresenter
    renderer: Renderer

    async def show(self) -> Any:
        overview = await self.interactor.overview(self.user.id)
        if overview is None:
            return await self.renderer.apply(self.presenter.text("messages-executor-no_profile"))
        return await self.renderer.apply(self.presenter.cabinet(overview))
