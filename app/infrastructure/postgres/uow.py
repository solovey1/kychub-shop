from dataclasses import dataclass

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.base import Base
from app.utils.codes import new_code


@dataclass(slots=True)
class UoW:
    session: AsyncSession

    async def commit(self, *instances: Base) -> None:
        self.session.add_all(instances)
        await self.session.commit()

    async def flush(self, *instances: Base) -> None:
        self.session.add_all(instances)
        await self.session.flush()

    async def flush_coded(self, instance: Base) -> None:
        """Insert a row with a public `code`; a taken code is retried (inside a savepoint, so the
        transaction survives)."""
        for attempt in range(5):
            setattr(instance, "code", new_code())
            try:
                async with self.session.begin_nested():
                    self.session.add(instance)
                    await self.session.flush()
                return
            except IntegrityError as e:
                if "_code_key" not in str(e.orig) or attempt == 4:
                    raise

    async def rollback(self) -> None:
        await self.session.rollback()

    async def merge(self, *instances: Base) -> None:
        for instance in instances:
            await self.session.merge(instance)

    async def delete(self, *instances: Base) -> None:
        for instance in instances:
            await self.session.delete(instance)
        await self.session.commit()
