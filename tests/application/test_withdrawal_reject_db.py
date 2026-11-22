import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.application.interactors.admin.money import Decided, MoneyAdminInteractor
from app.application.interactors.ledger import LedgerService
from app.domain.audit import AuditLog
from app.domain.enums.ledger import LedgerAccount, LedgerKind, WithdrawalStatus
from app.domain.ledger import LedgerEntry, Withdrawal
from app.domain.user import User
from app.infrastructure.postgres.repositories.admin import AdminRepository
from app.infrastructure.postgres.repositories.ledger import LedgerRepository
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW

EXECUTOR_ID = 910_002
ADMIN_ID = 910_003


async def _reject(engine: AsyncEngine, withdrawal_id: int) -> Decided:
    async with AsyncSession(engine) as s:
        money = MoneyAdminInteractor(
            UoW(s),
            AdminRepository(s),
            LedgerService(LedgerRepository(SqlRepositoryHelper(s, LedgerEntry))),
        )
        return await money.reject(ADMIN_ID, withdrawal_id, "wrong address")


@pytest.mark.db
async def test_reject_twice_returns_the_money_once(engine: AsyncEngine) -> None:
    try:
        async with AsyncSession(engine) as s:
            s.add_all(
                [
                    User(id=EXECUTOR_ID, name="e", language="ru", language_code=None),
                    User(id=ADMIN_ID, name="a", language="ru", language_code=None),
                ]
            )
            await s.flush()
            ledger = LedgerService(LedgerRepository(SqlRepositoryHelper(s, LedgerEntry)))
            available = LedgerAccount.executor_available
            await ledger.post(EXECUTOR_ID, available, Decimal("20.00"), LedgerKind.hold_release)
            w = Withdrawal(executor_id=EXECUTOR_ID, amount=Decimal("20.00"), address="addr")
            s.add(w)
            await s.flush()
            await ledger.post(
                EXECUTOR_ID,
                available,
                Decimal("-20.00"),
                LedgerKind.withdrawal,
                ref=f"withdrawal:{w.id}",
            )
            withdrawal_id = w.id
            await s.commit()

        # two admins press the button at once, then a third time later
        first = await asyncio.gather(
            _reject(engine, withdrawal_id), _reject(engine, withdrawal_id)
        )
        third = await _reject(engine, withdrawal_id)

        assert sorted(d.changed for d in (*first, third)) == [False, False, True]
        async with AsyncSession(engine) as s:
            repo = LedgerRepository(SqlRepositoryHelper(s, LedgerEntry))
            assert await repo.balance(EXECUTOR_ID, LedgerAccount.executor_available) == Decimal(
                "20.00"
            )
            row = await s.get(Withdrawal, withdrawal_id)
            assert row is not None and row.status is WithdrawalStatus.rejected
            refunds = await s.scalar(
                select(func.count()).where(
                    LedgerEntry.user_id == EXECUTOR_ID,
                    LedgerEntry.ref == f"withdrawal:{withdrawal_id}:reject",
                )
            )
            assert refunds == 1
    finally:
        async with AsyncSession(engine) as s:
            await s.execute(delete(AuditLog).where(AuditLog.actor_id == ADMIN_ID))
            await s.execute(delete(LedgerEntry).where(LedgerEntry.user_id == EXECUTOR_ID))
            await s.execute(delete(Withdrawal).where(Withdrawal.executor_id == EXECUTOR_ID))
            await s.execute(delete(User).where(User.id.in_((EXECUTOR_ID, ADMIN_ID))))
            await s.commit()
