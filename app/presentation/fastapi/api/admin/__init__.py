from fastapi import APIRouter

from app.presentation.fastapi.api.admin import catalog

router: APIRouter = APIRouter(prefix="/admin")
router.include_router(catalog.router)
