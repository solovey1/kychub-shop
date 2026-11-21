import logging
from typing import Final

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dishka import AsyncContainer

from app.application.interactors.dispatch import DispatchInteractor
from app.infrastructure.telegram.offers import OfferService

logger: Final = logging.getLogger(__name__)


async def expire_overdue(container: AsyncContainer) -> None:
    """Orders whose deadline passed go back to the queue; notify after each commit."""
    async with container() as request:
        results = await (await request.get(DispatchInteractor)).expire_overdue()
        offers = await request.get(OfferService)
        for result in results:
            await offers.announce(result)


async def requeue_stale(container: AsyncContainer) -> None:
    """Queued orders nobody was offered for 10 minutes: look for newly permitted executors."""
    async with container() as request:
        results = await (await request.get(DispatchInteractor)).requeue_stale()
        offers = await request.get(OfferService)
        for result in results:
            await offers.announce(result)


def _job(
    scheduler: AsyncIOScheduler, container: AsyncContainer, func: object, name: str, seconds: int
) -> None:
    scheduler.add_job(
        func,
        "interval",
        seconds=seconds,
        args=[container],
        id=name,
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )


def register(scheduler: AsyncIOScheduler, container: AsyncContainer) -> None:
    _job(scheduler, container, expire_overdue, "expire_overdue", 60)
    _job(scheduler, container, requeue_stale, "requeue_stale", 300)
