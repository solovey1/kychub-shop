from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any

from app.application.errors.shop import InvalidField, NotFound
from app.application.interactors.base import BaseInteractor
from app.application.ports.repositories.admin import AdminGateway
from app.application.ports.uow import UnitOfWork
from app.domain.base import Base

LOCALES = ("ru", "en", "uk")


@dataclass(frozen=True)
class AdminInteractor(BaseInteractor):
    uow: UnitOfWork
    db: AdminGateway

    @asynccontextmanager
    async def tx(self) -> AsyncIterator[None]:
        """One transaction: whatever happens inside commits together with its audit rows."""
        try:
            yield
            await self.uow.commit()
        except BaseException:
            await self.uow.rollback()
            raise

    async def need[T: Base](self, model: type[T], pk: object, lock: bool = True) -> T:
        row = await (self.db.lock if lock else self.db.get)(model, pk)
        if row is None:
            raise NotFound(f"{model.__name__} {pk}")
        return row


def i18n(value: dict[str, str] | None, field: str, *, required: bool = True) -> dict[str, Any]:
    """Cleans a {ru, en, uk} text: known locales only, blanks dropped, `ru` required."""
    clean = {k: v.strip() for k, v in (value or {}).items() if k in LOCALES and v.strip()}
    if required and "ru" not in clean:
        raise InvalidField(field, "ru is required")
    if any(len(v) > 4000 for v in clean.values()):
        raise InvalidField(field, "text is too long")
    return clean


def _json(value: object) -> object:
    if isinstance(value, (dict, list)):
        return "updated"  # schemas and texts are too big for a log line
    return value if value is None or isinstance(value, (bool, int, str)) else str(value)


def apply(item: Base, patch: dict[str, Any]) -> dict[str, object]:
    """Sets the changed attributes and returns {name: [old, new]} for the audit log."""
    diff: dict[str, object] = {}
    for name, new in patch.items():
        old = getattr(item, name)
        if old != new:
            diff[name] = [_json(old), _json(new)]
            setattr(item, name, new)
    return diff
