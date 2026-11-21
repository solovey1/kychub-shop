from dataclasses import dataclass
from typing import Any

from sqlalchemy import select

from app.application.ports.repositories.settings import SettingsGateway
from app.domain.settings import Setting
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper


@dataclass
class SettingsRepository(SettingsGateway):
    _helper: SqlRepositoryHelper[Setting]

    async def get(self, key: str, default: Any) -> Any:
        row = await self._helper.session.scalar(select(Setting).where(Setting.key == key))
        return default if row is None else row.value
