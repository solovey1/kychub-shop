import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.application.errors.base import InsufficientFunds
from app.application.interactors.ledger import LedgerService
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.ledger import LedgerEntry
from app.domain.user import User
from app.infrastructure.postgres.repositories.ledger import LedgerRepository
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper

USER_ID = 910_001


async def _spend(engine: AsyncEngine, amount: str) -> None:
    async with AsyncSession(engine) as s:
        service = LedgerService(LedgerRepository(SqlRepositoryHelper(s, LedgerEntry)))
        await service.post(USER_ID, LedgerAccount.main, -Decimal(amount), LedgerKind.purchase)
        await s.commit()


@pytest.mark.db
async def test_concurrent_spend_only_one_wins(engine: AsyncEngine) -> None:
    try:
        async with AsyncSession(engine) as s:
            s.add(User(id=USER_ID, name="t", language="ru", language_code=None))
            await s.flush()
            service = LedgerService(LedgerRepository(SqlRepositoryHelper(s, LedgerEntry)))
            await service.post(USER_ID, LedgerAccount.main, Decimal("10.00"), LedgerKind.topup)
            await s.commit()

        results = await asyncio.gather(
            _spend(engine, "7.00"), _spend(engine, "7.00"), return_exceptions=True
        )

        assert sum(r is None for r in results) == 1
        assert sum(isinstance(r, InsufficientFunds) for r in results) == 1
        async with AsyncSession(engine) as s:
            repo = LedgerRepository(SqlRepositoryHelper(s, LedgerEntry))
            assert await repo.balance(USER_ID, LedgerAccount.main) == Decimal("3.00")
    finally:
        async with AsyncSession(engine) as s:
            await s.execute(delete(LedgerEntry).where(LedgerEntry.user_id == USER_ID))
            await s.execute(delete(User).where(User.id == USER_ID))
            await s.commit()
