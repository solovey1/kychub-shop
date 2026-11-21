from dataclasses import dataclass

from sqlalchemy import select

from app.application.ports.repositories.balance import BalanceGateway
from app.domain.audit import AuditLog
from app.domain.enums.ledger import LedgerAccount
from app.domain.ledger import LedgerEntry
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW


@dataclass
class BalanceRepository(BalanceGateway):
    _uow: UoW
    _helper: SqlRepositoryHelper[LedgerEntry]

    async def history(self, user_id: int, limit: int) -> list[LedgerEntry]:
        query = (
            select(LedgerEntry)
            .where(LedgerEntry.user_id == user_id, LedgerEntry.account == LedgerAccount.main)
            .order_by(LedgerEntry.id.desc())
            .limit(limit)
        )
        return list(await self._helper.session.scalars(query))

    async def add_audit(self, record: AuditLog) -> None:
        await self._uow.flush(record)
