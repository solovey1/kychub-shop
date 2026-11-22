import logging
from typing import Final

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dishka import AsyncContainer

from app.application.interactors.auto_confirm import (
    AutoConfirmInteractor,
    confirm_deadline,
    confirm_hours,
)
from app.application.interactors.cancel_request import CancelRequestInteractor
from app.application.interactors.deadlines import ReminderInteractor
from app.application.interactors.dispatch import DispatchInteractor
from app.application.interactors.disputes import DisputeInteractor
from app.application.interactors.feedback import ReviewInteractor
from app.application.interactors.hold import HoldInteractor
from app.application.interactors.info_request import InfoRequestInteractor
from app.application.ports.repositories.settings import SettingsGateway
from app.infrastructure.telegram.effects import Effects
from app.infrastructure.telegram.notices import OrderNotices
from app.infrastructure.telegram.offers import OfferService

logger: Final = logging.getLogger(__name__)


async def expire_overdue(container: AsyncContainer) -> None:
    """Orders whose deadline passed go back to the queue; notify after each commit."""
    async with container() as request:
        results = await (await request.get(DispatchInteractor)).expire_overdue()
        offers = await request.get(OfferService)
        for result in results:
            await offers.announce(result)


async def release_unaccepted(container: AsyncContainer) -> None:
    """Auto-assigned orders the executor did not accept in time go back to the queue."""
    async with container() as request:
        results = await (await request.get(DispatchInteractor)).release_unaccepted()
        offers = await request.get(OfferService)
        effects = await request.get(Effects)
        for result in results:
            await offers.announce(result)
            if result.released_executor_id is not None:
                await effects.executor_offline(result.released_executor_id)


async def requeue_stale(container: AsyncContainer) -> None:
    """Queued orders nobody was offered for 10 minutes: look for newly permitted executors."""
    async with container() as request:
        results = await (await request.get(DispatchInteractor)).requeue_stale()
        offers = await request.get(OfferService)
        for result in results:
            await offers.announce(result)


async def release_holds(container: AsyncContainer) -> None:
    """Earnings whose hold is over become available. Safe to run twice: the ledger refs are
    unique and the order row is locked."""
    async with container() as request:
        released = await (await request.get(HoldInteractor)).release_due()
    if released:
        logger.info("hold released for orders %s", released)


async def request_reviews(container: AsyncContainer) -> None:
    """Rating requests for orders completed a while ago, one message per order."""
    async with container() as request:
        orders = await (await request.get(ReviewInteractor)).request_due()
        notices = await request.get(OrderNotices)
        for order in orders:
            await notices.review_request(order)


async def remind_deadlines(container: AsyncContainer) -> None:
    """Executors whose order is half way to its deadline, or close to it, get a reminder. The
    event is committed before the message goes out (like the rating request)."""
    async with container() as request:
        reminders = await (await request.get(ReminderInteractor)).due()
        notices = await request.get(OrderNotices)
        for reminder in reminders:
            await notices.reminder(reminder)


async def auto_confirm(container: AsyncContainer) -> None:
    """Submitted orders the buyer did not answer within `confirm_hours` confirm themselves."""
    async with container() as request:
        confirmed = await (await request.get(AutoConfirmInteractor)).confirm_due()
        effects = await request.get(Effects)
        for order in confirmed:
            await effects.order_confirmed(order)


async def remind_confirm(container: AsyncContainer) -> None:
    """One message to the buyer 2 hours before the auto-confirmation."""
    async with container() as request:
        interactor = await request.get(AutoConfirmInteractor)
        hours = await confirm_hours(await request.get(SettingsGateway))
        notices = await request.get(OrderNotices)
        for order in await interactor.remind_due():
            until = confirm_deadline(order, hours)
            if until is not None:
                await notices.confirm_reminder(order, until)


async def resolve_disputes(container: AsyncContainer) -> None:
    """Disputes whose silent side missed the reply deadline resolve themselves."""
    async with container() as request:
        resolved = await (await request.get(DisputeInteractor)).auto_resolve_due()
        effects = await request.get(Effects)
        for item in resolved:
            await effects.dispute_resolved(item)


async def remind_disputes(container: AsyncContainer) -> None:
    """One message to the side a dispute waits for, an hour before its deadline."""
    async with container() as request:
        reminders = await (await request.get(DisputeInteractor)).remind_due()
        effects = await request.get(Effects)
        for reminder in reminders:
            await effects.dispute_reminder(reminder)


async def agree_cancels(container: AsyncContainer) -> None:
    """An executor who left the buyer's cancel request unanswered for an hour agrees to it."""
    async with container() as request:
        answers = await (await request.get(CancelRequestInteractor)).agree_due()
        effects = await request.get(Effects)
        for answer in answers:
            await effects.cancel_answered(answer)


async def time_out_info(container: AsyncContainer) -> None:
    """A buyer who left the executor's question unanswered for 24 h: the order is refunded."""
    async with container() as request:
        timeouts = await (await request.get(InfoRequestInteractor)).timeout_due()
        effects = await request.get(Effects)
        for timeout in timeouts:
            await effects.info_timed_out(timeout)


async def remind_info(container: AsyncContainer) -> None:
    """One message to the buyer 2 hours before that refund."""
    async with container() as request:
        orders = await (await request.get(InfoRequestInteractor)).remind_due()
        effects = await request.get(Effects)
        for order in orders:
            await effects.info_reminder(order)


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
    _job(scheduler, container, release_unaccepted, "release_unaccepted", 60)
    _job(scheduler, container, remind_deadlines, "remind_deadlines", 60)
    _job(scheduler, container, agree_cancels, "agree_cancels", 60)
    _job(scheduler, container, time_out_info, "time_out_info", 60)
    _job(scheduler, container, remind_info, "remind_info", 60)
    _job(scheduler, container, auto_confirm, "auto_confirm", 60)
    _job(scheduler, container, remind_confirm, "remind_confirm", 60)
    _job(scheduler, container, resolve_disputes, "resolve_disputes", 60)
    _job(scheduler, container, remind_disputes, "remind_disputes", 60)
    _job(scheduler, container, requeue_stale, "requeue_stale", 300)
    _job(scheduler, container, release_holds, "release_holds", 600)
    _job(scheduler, container, request_reviews, "request_reviews", 300)
