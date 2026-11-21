from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dishka import AsyncContainer

from app.infrastructure.scheduler import payments


def create_scheduler(container: AsyncContainer) -> AsyncIOScheduler:
    """Not started here: LifespanService starts and stops it. Later phases add their jobs below."""
    scheduler = AsyncIOScheduler(timezone="UTC", job_defaults={"misfire_grace_time": 30})
    payments.register(scheduler, container)
    return scheduler
