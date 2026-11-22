from fastapi import APIRouter

from app.presentation.fastapi.api.admin import (
    audit,
    broadcasts,
    catalog,
    money,
    orders,
    people,
    promo,
    settings,
    stats,
)

router: APIRouter = APIRouter(prefix="/admin")
router.include_router(catalog.router)
router.include_router(people.router)
router.include_router(orders.router)
for module in (money, promo, broadcasts, stats, settings, audit):
    router.include_router(module.router)
