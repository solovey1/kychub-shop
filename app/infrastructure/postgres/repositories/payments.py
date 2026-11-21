from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import exists, func, select

from app.application.ports.repositories.payments import PaymentsGateway
from app.domain.enums.ledger import LedgerAccount, LedgerKind, PaymentStatus
from app.domain.ledger import LedgerEntry, Payment
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW
from app.utils.time import datetime_now

UNPAID = (PaymentStatus.created, PaymentStatus.pending, PaymentStatus.partially_paid)


@dataclass
class PaymentsRepository(PaymentsGateway):
    _uow: UoW
    _helper: SqlRepositoryHelper[Payment]

    async def add(self, payment: Payment) -> None:
        await self._uow.flush(payment)

    async def get(self, payment_id: int) -> Payment | None:
        return await self._helper.get_one(Payment.id == payment_id)

    async def get_for_update(self, payment_id: int) -> Payment | None:
        query = (
            select(Payment)
            .where(Payment.id == payment_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        payment: Payment | None = await self._helper.session.scalar(query)
        return payment

    async def pending(self, max_age: timedelta) -> list[Payment]:
        query = (
            select(Payment)
            .where(Payment.status.in_(UNPAID), Payment.created_at >= datetime_now() - max_age)
            .order_by(Payment.id)
        )
        return list(await self._helper.session.scalars(query))

    async def unfulfilled_success(self) -> list[Payment]:
        credited = exists().where(
            LedgerEntry.user_id == Payment.user_id,
            LedgerEntry.account == LedgerAccount.main,
            LedgerEntry.kind == LedgerKind.topup,
            LedgerEntry.ref == func.concat("payment:", Payment.id),
        )
        query = (
            select(Payment)
            .where(Payment.status == PaymentStatus.success, ~credited)
            .order_by(Payment.id)
        )
        return list(await self._helper.session.scalars(query))
