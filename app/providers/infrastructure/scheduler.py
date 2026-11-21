from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dishka import AsyncContainer, Provider, Scope, provide

from app.infrastructure.scheduler import create_scheduler


class SchedulerProvider(Provider):
    scope = Scope.APP

    @provide
    def provide_scheduler(self, container: AsyncContainer) -> AsyncIOScheduler:
        return create_scheduler(container)
