import logging
from datetime import timedelta
from typing import Final

from aiogram import Bot
from aiogram.fsm.storage.base import StorageKey
from aiogram.fsm.storage.redis import RedisStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dishka import AsyncContainer

from app.application.errors.base import AppError
from app.application.i18n_text import fmt_usd
from app.application.interactors.purchase import PurchaseInteractor
from app.application.interactors.topup import TopupInteractor
from app.domain.ledger import Payment
from app.infrastructure.telegram.notifier import Notifier
from app.presentation.telegram.keyboards.purchase import resume_markup

logger: Final = logging.getLogger(__name__)

PENDING_MAX_AGE: Final = timedelta(hours=24)


async def _checkout(request: AsyncContainer, user_id: int) -> tuple[bool, bool]:
    """(the user left a checkout screen open in the bot, his balance covers it now). The
    checkout is the FSM data of the purchase flow: variant, token, no input state."""
    storage = await request.get(RedisStorage)
    key = StorageKey((await request.get(Bot)).id, user_id, user_id)
    data = await storage.get_data(key)
    if not data.get("variant_id") or not data.get("purchase_token"):
        return False, False
    if await storage.get_state(key) is not None:
        return False, False
    try:
        quote = await (await request.get(PurchaseInteractor)).quote(
            user_id, data["variant_id"], data.get("promo_code")
        )
    except AppError:  # the product is gone: nothing to come back to
        return False, False
    return True, quote.total <= quote.balance


async def _notify(container: AsyncContainer, payment: Payment) -> None:
    """Tell the user in their language. A failed send never fails the job."""
    try:
        async with container() as request:
            resume, enough = await _checkout(request, payment.user_id)
            await (await request.get(Notifier)).send(
                payment.user_id,
                "messages-topup-done_resume" if enough else "messages-topup-done",
                (lambda tr: resume_markup(tr("buttons-resume_checkout"))) if resume else None,
                amount=fmt_usd(payment.amount),
            )
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
