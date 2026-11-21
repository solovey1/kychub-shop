from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select

from app.application.ports.repositories.ledger import LedgerGateway
from app.domain.enums.ledger import LedgerAccount
from app.domain.ledger import LedgerEntry
from app.domain.user import User
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper


@dataclass
class LedgerRepository(LedgerGateway):
    _helper: SqlRepositoryHelper[LedgerEntry]

    async def lock_user(self, user_id: int) -> None:
        await self._helper.session.execute(
            select(User.id).where(User.id == user_id).with_for_update()
        )

    async def balance(self, user_id: int, account: LedgerAccount) -> Decimal:
        query = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
            LedgerEntry.user_id == user_id, LedgerEntry.account == account
        )
        return Decimal(await self._helper.session.scalar(query) or 0)

    async def add(self, entry: LedgerEntry) -> None:
        await self._helper.add_one(entry)
