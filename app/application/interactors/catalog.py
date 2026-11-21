from dataclasses import dataclass
from decimal import Decimal

from app.application.interactors.base import BaseInteractor
from app.application.ports.repositories.catalog import CatalogGateway
from app.domain.catalog import Category, Country, Product, ProductVariant

PAGE_SIZE = 8
INLINE_PAGE_SIZE = 20


@dataclass(frozen=True)
class CategoryPage:
    category: Category | None  # None = catalog root
    children: list[Category]
    products: list[Product]
    page: int
    pages: int


@dataclass(frozen=True)
class VariantView:
    variant: ProductVariant
    in_stock: bool
    country: Country | None


@dataclass(frozen=True)
class ProductCard:
    product: Product
    variants: list[VariantView]


@dataclass(frozen=True)
class InlinePage:
    items: list[tuple[Product, Decimal]]
    next_offset: str  # empty string = no more pages


@dataclass(frozen=True)
class CatalogInteractor(BaseInteractor):
    gateway: CatalogGateway

    async def category(self, category_id: int, page: int) -> CategoryPage | None:
        category: Category | None = None
        if category_id:
            category = await self.gateway.category(category_id)
            if category is None:
                return None
        children = await self.gateway.children(category_id or None)
        if category is None:
            return CategoryPage(None, children, [], 0, 1)
        total = await self.gateway.count_products(category.id)
        pages = max(1, -(-total // PAGE_SIZE))
        page = min(max(page, 0), pages - 1)
        products = await self.gateway.products(category.id, page * PAGE_SIZE, PAGE_SIZE)
        return CategoryPage(category, children, products, page, pages)

    async def product(self, product_id: int) -> ProductCard | None:
        product = await self.gateway.product(product_id)
        if product is None or not product.is_active:
            return None
        variants = await self.gateway.variants(product.id)
        stock: dict[int, int] = {}
        if product.fulfillment_type == "stock":
            stock = await self.gateway.available_stock([v.id for v in variants])
        countries = await self.gateway.countries(
            [v.country_code for v in variants if v.country_code]
        )
        views = [
            VariantView(
                variant=v,
                in_stock=product.fulfillment_type != "stock" or stock.get(v.id, 0) > 0,
                country=countries.get(v.country_code) if v.country_code else None,
            )
            for v in variants
        ]
        return ProductCard(product, views)

    async def search(self, text: str, locale: str, offset: int) -> InlinePage:
        rows = await self.gateway.search(text, locale, offset, INLINE_PAGE_SIZE + 1)
        more = len(rows) > INLINE_PAGE_SIZE
        return InlinePage(rows[:INLINE_PAGE_SIZE], str(offset + INLINE_PAGE_SIZE) if more else "")
