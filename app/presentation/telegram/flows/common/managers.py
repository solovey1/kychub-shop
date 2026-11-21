from dataclasses import dataclass

from app.application.errors.shop import ManagerExists, ManagerNotFound
from app.application.interactors.managers import ManagerAdminInteractor
from app.domain.user import User
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.executor.cabinet import ExecutorPresenter
from app.presentation.telegram.view.renderer import Renderer


@dataclass(frozen=True)
class ManagerAdminFlow(BaseFlow):
    user: User
    interactor: ManagerAdminInteractor
    presenter: ExecutorPresenter
    renderer: Renderer

    async def run(self, args: str | None, *, add: bool) -> None:
        parts = (args or "").split()
        if len(parts) != 1 or not parts[0].isdigit():
            return await self._reply("usage")
        tg_id = int(parts[0])
        try:
            if add:
                await self.interactor.add(self.user.id, tg_id)
            else:
                await self.interactor.remove(self.user.id, tg_id)
        except ManagerExists:
            return await self._reply("err_exists")
        except ManagerNotFound:
            return await self._reply("err_not_found")
        await self._reply("done")

    async def _reply(self, key: str) -> None:
        await self.renderer.apply(self.presenter.text(f"messages-manager-{key}"))
