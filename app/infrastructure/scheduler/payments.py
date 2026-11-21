import logging
from datetime import timedelta
from typing import Final

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError
from aiogram_i18n.cores import FluentRuntimeCore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dishka import AsyncContainer

from app.application.i18n_text import fmt_usd
from app.application.interactors.topup import TopupInteractor
from app.application.ports.repositories.users import UsersGateway
from app.const import DEFAULT_LOCALE
from app.domain.ledger import Payment

logger: Final = logging.getLogger(__name__)

PENDING_MAX_AGE: Final = timedelta(hours=24)


async def _notify(container: AsyncContainer, payment: Payment) -> None:
    """Tell the user in their language. A failed send never fails the job."""
    try:
        async with container() as request:
            user = await (await request.get(UsersGateway)).get(payment.user_id)
            core = await request.get(FluentRuntimeCore)
            bot = await request.get(Bot)
            text = core.get(
                "messages-topup-done",
                user.language if user else DEFAULT_LOCALE,
                amount=fmt_usd(payment.amount),
            )
            await bot.send_message(payment.user_id, text)
    except TelegramAPIError:
        logger.info("could not notify user %s about payment %s", payment.user_id, payment.id)
    except Exception:
        logger.exception("notification about payment %s failed", payment.id)


async def poll_payments(container: AsyncContainer) -> None:
    """Unpaid invoices younger than 24 h; each one in its own transaction scope."""
    async with container() as request:
        ids = [p.id for p in await (await request.get(TopupInteractor)).pending(PENDING_MAX_AGE)]
    for payment_id in ids:
        try:
            async with container() as request:
                payment, credited = await (await request.get(TopupInteractor)).sync(payment_id)
        except Exception:
            logger.exception("polling payment %s failed", payment_id)
            continue
        if credited:
            logger.info("payment %s credited", payment_id)
            await _notify(container, payment)


async def retry_unfulfilled(container: AsyncContainer) -> None:
    """Paid but not credited (crash between steps, manual status change)."""
    async with container() as request:
        ids = [p.id for p in await (await request.get(TopupInteractor)).unfulfilled_success()]
    for payment_id in ids:
        try:
            async with container() as request:
                topup = await request.get(TopupInteractor)
                credited = await topup.credit(payment_id)
                payment = await topup.get(payment_id)
        except Exception:
            logger.exception("crediting payment %s failed", payment_id)
            continue
        if credited:
            logger.info("payment %s credited on retry", payment_id)
            await _notify(container, payment)


def register(scheduler: AsyncIOScheduler, container: AsyncContainer) -> None:
    scheduler.add_job(
        poll_payments,
        "interval",
        seconds=60,
        args=[container],
        id="poll_payments",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
    scheduler.add_job(
        retry_unfulfilled,
        "interval",
        seconds=180,
        args=[container],
        id="retry_unfulfilled",
        max_instances=1,
        coalesce=True,
        replace_existing=True,
    )
