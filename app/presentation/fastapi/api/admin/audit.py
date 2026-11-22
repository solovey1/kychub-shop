from html import unescape

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app.application.interactors.admin.system import AuditAdminInteractor
from app.presentation.fastapi.api.admin.schemas import AuditOut, SettingsUser

router: APIRouter = APIRouter(tags=["admin-audit"])
Audit = FromDishka[AuditAdminInteractor]


@router.get("/audit")
@inject
async def audit(
    _: SettingsUser, interactor: Audit, actor_id: int | None = None, action: str | None = None
) -> list[AuditOut]:
    return [
        AuditOut(
            id=row.id,
            actor_id=row.actor_id,
            actor_name=None if name is None else unescape(name),
            action=row.action,
            target=row.target,
            payload=row.payload,
            created_at=row.created_at,
        )
        for row, name in await interactor.rows(actor_id, action)
    ]


@router.get("/audit/actions")
@inject
async def actions(_: SettingsUser, interactor: Audit) -> list[str]:
    return await interactor.actions()
