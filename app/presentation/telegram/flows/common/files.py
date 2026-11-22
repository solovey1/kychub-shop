import asyncio
from typing import Any, Literal

from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from app.application.models.form_schema import FormField, join_files

# ponytail: process-local locks (one bot process); a shared lock if the bot is ever scaled out.
_LOCKS: dict[int, asyncio.Lock] = {}


def chat_lock(chat_id: int) -> asyncio.Lock:
    """The items of an album arrive as separate updates handled concurrently: one at a time."""
    return _LOCKS.setdefault(chat_id, asyncio.Lock())


def file_id_of(message: Message) -> str | None:
    if message.document:
        return message.document.file_id
    if message.photo:
        return message.photo[-1].file_id
    return None


def is_straggler(message: Message, data: dict[str, Any]) -> bool:
    """An item of an album whose field is already answered: it must not answer anything else."""
    return bool(message.media_group_id) and message.media_group_id == data.get("group")


async def take_file(
    fsm: FSMContext, message: Message, field: FormField, data: dict[str, Any]
) -> tuple[Literal["wrong", "more", "done"], str]:
    """One file message for a `file` field. FSM data: `files` (collected for this field),
    `group_open` (album being collected), `group` (album already closed: its other items
    are dropped, so they never answer the next question). Call under `chat_lock`."""
    group = message.media_group_id
    file_id = file_id_of(message)
    if file_id is None:
        return "wrong", ""
    if field.max_files == 1:
        await fsm.update_data(group=group)
        return "done", file_id
    files: list[str] = list(data.get("files", []))
    if file_id not in files:
        files.append(file_id)
    if len(files) >= field.max_files:
        await fsm.update_data(files=[], group_open=None, group=group)
        return "done", join_files(files)
    await fsm.update_data(files=files, group_open=group)
    return "more", ""


async def finish_files(fsm: FSMContext, data: dict[str, Any]) -> str:
    """The "Done" button: what is collected so far; the rest of the album is dropped."""
    await fsm.update_data(files=[], group=data.get("group_open"), group_open=None)
    return join_files(list(data.get("files", [])))
