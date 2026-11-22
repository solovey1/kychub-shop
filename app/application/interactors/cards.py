from dataclasses import dataclass
from decimal import Decimal

from app.application.cards import CardField, OrderCard
from app.application.interactors.base import BaseInteractor
from app.application.models.form_schema import FieldType, FormSchema
from app.application.ports.repositories.catalog import CatalogGateway
from app.application.ports.repositories.executors import ExecutorsGateway
from app.domain.catalog import Product, ProductVariant, Service
from app.domain.executor import ExecutorProfile
from app.domain.money import money, percent_of
from app.domain.order import Order


@dataclass(frozen=True)
class OrderContext:
    variant: ProductVariant
    product: Product
    service: Service | None


async def load_context(catalog: CatalogGateway, order: Order) -> OrderContext | None:
    variant = await catalog.variant(order.variant_id)
    product = await catalog.product(variant.product_id) if variant else None
    if variant is None or product is None:
        return None
    service = await catalog.service(product.service_id) if product.service_id else None
    return OrderContext(variant, product, service)


def percent_for(profile: ExecutorProfile | None, service: Service | None) -> int:
    if profile is not None and profile.percent_override is not None:
        return profile.percent_override
    return service.executor_percent if service else 0


def earning_for(order: Order, percent: int) -> Decimal:
    """Share of what the buyer actually paid (after the discount)."""
    return money(percent_of(order.price - order.discount, Decimal(percent)))


@dataclass(frozen=True)
class CardBuilder(BaseInteractor):
    catalog: CatalogGateway
    executors: ExecutorsGateway

    async def build(
        self, order: Order, executor_id: int | None, *, hide_private: bool = True
    ) -> OrderCard:
        """`hide_private=True`: without the fields hidden from executors."""
        ctx = await load_context(self.catalog, order)
        if ctx is None:
            raise LookupError(f"order {order.id}: product is gone")
        schema = FormSchema.model_validate(ctx.product.input_schema or {"fields": []})
        fields = [
            CardField(f.label, order.input_data[f.key], f.type is FieldType.file)
            for f in schema.fields
            if order.input_data.get(f.key) and not (hide_private and f.hidden_from_executor)
        ]
        profile = await self.executors.get_profile(executor_id) if executor_id else None
        country_code = ctx.variant.country_code
        country = (
            (await self.catalog.countries([country_code])).get(country_code)
            if country_code
            else None
        )
        return OrderCard(
            order_id=order.id,
            code=order.code,
            product=ctx.product.title_i18n,
            country_code=country_code,
            country_title=country.title_i18n if country else None,
            paid=order.price - order.discount,
            earning=earning_for(order, percent_for(profile, ctx.service)),
            deadline_minutes=ctx.service.deadline_minutes if ctx.service else 0,
            fields=fields,
        )
