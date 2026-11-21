from dataclasses import dataclass

from sqlalchemy import select

from app.application.ports.repositories.promo import PromoGateway
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.domain.promo import PromoCode, PromoCodeUsage
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW


@dataclass
class PromoRepository(PromoGateway):
    _uow: UoW
    _helper: SqlRepositoryHelper[PromoCode]

    async def get_by_code(self, code: str, lock: bool) -> PromoCode | None:
        query = select(PromoCode).where(PromoCode.code == code)
        if lock:
            query = query.with_for_update()
        promo: PromoCode | None = await self._helper.session.scalar(query)
        return promo

    async def usage_exists(self, promo_id: int, user_id: int) -> bool:
        query = select(PromoCodeUsage.id).where(
            PromoCodeUsage.promo_code_id == promo_id, PromoCodeUsage.user_id == user_id
        )
        return await self._helper.session.scalar(query.limit(1)) is not None

    async def has_purchases(self, user_id: int) -> bool:
        # orders, not ledger rows: a 100%-discount order posts no ledger entry
        query = select(Order.id).where(
            Order.user_id == user_id, Order.status.not_in([OrderStatus.cancelled])
        )
        return await self._helper.session.scalar(query.limit(1)) is not None

    async def add_usage(self, usage: PromoCodeUsage) -> None:
        await self._uow.flush(usage)
