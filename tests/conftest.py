import os
from collections.abc import AsyncIterator

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine

from app.domain.base import Base

DSN = os.environ.get("TEST_POSTGRES_DSN")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if DSN:
        return
    skip = pytest.mark.skip(reason="TEST_POSTGRES_DSN is not set")
    for item in items:
        if "db" in item.keywords:
            item.add_marker(skip)


@pytest_asyncio.fixture(scope="session", loop_scope="session")
async def engine() -> AsyncIterator[AsyncEngine]:
    assert DSN
    eng = create_async_engine(DSN)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture(loop_scope="session")
async def session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    async with engine.connect() as conn:
        trans = await conn.begin()
        async with AsyncSession(bind=conn, join_transaction_mode="create_savepoint") as s:
            yield s
        await trans.rollback()
