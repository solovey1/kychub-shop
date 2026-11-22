import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Final

from pydantic import ValidationError

from app.application.errors.shop import Conflict, InvalidAmount, InvalidField, UnknownCountry
from app.application.fulfillment import FulfillmentRegistry
from app.application.interactors.admin.base import AdminInteractor, apply, i18n
from app.application.interactors.balance import parse_money
from app.application.models.form_schema import FormSchema
from app.domain.catalog import (
    Category,
    Country,
    Product,
    ProductVariant,
    Service,
    StockUnit,
)
from app.domain.enums.catalog import AssignMode

STOCK_RECENT: Final = 50
STOCK_MAX_LINES: Final = 5000
PAYLOAD_MAX: Final = 4096
MAX_PRICE: Final = Decimal("1000000")
_SERVICE_CODE: Final = re.compile(r"[a-z0-9_]{2,32}")


@dataclass(frozen=True)
class ProductDetail:
    product: Product
    variants: list[ProductVariant]
    stock: dict[int, int]  # variant id -> unsold limited units (stock products only)
    used: str | None  # why it cannot be deleted


@dataclass(frozen=True)
class StockView:
    free: int
    unlimited: StockUnit | None
    recent: list[StockUnit]


@dataclass(frozen=True)
class StockImport:
    added: int
    duplicates: int


def _schema(value: dict[str, Any] | None, field: str) -> dict[str, Any]:
    """The form constructor result, checked by FormSchema; `{}` when it has no fields."""
    if not value or not value.get("fields"):
        return {}
    try:
        schema = FormSchema.model_validate(value)
    except ValidationError as e:
        first = e.errors()[0]
        where = ".".join(str(p) for p in first["loc"])
        raise InvalidField(field, f"{where}: {first['msg']}".strip(": ")) from e
    return schema.model_dump(mode="json", exclude_none=True)


def _price(raw: str) -> Decimal:
    try:
        price = parse_money(raw)
    except InvalidAmount as e:
        raise InvalidField("price", "at most two decimals") from e
    if price < 0 or price > MAX_PRICE:
        raise InvalidField("price", "out of range")
    return price


def _swap(items: list[Any], item_id: int, direction: str) -> None:
    """Renumbers the siblings 0..n and moves one step up or down."""
    for i, item in enumerate(items):
        item.position = i
    at = next(i for i, item in enumerate(items) if item.id == item_id)
    to = at - 1 if direction == "up" else at + 1
    if 0 <= to < len(items):
        items[at].position, items[to].position = to, at


