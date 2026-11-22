from fastapi import APIRouter

from app.presentation.fastapi.api.admin import catalog, orders, people

router: APIRouter = APIRouter(prefix="/admin")
router.include_router(catalog.router)
router.include_router(people.router)
router.include_router(orders.router)
