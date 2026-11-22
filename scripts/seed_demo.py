"""Idempotent demo data: countries, a service, a category tree and four products.

Run: uv run python -m scripts.seed_demo
"""

import asyncio
import sys
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.application.models.config import AppConfig
from app.application.models.form_schema import FormSchema
from app.domain.catalog import Category, Country, Product, ProductVariant, Service, StockUnit
from app.providers.infrastructure.app import create_app_config


def _tr(ru: str, en: str, uk: str) -> dict[str, str]:
    return {"ru": ru, "en": en, "uk": uk}


async def _category(
    s: AsyncSession, parent: Optional[Category], title: dict[str, str], position: int
) -> Category:
    query = select(Category).where(Category.title_i18n["ru"].astext == title["ru"])
    query = query.where(
        Category.parent_id.is_(None) if parent is None else Category.parent_id == parent.id
    )
    found = await s.scalar(query)
    if found:
        return found
    cat = Category(parent_id=parent.id if parent else None, title_i18n=title, position=position)
    s.add(cat)
    await s.flush()
    return cat


async def _product(
    s: AsyncSession,
    category: Category,
    title: dict[str, str],
    fulfillment_type: str,
    variants: list[tuple[Optional[str], Decimal]],
    *,
    description: dict[str, str],
    service: Optional[Service] = None,
    input_schema: Optional[dict[str, Any]] = None,
    config: Optional[dict[str, Any]] = None,
    stock: int = 0,
) -> None:
    FormSchema.model_validate(input_schema or {"fields": []})  # before anything is written
    existing = await s.scalar(
        select(Product).where(Product.title_i18n["ru"].astext == title["ru"])
    )
    if existing is not None:
        existing.input_schema = input_schema or {}  # keeps a re-run in step with the seed
        return
    product = Product(
        category_id=category.id,
        service_id=service.id if service else None,
        title_i18n=title,
        description_i18n=description,
        input_schema=input_schema or {},
        fulfillment_type=fulfillment_type,
        fulfillment_config=config or {},
    )
    s.add(product)
    await s.flush()
    for country, price in variants:
        variant = ProductVariant(product_id=product.id, country_code=country, price=price)
        s.add(variant)
        await s.flush()
        for i in range(stock):
            s.add(StockUnit(variant_id=variant.id, payload=f"DEMO-KEY-{variant.id}-{i + 1}"))


async def seed(s: AsyncSession) -> None:
    for code, title in (
        ("TR", _tr("Турция", "Turkey", "Туреччина")),
        ("KZ", _tr("Казахстан", "Kazakhstan", "Казахстан")),
        ("US", _tr("США", "United States", "США")),
    ):
        if await s.get(Country, code) is None:
            s.add(Country(code=code, title_i18n=title))

    steam = await s.scalar(select(Service).where(Service.code == "steam"))
    if steam is None:
        steam = Service(code="steam", title="Steam", deadline_minutes=120, executor_percent=70)
        s.add(steam)
    await s.flush()

    accounts = await _category(s, None, _tr("Аккаунты", "Accounts", "Акаунти"), 0)
    steam_cat = await _category(s, accounts, _tr("Steam", "Steam", "Steam"), 0)
    keys = await _category(s, None, _tr("Ключи", "Keys", "Ключі"), 1)

    await _product(
        s,
        steam_cat,
        _tr("Регистрация Steam", "Steam registration", "Реєстрація Steam"),
        "executor",
        [("TR", Decimal("5.00")), ("KZ", Decimal("7.00"))],
        description=_tr(
            "Регистрация аккаунта Steam в выбранном регионе.",
            "Steam account registration in the selected region.",
            "Реєстрація акаунта Steam у вибраному регіоні.",
        ),
        service=steam,
    )
    await _product(
        s,
        keys,
        _tr("Ключ Windows", "Windows key", "Ключ Windows"),
        "stock",
        [(None, Decimal("10.00"))],
        description=_tr(
            "Лицензионный ключ выдаётся сразу после оплаты.",
            "The license key is delivered right after payment.",
            "Ліцензійний ключ видається одразу після оплати.",
        ),
        stock=3,
    )
    await _product(
        s,
        keys,
        _tr("Гайд PDF", "Guide PDF", "Гайд PDF"),
        "fixed",
        [(None, Decimal("2.00"))],
        description=_tr("Ссылка на гайд.", "A link to the guide.", "Посилання на гайд."),
        config={"text": "https://example.com/guide"},
    )
    await _product(
        s,
        accounts,
        _tr("Индивидуальный заказ", "Custom order", "Індивідуальне замовлення"),
        "manual",
        [(None, Decimal("15.00"))],
        description=_tr(
            "Опишите задачу, администратор свяжется с вами.",
            "Describe the task, an administrator will contact you.",
            "Опишіть завдання, адміністратор зв'яжеться з вами.",
        ),
        input_schema={
            "fields": [
                {
                    "key": "details",
                    "type": "text",
                    "label": _tr("Опишите задачу", "Describe the task", "Опишіть завдання"),
                    "max_length": 1000,
                }
            ]
        },
    )


async def main() -> None:
    config: AppConfig = create_app_config()
    engine = create_async_engine(config.postgres.build_url())
    try:
        async with AsyncSession(engine) as session:
            await seed(session)
            await session.commit()
    finally:
        await engine.dispose()
    sys.stdout.write("demo data is in place" + chr(10))


if __name__ == "__main__":
    asyncio.run(main())