@dataclass(frozen=True)
class CatalogAdminInteractor(AdminInteractor):
    registry: FulfillmentRegistry

    # --- categories
    async def categories(self) -> list[tuple[Category, int, int]]:
        counts = await self.db.category_counts()
        return [(c, *counts.get(c.id, (0, 0))) for c in await self.db.categories()]

    async def create_category(
        self, actor: int, parent_id: int | None, title: dict[str, str], is_active: bool
    ) -> Category:
        async with self.tx():
            if parent_id is not None:
                await self.need(Category, parent_id, lock=False)
            siblings = [c for c in await self.db.categories() if c.parent_id == parent_id]
            category = Category(
                parent_id=parent_id,
                title_i18n=i18n(title, "title"),
                position=len(siblings),
                is_active=is_active,
            )
            await self.db.add(category)
            await self.db.audit(actor, "category.create", f"category:{category.id}", {})
        return category

    async def update_category(
        self, actor: int, category_id: int, patch: dict[str, Any]
    ) -> Category:
        async with self.tx():
            category = await self.need(Category, category_id)
            changes: dict[str, Any] = {}
            if "title" in patch:
                changes["title_i18n"] = i18n(patch["title"], "title")
            if "is_active" in patch:
                changes["is_active"] = patch["is_active"]
            if "parent_id" in patch and patch["parent_id"] != category.parent_id:
                parent_id = patch["parent_id"]
                if parent_id is not None:
                    await self.need(Category, parent_id, lock=False)
                    parents = {c.id: c.parent_id for c in await self.db.categories()}
                    up: int | None = parent_id
                    while up is not None:  # the new parent must not sit below the category
                        if up == category_id:
                            raise Conflict("cycle")
                        up = parents.get(up)
                changes["parent_id"] = parent_id
                changes["position"] = len(
                    [c for c in await self.db.categories() if c.parent_id == parent_id]
                )
            diff = apply(category, changes)
            await self.db.audit(actor, "category.update", f"category:{category_id}", diff)
        return category

    async def move_category(self, actor: int, category_id: int, direction: str) -> None:
        async with self.tx():
            category = await self.need(Category, category_id)
            siblings = [c for c in await self.db.categories() if c.parent_id == category.parent_id]
            _swap(siblings, category_id, direction)
            await self.db.audit(
                actor, "category.move", f"category:{category_id}", {"direction": direction}
            )

    async def delete_category(self, actor: int, category_id: int) -> None:
        async with self.tx():
            category = await self.need(Category, category_id)
            children, products = (await self.db.category_counts()).get(category_id, (0, 0))
            if children:
                raise Conflict("has_children")
            if products:
                raise Conflict("has_products")
            await self.db.delete(category)
            await self.db.audit(actor, "category.delete", f"category:{category_id}", {})

    # --- products
    async def products(self, category_id: int) -> list[tuple[Product, int, Decimal | None]]:
        await self.need(Category, category_id, lock=False)
        return await self.db.products_of(category_id)

    async def product(self, product_id: int) -> ProductDetail:
        product = await self.need(Product, product_id, lock=False)
        variants = await self.db.variants_of(product_id)
        stock = (
            await self.db.free_stock([v.id for v in variants])
            if product.fulfillment_type == "stock"
            else {}
        )
        return ProductDetail(product, variants, stock, await self.db.product_used(product_id))

    async def _checked(self, fields: dict[str, Any]) -> dict[str, Any]:
        """Column values of the product fields that were sent, validated."""
        out: dict[str, Any] = {}
        if "title" in fields:
            out["title_i18n"] = i18n(fields["title"], "title")
        if "description" in fields:
            out["description_i18n"] = i18n(fields["description"], "description", required=False)
        for name in ("input_schema", "result_schema"):
            if name in fields:
                out[name] = _schema(fields[name], name)
        for name in ("is_active", "service_id", "category_id"):
            if name in fields:
                out[name] = fields[name]
        if out.get("service_id") is not None:
            await self.need(Service, out["service_id"], lock=False)
        if out.get("category_id") is not None:
            await self.need(Category, out["category_id"], lock=False)
        return out

    def _fulfillment(self, kind: str, config: dict[str, Any]) -> None:
        handler = self.registry.get(kind)
        if handler is None:
            raise InvalidField("fulfillment_type", "unknown type")
        try:
            handler.validate_config(config)
        except ValueError as e:
            raise InvalidField("fulfillment_config", str(e)) from e

    async def create_product(self, actor: int, fields: dict[str, Any]) -> Product:
        async with self.tx():
            values = await self._checked(fields)
            kind, config = fields["fulfillment_type"], fields.get("fulfillment_config") or {}
            self._fulfillment(kind, config)
            if kind == "executor" and values.get("service_id") is None:
                raise InvalidField("service_id", "an executor product needs a service")
            position = len(await self.db.products_of(values["category_id"]))
            product = Product(
                fulfillment_type=kind, fulfillment_config=config, position=position, **values
            )
            await self.db.add(product)
            await self.db.audit(actor, "product.create", f"product:{product.id}", {"type": kind})
        return product

    async def update_product(self, actor: int, product_id: int, fields: dict[str, Any]) -> Product:
        async with self.tx():
            product = await self.need(Product, product_id)
            values = await self._checked(fields)
            kind = fields.get("fulfillment_type", product.fulfillment_type)
            config = fields.get("fulfillment_config", product.fulfillment_config) or {}
            self._fulfillment(kind, config)
            if kind != product.fulfillment_type and await self.db.product_used(product_id):
                raise Conflict("type_locked")
            service_id = values.get("service_id", product.service_id)
            if kind == "executor" and service_id is None:
                raise InvalidField("service_id", "an executor product needs a service")
            values |= {"fulfillment_type": kind, "fulfillment_config": config}
            if values.get("category_id", product.category_id) != product.category_id:
                values["position"] = len(await self.db.products_of(values["category_id"]))
            diff = apply(product, values)
            await self.db.audit(actor, "product.update", f"product:{product_id}", diff)
        return product

    async def move_product(self, actor: int, product_id: int, direction: str) -> None:
        async with self.tx():
            product = await self.need(Product, product_id)
            siblings = [p for p, _, _ in await self.db.products_of(product.category_id)]
            _swap(siblings, product_id, direction)
            await self.db.audit(
                actor, "product.move", f"product:{product_id}", {"direction": direction}
            )

    async def delete_product(self, actor: int, product_id: int) -> None:
        async with self.tx():
            product = await self.need(Product, product_id)
            if (why := await self.db.product_used(product_id)) is not None:
                raise Conflict(why)
            await self.db.delete(product)
            await self.db.audit(actor, "product.delete", f"product:{product_id}", {})

    # --- variants
    async def _variant_values(self, fields: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if "price" in fields:
            out["price"] = _price(fields["price"])
        if "title" in fields:
            out["title_i18n"] = i18n(fields["title"], "title", required=False) or None
        if "is_active" in fields:
            out["is_active"] = fields["is_active"]
        if "country_code" in fields:
            code = (fields["country_code"] or "").strip().upper() or None
            if code is not None and await self.db.get(Country, code) is None:
                raise UnknownCountry(code)
            out["country_code"] = code
        return out

    async def create_variant(
        self, actor: int, product_id: int, fields: dict[str, Any]
    ) -> ProductVariant:
        async with self.tx():
            await self.need(Product, product_id, lock=False)
            variant = ProductVariant(product_id=product_id, **await self._variant_values(fields))
            await self.db.add(variant)
            await self.db.audit(
                actor, "variant.create", f"variant:{variant.id}", {"product": product_id}
            )
        return variant

    async def update_variant(
        self, actor: int, variant_id: int, fields: dict[str, Any]
    ) -> ProductVariant:
        async with self.tx():
            variant = await self.need(ProductVariant, variant_id)
            diff = apply(variant, await self._variant_values(fields))
            await self.db.audit(actor, "variant.update", f"variant:{variant_id}", diff)
        return variant

    async def delete_variant(self, actor: int, variant_id: int) -> None:
        async with self.tx():
            variant = await self.need(ProductVariant, variant_id)
            if await self.db.variant_has_orders(variant_id):
                raise Conflict("has_orders")
            await self.db.delete(variant)
            await self.db.audit(actor, "variant.delete", f"variant:{variant_id}", {})

    # --- stock
    async def stock(self, variant_id: int) -> StockView:
        variant = await self.need(ProductVariant, variant_id, lock=False)
        free = (await self.db.free_stock([variant.id]))[variant.id]
        return StockView(
            free,
            await self.db.stock_unlimited(variant_id),
            await self.db.stock_recent(variant_id, STOCK_RECENT),
        )

    async def _stock_variant(self, variant_id: int) -> ProductVariant:
        variant = await self.need(ProductVariant, variant_id)
        product = await self.need(Product, variant.product_id, lock=False)
        if product.fulfillment_type != "stock":
            raise Conflict("not_stock")
        return variant

    async def add_stock(self, actor: int, variant_id: int, text: str) -> StockImport:
        """One line is one unit: blank lines are skipped, repeats in the paste and units that
        already wait unsold are not added twice."""
        lines = [line.strip() for line in text.splitlines()]
        lines = [line for line in lines if line]
        if len(lines) > STOCK_MAX_LINES:
            raise InvalidField("text", f"at most {STOCK_MAX_LINES} lines at once")
        if any(len(line) > PAYLOAD_MAX for line in lines):
            raise InvalidField("text", f"a line is longer than {PAYLOAD_MAX}")
        unique = list(dict.fromkeys(lines))
        async with self.tx():
            await self._stock_variant(variant_id)
            known = await self.db.stock_payloads(variant_id, unique)
            fresh = [p for p in unique if p not in known]
            if fresh:
                await self.db.add(*(StockUnit(variant_id=variant_id, payload=p) for p in fresh))
            await self.db.audit(actor, "stock.add", f"variant:{variant_id}", {"added": len(fresh)})
        return StockImport(len(fresh), len(lines) - len(fresh))

    async def set_unlimited(self, actor: int, variant_id: int, text: str | None) -> None:
        """The one unit that is handed out forever; None or blank removes it."""
        payload = (text or "").strip()
        if len(payload) > PAYLOAD_MAX * 4:
            raise InvalidField("text", "too long")
        async with self.tx():
            await self._stock_variant(variant_id)
            unit = await self.db.stock_unlimited(variant_id)
            if unit is None and payload:
                await self.db.add(
                    StockUnit(variant_id=variant_id, payload=payload, is_unlimited=True)
                )
            elif unit is not None and payload:
                unit.payload = payload
            elif unit is not None:
                await self.db.delete(unit)
            await self.db.audit(
                actor, "stock.unlimited", f"variant:{variant_id}", {"set": bool(payload)}
            )

    async def delete_stock(self, actor: int, unit_id: int) -> None:
        async with self.tx():
            unit = await self.need(StockUnit, unit_id)
            if unit.sold_order_id is not None:
                raise Conflict("sold")
            await self.db.delete(unit)
            await self.db.audit(
                actor, "stock.delete", f"variant:{unit.variant_id}", {"unit": unit_id}
            )

    # --- services
    async def services(self) -> list[Service]:
        return await self.db.services()

    def _service_values(self, fields: dict[str, Any]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        if "title" in fields:
            title = (fields["title"] or "").strip()
            if not title:
                raise InvalidField("title", "required")
            out["title"] = title
        if "deadline_minutes" in fields:
            if not 1 <= fields["deadline_minutes"] <= 60 * 24 * 30:
                raise InvalidField("deadline_minutes", "out of range")
            out["deadline_minutes"] = fields["deadline_minutes"]
        if "assign_mode" in fields:
            out["assign_mode"] = AssignMode(fields["assign_mode"])
        if "executor_percent" in fields:
            if not 0 <= fields["executor_percent"] <= 100:
                raise InvalidField("executor_percent", "0..100")
            out["executor_percent"] = fields["executor_percent"]
        if "is_active" in fields:
            out["is_active"] = fields["is_active"]
        return out

    async def create_service(self, actor: int, code: str, fields: dict[str, Any]) -> Service:
        code = code.strip().lower()
        if not _SERVICE_CODE.fullmatch(code):
            raise InvalidField("code", "a-z, 0-9, _; 2-32 characters")
        async with self.tx():
            if await self.db.service_by_code(code) is not None:
                raise Conflict("code_taken")
            service = Service(code=code, **self._service_values(fields))
            await self.db.add(service)
            await self.db.audit(actor, "service.create", f"service:{service.id}", {"code": code})
        return service

    async def update_service(self, actor: int, service_id: int, fields: dict[str, Any]) -> Service:
        async with self.tx():
            service = await self.need(Service, service_id)
            diff = apply(service, self._service_values(fields))
            await self.db.audit(actor, "service.update", f"service:{service_id}", diff)
        return service

    async def delete_service(self, actor: int, service_id: int) -> None:
        async with self.tx():
            service = await self.need(Service, service_id)
            if await self.db.service_products(service_id):
                raise Conflict("has_products")
            await self.db.delete(service)
            await self.db.audit(actor, "service.delete", f"service:{service_id}", {})

    # --- countries
    async def countries(self) -> list[Country]:
        return await self.db.countries()

    async def create_country(self, actor: int, code: str, title: dict[str, str]) -> Country:
        code = code.strip().upper()
        if not re.fullmatch(r"[A-Z]{2}", code):
            raise InvalidField("code", "ISO 3166-1 alpha-2")
        async with self.tx():
            if await self.db.get(Country, code) is not None:
                raise Conflict("code_taken")
            country = Country(code=code, title_i18n=i18n(title, "title"))
            await self.db.add(country)
            await self.db.audit(actor, "country.create", f"country:{code}", {})
        return country

    async def update_country(self, actor: int, code: str, title: dict[str, str]) -> Country:
        async with self.tx():
            country = await self.need(Country, code.upper())
            diff = apply(country, {"title_i18n": i18n(title, "title")})
            await self.db.audit(actor, "country.update", f"country:{country.code}", diff)
        return country

    async def delete_country(self, actor: int, code: str) -> None:
        async with self.tx():
            country = await self.need(Country, code.upper())
            if await self.db.country_used(country.code):
                raise Conflict("in_use")
            await self.db.delete(country)
            await self.db.audit(actor, "country.delete", f"country:{country.code}", {})
