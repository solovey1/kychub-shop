from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.repositories.catalog import CatalogGateway
from app.domain.catalog import Category, Country, Product, ProductVariant, Service, StockUnit
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper


@dataclass
class CatalogRepository(CatalogGateway):
    _helper: SqlRepositoryHelper[Category]

    @property
    def _session(self) -> AsyncSession:
        return self._helper.session

    async def category(self, category_id: int) -> Category | None:
        return await self._helper.get_one(Category.id == category_id, Category.is_active)

    async def children(self, parent_id: int | None) -> list[Category]:
        cond = (
            Category.parent_id.is_(None) if parent_id is None else Category.parent_id == parent_id
        )
        query = (
            select(Category)
            .where(cond, Category.is_active)
            .order_by(Category.position, Category.id)
        )
        return list(await self._session.scalars(query))

    async def products(self, category_id: int, offset: int, limit: int) -> list[Product]:
        query = (
            select(Product)
            .where(Product.category_id == category_id, Product.is_active)
            .order_by(Product.position, Product.id)
            .offset(offset)
            .limit(limit)
        )
        return list(await self._session.scalars(query))

    async def count_products(self, category_id: int) -> int:
        query = select(func.count()).where(Product.category_id == category_id, Product.is_active)
        return int(await self._session.scalar(query) or 0)

    async def product(self, product_id: int) -> Product | None:
        return await self._session.get(Product, product_id)

    async def variants(self, product_id: int) -> list[ProductVariant]:
        query = (
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id, ProductVariant.is_active)
            .order_by(ProductVariant.price, ProductVariant.id)
        )
        return list(await self._session.scalars(query))

    async def variant(self, variant_id: int) -> ProductVariant | None:
        return await self._session.get(ProductVariant, variant_id)

    async def service(self, service_id: int) -> Service | None:
        return await self._session.get(Service, service_id)

    async def service_by_code(self, code: str) -> Service | None:
        service: Service | None = await self._session.scalar(
            select(Service).where(Service.code == code)
        )
        return service

    async def available_stock(self, variant_ids: list[int]) -> dict[int, int]:
        if not variant_ids:
            return {}
        # unlimited units are never marked sold, so they always count as available
        query = (
            select(StockUnit.variant_id, func.count())
            .where(
                StockUnit.variant_id.in_(variant_ids),
                or_(StockUnit.sold_order_id.is_(None), StockUnit.is_unlimited.is_(True)),
            )
            .group_by(StockUnit.variant_id)
        )
        result = dict.fromkeys(variant_ids, 0)
        for variant_id, total in (await self._session.execute(query)).all():
            result[variant_id] = int(total)
        return result

    async def countries(self, codes: list[str]) -> dict[str, Country]:
        if not codes:
            return {}
        query = select(Country).where(Country.code.in_(codes))
        return {c.code: c for c in await self._session.scalars(query)}

    async def min_prices(self, product_ids: list[int]) -> dict[int, Decimal]:
        if not product_ids:
            return {}
        query = (
            select(ProductVariant.product_id, func.min(ProductVariant.price))
            .where(ProductVariant.product_id.in_(product_ids), ProductVariant.is_active)
            .group_by(ProductVariant.product_id)
        )
        return {pid: Decimal(p) for pid, p in (await self._session.execute(query)).all()}
