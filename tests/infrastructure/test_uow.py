import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.user import User
from app.infrastructure.postgres.uow import UoW


@pytest.mark.db
async def test_flush_makes_row_visible_in_same_session(session: AsyncSession) -> None:
    uow = UoW(session)
    await uow.flush(User(id=1, name="a", language="ru", language_code=None))
    assert await session.get(User, 1) is not None
