from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app.application.interactors.admin.catalog import CatalogAdminInteractor
from app.presentation.fastapi.api.admin.schemas import (
    CatalogOrUsers,
    CatalogUser,
    CategoryIn,
    CategoryOut,
    CategoryPatch,
    CountryIn,
    CountryOut,
    CountryPatch,
    IdOut,
    MoveIn,
    OkOut,
    ProductBrief,
    ProductIn,
    ProductOut,
    ProductPatch,
    ServiceIn,
    ServiceOut,
    ServicePatch,
    StockImportOut,
    StockIn,
    StockOut,
    StockUnitOut,
    UnlimitedIn,
    VariantIn,
    VariantOut,
    VariantPatch,
)
from app.presentation.fastapi.api.schemas import usd

router: APIRouter = APIRouter(tags=["admin-catalog"])
Catalog = FromDishka[CatalogAdminInteractor]


# --- categories
@router.get("/categories")
@inject
async def categories(_: CatalogUser, catalog: Catalog) -> list[CategoryOut]:
    return [
        CategoryOut(
            id=c.id,
            parent_id=c.parent_id,
            title=c.title_i18n,
            position=c.position,
            is_active=c.is_active,
            children=children,
            products=products,
        )
        for c, children, products in await catalog.categories()
    ]


@router.post("/categories")
@inject
async def create_category(body: CategoryIn, user: CatalogUser, catalog: Catalog) -> IdOut:
    category = await catalog.create_category(user.id, body.parent_id, body.title, body.is_active)
    return IdOut(id=category.id)


@router.patch("/categories/{category_id}")
@inject
async def update_category(
    category_id: int, body: CategoryPatch, user: CatalogUser, catalog: Catalog
) -> OkOut:
    await catalog.update_category(user.id, category_id, body.model_dump(exclude_unset=True))
    return OkOut()


@router.post("/categories/{category_id}/move")
@inject
async def move_category(
    category_id: int, body: MoveIn, user: CatalogUser, catalog: Catalog
) -> OkOut:
    await catalog.move_category(user.id, category_id, body.direction)
    return OkOut()


@router.delete("/categories/{category_id}")
@inject
async def delete_category(category_id: int, user: CatalogUser, catalog: Catalog) -> OkOut:
    await catalog.delete_category(user.id, category_id)
    return OkOut()


# --- products
@router.get("/categories/{category_id}/products")
@inject
async def products(category_id: int, _: CatalogUser, catalog: Catalog) -> list[ProductBrief]:
    return [
        ProductBrief(
            id=p.id,
            title=p.title_i18n,
            is_active=p.is_active,
            fulfillment_type=p.fulfillment_type,
            variants=variants,
            price_from=None if price is None else usd(price),
        )
        for p, variants, price in await catalog.products(category_id)
    ]


@router.get("/products/{product_id}")
@inject
async def product(product_id: int, _: CatalogUser, catalog: Catalog) -> ProductOut:
    detail = await catalog.product(product_id)
    p = detail.product
    return ProductOut(
        id=p.id,
        category_id=p.category_id,
        service_id=p.service_id,
        title=p.title_i18n,
        description=p.description_i18n,
        input_schema=p.input_schema,
        result_schema=p.result_schema,
        fulfillment_type=p.fulfillment_type,
        fulfillment_config=p.fulfillment_config,
        is_active=p.is_active,
        variants=[
            VariantOut(
                id=v.id,
                country_code=v.country_code,
                title=v.title_i18n,
                price=usd(v.price),
                is_active=v.is_active,
                stock=detail.stock.get(v.id),
            )
            for v in detail.variants
        ],
        used=detail.used,
    )


@router.post("/products")
@inject
async def create_product(body: ProductIn, user: CatalogUser, catalog: Catalog) -> IdOut:
    created = await catalog.create_product(user.id, body.model_dump())
    return IdOut(id=created.id)


@router.patch("/products/{product_id}")
@inject
async def update_product(
    product_id: int, body: ProductPatch, user: CatalogUser, catalog: Catalog
) -> OkOut:
    await catalog.update_product(user.id, product_id, body.model_dump(exclude_unset=True))
    return OkOut()


@router.post("/products/{product_id}/move")
@inject
async def move_product(
    product_id: int, body: MoveIn, user: CatalogUser, catalog: Catalog
) -> OkOut:
    await catalog.move_product(user.id, product_id, body.direction)
    return OkOut()


