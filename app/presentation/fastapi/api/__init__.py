from fastapi import APIRouter

from app.presentation.fastapi.api import chat, executor, me, orders, staff
from app.presentation.fastapi.api.admin import router as admin_router

router: APIRouter = APIRouter(prefix="/api")
router.include_router(me.router)
router.include_router(orders.router)
router.include_router(chat.router)
router.include_router(executor.router)
router.include_router(staff.router)
router.include_router(admin_router)
