from aiogram.exceptions import TelegramAPIError
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter

from app.application.errors.shop import InvalidField
from app.application.interactors.admin.broadcasts import BroadcastAdminInteractor, clean_text
from app.domain.broadcast import Broadcast
from app.infrastructure.telegram.broadcast import BroadcastSender
from app.presentation.fastapi.api.admin.schemas import (
    BroadcastIn,
    BroadcastOut,
    BroadcastUser,
    IdOut,
    OkOut,
    RecipientsOut,
)

router: APIRouter = APIRouter(tags=["admin-broadcasts"])
Broadcasts = FromDishka[BroadcastAdminInteractor]


def _out(b: Broadcast) -> BroadcastOut:
    return BroadcastOut(
        id=b.id,
        text=b.text,
        status=b.status.value,
        sent_count=b.sent_count,
        failed_count=b.failed_count,
        total_count=b.total_count,
        created_at=b.created_at,
        started_at=b.started_at,
        finished_at=b.finished_at,
    )


@router.get("/broadcasts")
@inject
async def broadcasts(_: BroadcastUser, interactor: Broadcasts) -> list[BroadcastOut]:
    return [_out(b) for b in await interactor.broadcasts()]


@router.get("/broadcasts/recipients")
@inject
async def recipients(_: BroadcastUser, interactor: Broadcasts) -> RecipientsOut:
    return RecipientsOut(count=await interactor.recipients())


@router.get("/broadcasts/{broadcast_id}")
@inject
async def broadcast(broadcast_id: int, _: BroadcastUser, interactor: Broadcasts) -> BroadcastOut:
    return _out(await interactor.broadcast(broadcast_id))


@router.post("/broadcasts")
@inject
async def create(body: BroadcastIn, user: BroadcastUser, interactor: Broadcasts) -> IdOut:
    return IdOut(id=(await interactor.create(user.id, body.text)).id)


@router.put("/broadcasts/{broadcast_id}")
@inject
async def update(
    broadcast_id: int, body: BroadcastIn, user: BroadcastUser, interactor: Broadcasts
) -> OkOut:
    await interactor.update(user.id, broadcast_id, body.text)
    return OkOut()


@router.post("/broadcasts/preview")
@inject
async def preview(
    body: BroadcastIn, user: BroadcastUser, sender: FromDishka[BroadcastSender]
) -> OkOut:
    """The text as the recipients will see it, to the caller only."""
    try:
        await sender.preview(user.id, clean_text(body.text))
    except TelegramAPIError as e:
        raise InvalidField("text", e.message) from e
    return OkOut()


@router.post("/broadcasts/{broadcast_id}/start")
@inject
async def start(broadcast_id: int, user: BroadcastUser, interactor: Broadcasts) -> BroadcastOut:
    return _out(await interactor.start(user.id, broadcast_id))


@router.post("/broadcasts/{broadcast_id}/stop")
@inject
async def stop(broadcast_id: int, user: BroadcastUser, interactor: Broadcasts) -> BroadcastOut:
    return _out(await interactor.stop(user.id, broadcast_id))
