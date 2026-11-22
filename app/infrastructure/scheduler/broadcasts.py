import asyncio
import logging
import time
from typing import Final

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dishka import AsyncContainer

from app.infrastructure.telegram.broadcast import BroadcastSender

logger: Final = logging.getLogger(__name__)


async def send_broadcasts(container: AsyncContainer) -> None:
    """Runs batches of 25 messages, one per second, until no broadcast is running."""
    while True:
        started = time.monotonic()
        try:
            async with container() as request:
                more = await (await request.get(BroadcastSender)).step()
        except Exception:
            logger.exception("broadcast step failed")
            return  # the next run of the job tries again from the saved cursor
        if not more:
            return
        await asyncio.sleep(max(0.0, 1.0 - (time.monotonic() - started)))


def register(scheduler: AsyncIOScheduler, container: AsyncContainer) -> None:
    scheduler.add_job(
        send_broadcasts,
        "interval",
        seconds=10,
        args=[container],
        id="send_broadcasts",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