@router.delete("/products/{product_id}")
@inject
async def delete_product(product_id: int, user: CatalogUser, catalog: Catalog) -> OkOut:
    await catalog.delete_product(user.id, product_id)
    return OkOut()


# --- variants and stock
@router.post("/products/{product_id}/variants")
@inject
async def create_variant(
    product_id: int, body: VariantIn, user: CatalogUser, catalog: Catalog
) -> IdOut:
    return IdOut(id=(await catalog.create_variant(user.id, product_id, body.model_dump())).id)


@router.patch("/variants/{variant_id}")
@inject
async def update_variant(
    variant_id: int, body: VariantPatch, user: CatalogUser, catalog: Catalog
) -> OkOut:
    await catalog.update_variant(user.id, variant_id, body.model_dump(exclude_unset=True))
    return OkOut()


@router.delete("/variants/{variant_id}")
@inject
async def delete_variant(variant_id: int, user: CatalogUser, catalog: Catalog) -> OkOut:
    await catalog.delete_variant(user.id, variant_id)
    return OkOut()


@router.get("/variants/{variant_id}/stock")
@inject
async def stock(variant_id: int, _: CatalogUser, catalog: Catalog) -> StockOut:
    view = await catalog.stock(variant_id)
    return StockOut(
        free=view.free,
        unlimited=view.unlimited.payload if view.unlimited else None,
        recent=[StockUnitOut(id=u.id, payload=u.payload) for u in view.recent],
    )


@router.post("/variants/{variant_id}/stock")
@inject
async def add_stock(
    variant_id: int, body: StockIn, user: CatalogUser, catalog: Catalog
) -> StockImportOut:
    result = await catalog.add_stock(user.id, variant_id, body.text)
    return StockImportOut(added=result.added, duplicates=result.duplicates)


@router.put("/variants/{variant_id}/stock/unlimited")
@inject
async def set_unlimited(
    variant_id: int, body: UnlimitedIn, user: CatalogUser, catalog: Catalog
) -> OkOut:
    await catalog.set_unlimited(user.id, variant_id, body.text)
    return OkOut()


@router.delete("/stock/{unit_id}")
@inject
async def delete_stock(unit_id: int, user: CatalogUser, catalog: Catalog) -> OkOut:
    await catalog.delete_stock(user.id, unit_id)
    return OkOut()


# --- services and countries (the executor matrix reads them too)
@router.get("/services")
@inject
async def services(_: CatalogOrUsers, catalog: Catalog) -> list[ServiceOut]:
    return [
        ServiceOut(
            id=s.id,
            code=s.code,
            title=s.title,
            deadline_minutes=s.deadline_minutes,
            assign_mode=s.assign_mode.value,
            executor_percent=s.executor_percent,
            is_active=s.is_active,
        )
        for s in await catalog.services()
    ]


@router.post("/services")
@inject
async def create_service(body: ServiceIn, user: CatalogUser, catalog: Catalog) -> IdOut:
    created = await catalog.create_service(user.id, body.code, body.model_dump(exclude={"code"}))
    return IdOut(id=created.id)


@router.patch("/services/{service_id}")
@inject
async def update_service(
    service_id: int, body: ServicePatch, user: CatalogUser, catalog: Catalog
) -> OkOut:
    await catalog.update_service(user.id, service_id, body.model_dump(exclude_unset=True))
    return OkOut()


@router.delete("/services/{service_id}")
@inject
async def delete_service(service_id: int, user: CatalogUser, catalog: Catalog) -> OkOut:
    await catalog.delete_service(user.id, service_id)
    return OkOut()


@router.get("/countries")
@inject
async def countries(_: CatalogOrUsers, catalog: Catalog) -> list[CountryOut]:
    return [CountryOut(code=c.code, title=c.title_i18n) for c in await catalog.countries()]


@router.post("/countries")
@inject
async def create_country(body: CountryIn, user: CatalogUser, catalog: Catalog) -> CountryOut:
    country = await catalog.create_country(user.id, body.code, body.title)
    return CountryOut(code=country.code, title=country.title_i18n)


@router.patch("/countries/{code}")
@inject
async def update_country(
    code: str, body: CountryPatch, user: CatalogUser, catalog: Catalog
) -> OkOut:
    await catalog.update_country(user.id, code, body.title)
    return OkOut()


@router.delete("/countries/{code}")
@inject
async def delete_country(code: str, user: CatalogUser, catalog: Catalog) -> OkOut:
    await catalog.delete_country(user.id, code)
    return OkOut()
