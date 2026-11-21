from fastapi import APIRouter

from app.presentation.fastapi.api import me, orders

router: APIRouter = APIRouter(prefix="/api")
router.include_router(me.router)
router.include_router(orders.router)
