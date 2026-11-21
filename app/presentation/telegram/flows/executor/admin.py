from dataclasses import dataclass
from typing import Awaitable, Final

from app.application.errors.base import AppError
from app.application.errors.shop import (
    AliasTaken,
    ExecutorExists,
    ExecutorNotFound,
    InvalidInput,
    UnknownCountry,
    UnknownService,
)
from app.application.interactors.executors import ExecutorAdminInteractor
from app.domain.user import User
from app.presentation.telegram.flows.base import BaseFlow
from app.presentation.telegram.presenters.executor.cabinet import ExecutorPresenter
from app.presentation.telegram.view.renderer import Renderer

_ERRORS: Final[dict[type[AppError], str]] = {
    AliasTaken: "alias_taken",
    ExecutorExists: "exists",
    ExecutorNotFound: "not_found",
    UnknownService: "service",
    UnknownCountry: "country",
    InvalidInput: "input",
}


@dataclass(frozen=True)
class ExecutorAdminFlow(BaseFlow):
    user: User
    interactor: ExecutorAdminInteractor
    presenter: ExecutorPresenter
    renderer: Renderer

    async def _reply(self, key: str) -> None:
        await self.renderer.apply(self.presenter.text(f"messages-executor-{key}"))

    async def _run(self, call: Awaitable[object]) -> None:
        try:
            await call
        except AppError as e:
            await self._reply(f"err_{_ERRORS.get(type(e), 'input')}")
        else:
            await self._reply("admin_done")

    async def add(self, args: str | None) -> None:
        parts = (args or "").split()
        if len(parts) != 2 or not parts[0].isdigit():
            return await self._reply("usage_add")
        await self._run(self.interactor.register(self.user.id, int(parts[0]), parts[1]))

    async def perm(self, args: str | None) -> None:
        parts = (args or "").split()
        if len(parts) != 3 or not parts[0].isdigit():
            return await self._reply("usage_perm")
        countries = [] if parts[2] == "-" else parts[2].split(",")
        await self._run(
            self.interactor.set_permissions(self.user.id, int(parts[0]), parts[1], countries)
        )

    async def switch(self, args: str | None, active: bool) -> None:
        parts = (args or "").split()
        if len(parts) != 1 or not parts[0].isdigit():
            return await self._reply("usage_switch")
        await self._run(self.interactor.set_active(self.user.id, int(parts[0]), active))

    async def limits(self, args: str | None) -> None:
        parts = (args or "").split()
        if len(parts) not in (2, 3) or not all(p.isdigit() for p in parts):
            return await self._reply("usage_limits")
        percent = int(parts[2]) if len(parts) == 3 else None
        await self._run(
            self.interactor.set_limits(self.user.id, int(parts[0]), int(parts[1]), percent)
        )
