from fastapi import APIRouter

from app.presentation.fastapi.api import chat, me, orders

router: APIRouter = APIRouter(prefix="/api")
router.include_router(me.router)
router.include_router(orders.router)
router.include_router(chat.router)
