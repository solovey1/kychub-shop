import asyncio
import mimetypes
from typing import Final

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from app.application.errors.shop import ChatForbidden
from app.application.interactors.conversations import ConversationInteractor
from app.application.models.config import AppConfig
from app.application.ports.repositories.users import UsersGateway
from app.domain.support import Conversation
from app.infrastructure.events import EventHub, message_view
from app.infrastructure.telegram.effects import Effects
from app.presentation.fastapi.api.auth import CurrentUser, authenticate
from app.presentation.fastapi.api.schemas import (
    ConversationOut,
    MessageOut,
    MessagesOut,
    PostMessageIn,
    SupportIn,
    TicketRefOut,
)

router: APIRouter = APIRouter(tags=["chat"])

PING_EVERY: Final = 30
UNAUTHORIZED_CLOSE: Final = 4401
PAGE_MAX: Final = 100
AUTH_WAIT: Final = 10
INLINE_TYPES: Final = frozenset(
    {"image/jpeg", "image/png", "image/webp", "video/mp4", "audio/ogg", "audio/mpeg"}
)


async def _readable(
    chat: ConversationInteractor, user_id: int, conversation_id: int
) -> Conversation:
    """Somebody else's conversation looks exactly like a missing one."""
    conversation = await chat.get_conversation(conversation_id)
    if conversation is None or await chat.reader_role(user_id, conversation) is None:
        raise HTTPException(404, "Not found")
    return conversation


@router.post("/orders/{order_id}/chat")
@inject
async def order_chat(
    order_id: int, user: CurrentUser, chat: FromDishka[ConversationInteractor]
) -> ConversationOut:
    conversation = await chat.order_conversation(user.id, order_id)  # OrderUnavailable -> 404
    return ConversationOut(
        conversation_id=conversation.id,
        can_post=await chat.can_post(user.id, conversation) is not None,
    )


@router.post("/support")
@inject
async def support(
    body: SupportIn, user: CurrentUser, chat: FromDishka[ConversationInteractor]
) -> TicketRefOut:
    ticket, conversation, created = await chat.open_ticket(user.id, body.order_id)
    return TicketRefOut(ticket_id=ticket.id, conversation_id=conversation.id, created=created)


@router.get("/conversations/{conversation_id}/messages")
@inject
async def messages(
    conversation_id: int,
    user: CurrentUser,
    chat: FromDishka[ConversationInteractor],
    before_id: int | None = Query(None, ge=1),
    limit: int = Query(50, ge=1, le=PAGE_MAX),
) -> MessagesOut:
    conversation = await _readable(chat, user.id, conversation_id)
    items, has_more = await chat.messages(conversation_id, before_id, limit)
    return MessagesOut(
        items=[MessageOut(**message_view(m, user.id)) for m in items],
        has_more=has_more,
        can_post=await chat.can_post(user.id, conversation) is not None,
    )


@router.post("/conversations/{conversation_id}/messages")
@inject
async def post_message(
    conversation_id: int,
    body: PostMessageIn,
    user: CurrentUser,
    chat: FromDishka[ConversationInteractor],
    effects: FromDishka[Effects],
) -> MessageOut:
    await _readable(chat, user.id, conversation_id)
    try:
        posted = await chat.post(conversation_id, user.id, body.text, None)
    except ChatForbidden:  # may read, may not write: a closed ticket, an order chat of staff
        raise HTTPException(409, "Conversation is read-only") from None
    await effects.message_posted(posted)
    message = await chat.message(posted.message_id)
    assert message is not None
    return MessageOut(**message_view(message, user.id))


@router.get("/files/{message_id}")
@inject
async def file(
    message_id: int,
    user: CurrentUser,
    chat: FromDishka[ConversationInteractor],
    bot: FromDishka[Bot],
) -> StreamingResponse:
    """The media of a message, streamed from Telegram by its file id."""
    message = await chat.readable_message(user.id, message_id)
    if message is None or not message.media:
        raise HTTPException(404, "Not found")
    try:
        info = await bot.get_file(message.media["file_id"])
    except TelegramAPIError:
        raise HTTPException(404, "File unavailable") from None
    if not info.file_path:
        raise HTTPException(404, "File unavailable")
    # same origin as the Mini App: only a short list of types may be shown inline, the type
    # never comes from the (sender-controlled) file name alone
    guessed = "image/jpeg" if message.media.get("type") == "photo" else None
    guessed = guessed or mimetypes.guess_type(info.file_path)[0]
    inline = guessed in INLINE_TYPES
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "sandbox; default-src 'none'",
    }
    if not inline:
        headers["Content-Disposition"] = "attachment"
    stream = bot.session.stream_content(bot.session.api.file_url(bot.token, info.file_path))
    return StreamingResponse(
        stream, media_type=guessed if inline else "application/octet-stream", headers=headers
    )


@router.websocket("/ws")
async def ws(websocket: WebSocket) -> None:
    """The first frame must be {"type": "auth", "init_data": "..."} within 10 seconds (the
    credentials never go into the URL). Events: message, order, queue, ticket."""
    container = websocket.state.dishka_container
    await websocket.accept()
    init_data = ""
    try:
        frame = await asyncio.wait_for(websocket.receive_json(), AUTH_WAIT)
        if isinstance(frame, dict) and frame.get("type") == "auth":
            init_data = str(frame.get("init_data", ""))
    except (asyncio.TimeoutError, ValueError, KeyError):
        pass
    except WebSocketDisconnect:
        return
    user = None
    if init_data:
        async with container() as request:  # the socket itself holds no database session
            user = await authenticate(
                init_data, await request.get(AppConfig), await request.get(UsersGateway)
            )
    if user is None:
        await websocket.close(UNAUTHORIZED_CLOSE)
        return
    hub = await container.get(EventHub)
    await hub.connect(user.id, websocket)
    try:
        while True:
            try:  # nothing is expected from the client; silence for 30 seconds is pinged
                await asyncio.wait_for(websocket.receive_text(), PING_EVERY)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(user.id, websocket)
