import asyncio
import logging
from dataclasses import dataclass
from typing import Final, Literal

from aiogram import Bot
from aiogram.enums import ParseMode
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter

from app.application.ports.repositories.admin import AdminGateway
from app.application.ports.uow import UnitOfWork
from app.domain.broadcast import Broadcast
from app.domain.enums.broadcast import BroadcastStatus
from app.utils.time import datetime_now

logger: Final = logging.getLogger(__name__)

BATCH: Final = 25  # messages per second; Telegram allows about 30 to different chats
Outcome = Literal["ok", "blocked", "failed"]


@dataclass(frozen=True)
class BroadcastSender:
    """Sends the oldest running broadcast, one second of recipients per `step`.
    Progress (the id of the last recipient, the counters) is saved after every batch, so a
    restart goes on where it stopped; a batch that was in flight may be sent twice.
    ponytail: the broadcast row stays locked while a batch is on its way (a flood wait makes it
    longer); a stop request simply waits for it."""

    bot: Bot
    db: AdminGateway
    uow: UnitOfWork

    async def preview(self, user_id: int, text: str) -> None:
        """To the admin himself; a Telegram error (broken HTML) is for the caller to show."""
        await self.bot.send_message(user_id, text, parse_mode=ParseMode.HTML)

    async def _send(self, user_id: int, text: str) -> Outcome:
        for attempt in (1, 2):
            try:
                await self.bot.send_message(user_id, text, parse_mode=ParseMode.HTML)
                return "ok"
            except TelegramRetryAfter as e:
                if attempt == 2:
                    return "failed"
                await asyncio.sleep(e.retry_after)
            except TelegramForbiddenError:
                return "blocked"
            except TelegramAPIError:
                return "failed"
        return "failed"

    async def step(self) -> bool:
        """One batch of the first running broadcast. False: nothing is running."""
        try:
            running = await self.db.next_sending()
            if running is None:
                return False
            broadcast = await self.db.lock(Broadcast, running.id)
            if broadcast is None or broadcast.status is not BroadcastStatus.sending:
                await self.uow.rollback()  # stopped while we were picking it up
                return True
            ids = await self.db.broadcast_batch(broadcast.cursor_user_id, BATCH)
            if not ids:
                broadcast.status = BroadcastStatus.sent
                broadcast.finished_at = datetime_now()
            else:
                outcomes = await asyncio.gather(*(self._send(i, broadcast.text) for i in ids))
                blocked = [i for i, o in zip(ids, outcomes, strict=True) if o == "blocked"]
                broadcast.sent_count += outcomes.count("ok")
                broadcast.failed_count += len(ids) - outcomes.count("ok")
                broadcast.cursor_user_id = ids[-1]
                await self.db.mark_blocked(blocked)
            await self.uow.commit()
            return True
        except BaseException:
            await self.uow.rollback()
            raise
