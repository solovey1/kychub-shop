from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app.application.interactors.admin.system import SettingsAdminInteractor, Tunables
from app.presentation.fastapi.api.admin.schemas import SettingsBody, SettingsUser
from app.presentation.fastapi.api.schemas import usd

router: APIRouter = APIRouter(tags=["admin-settings"])


def _out(t: Tunables) -> SettingsBody:
    return SettingsBody(
        hold_days=t.hold_days,
        review_delay_hours=t.review_delay_hours,
        min_withdrawal=usd(t.min_withdrawal),
        confirm_hours=t.confirm_hours,
        dispute_reply_hours=t.dispute_reply_hours,
        accept_minutes=t.accept_minutes,
    )


@router.get("/settings")
@inject
async def get_settings(
    _: SettingsUser, settings: FromDishka[SettingsAdminInteractor]
) -> SettingsBody:
    return _out(await settings.get())


@router.put("/settings")
@inject
async def put_settings(
    body: SettingsBody, user: SettingsUser, settings: FromDishka[SettingsAdminInteractor]
) -> SettingsBody:
    return _out(
        await settings.update(
            user.id,
            body.hold_days,
            body.review_delay_hours,
            body.min_withdrawal,
            body.confirm_hours,
            body.dispute_reply_hours,
            body.accept_minutes,
        )
    )
