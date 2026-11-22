from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.repositories.admin import AdminGateway
from app.domain.audit import AuditLog
from app.domain.base import Base
from app.domain.catalog import (
    Category,
    Country,
    Product,
    ProductVariant,
    Service,
    StockUnit,
)
from app.domain.executor import ExecutorPermission
from app.domain.order import Order
from app.domain.promo import PromoCode


@dataclass
class AdminRepository(AdminGateway):
    _session: AsyncSession

    async def get[T: Base](self, model: type[T], pk: object) -> T | None:
        return await self._session.get(model, pk)

    async def lock[T: Base](self, model: type[T], pk: object) -> T | None:
        return await self._session.get(model, pk, with_for_update=True, populate_existing=True)

    async def add(self, *items: Base) -> None:
        self._session.add_all(items)
        await self._session.flush()

    async def delete(self, item: Base) -> None:
        await self._session.delete(item)
        await self._session.flush()

    async def flush(self) -> None:
        await self._session.flush()

    async def audit(
        self, actor_id: int, action: str, target: str | None, payload: dict[str, Any]
    ) -> None:
        self._session.add(
            AuditLog(actor_id=actor_id, action=action, target=target, payload=payload)
        )
        await self._session.flush()

    # --- catalog
    async def categories(self) -> list[Category]:
        query = select(Category).order_by(Category.position, Category.id)
        return list(await self._session.scalars(query))

    async def category_counts(self) -> dict[int, tuple[int, int]]:
        counts: dict[int, tuple[int, int]] = {}
        children = (
            select(Category.parent_id, func.count())
            .where(Category.parent_id.is_not(None))
            .group_by(Category.parent_id)
        )
        for pid, n in (await self._session.execute(children)).all():
            counts[int(pid)] = (int(n), 0)
        products = select(Product.category_id, func.count()).group_by(Product.category_id)
        for cid, n in (await self._session.execute(products)).all():
            counts[int(cid)] = (counts.get(int(cid), (0, 0))[0], int(n))
        return counts

    async def products_of(self, category_id: int) -> list[tuple[Product, int, Decimal | None]]:
        query = (
            select(
                Product,
                func.count(ProductVariant.id),
                func.min(ProductVariant.price).filter(ProductVariant.is_active),
            )
            .outerjoin(ProductVariant, ProductVariant.product_id == Product.id)
            .where(Product.category_id == category_id)
            .group_by(Product.id)
            .order_by(Product.position, Product.id)
        )
        return [
            (p, int(n), None if price is None else Decimal(price))
            for p, n, price in (await self._session.execute(query)).all()
        ]

    async def variants_of(self, product_id: int) -> list[ProductVariant]:
        query = (
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.id)
        )
        return list(await self._session.scalars(query))

    async def free_stock(self, variant_ids: list[int]) -> dict[int, int]:
        if not variant_ids:
            return {}
        query = (
            select(StockUnit.variant_id, func.count())
            .where(
                StockUnit.variant_id.in_(variant_ids),
                StockUnit.sold_order_id.is_(None),
                StockUnit.is_unlimited.is_(False),
            )
            .group_by(StockUnit.variant_id)
        )
        found = {int(v): int(n) for v, n in (await self._session.execute(query)).all()}
        return {v: found.get(v, 0) for v in variant_ids}

    async def product_used(self, product_id: int) -> str | None:
        ordered = select(
            exists(
                select(Order.id)
                .join(ProductVariant, ProductVariant.id == Order.variant_id)
                .where(ProductVariant.product_id == product_id)
            )
        )
        if await self._session.scalar(ordered):
            return "has_orders"
        promo = select(exists(select(PromoCode.id).where(PromoCode.product_id == product_id)))
        return "has_promo" if await self._session.scalar(promo) else None

    async def variant_has_orders(self, variant_id: int) -> bool:
        query = select(exists(select(Order.id).where(Order.variant_id == variant_id)))
        return bool(await self._session.scalar(query))

    async def services(self) -> list[Service]:
        return list(await self._session.scalars(select(Service).order_by(Service.id)))

    async def service_products(self, service_id: int) -> int:
        query = select(func.count()).where(Product.service_id == service_id)
        return int(await self._session.scalar(query) or 0)

    async def service_by_code(self, code: str) -> Service | None:
        service: Service | None = await self._session.scalar(
            select(Service).where(Service.code == code)
        )
        return service

    async def countries(self) -> list[Country]:
        return list(await self._session.scalars(select(Country).order_by(Country.code)))

    async def country_used(self, code: str) -> bool:
        query = select(
            exists(select(ProductVariant.id).where(ProductVariant.country_code == code))
            | exists(
                select(ExecutorPermission.executor_id).where(
                    ExecutorPermission.country_code == code
                )
            )
        )
        return bool(await self._session.scalar(query))

    async def stock_recent(self, variant_id: int, limit: int) -> list[StockUnit]:
        query = (
            select(StockUnit)
            .where(
                StockUnit.variant_id == variant_id,
                StockUnit.sold_order_id.is_(None),
                StockUnit.is_unlimited.is_(False),
            )
            .order_by(StockUnit.id.desc())
            .limit(limit)
        )
        return list(await self._session.scalars(query))

    async def stock_unlimited(self, variant_id: int) -> StockUnit | None:
        query = select(StockUnit).where(
            and_(StockUnit.variant_id == variant_id, StockUnit.is_unlimited.is_(True))
        )
        unit: StockUnit | None = await self._session.scalar(query.limit(1))
        return unit

    async def stock_payloads(self, variant_id: int, payloads: list[str]) -> set[str]:
        if not payloads:
            return set()
        query = select(StockUnit.payload).where(
            StockUnit.variant_id == variant_id,
            StockUnit.sold_order_id.is_(None),
            StockUnit.payload.in_(payloads),
        )
        return set(await self._session.scalars(query))
