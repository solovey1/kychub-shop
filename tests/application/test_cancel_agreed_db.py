"""Cancel by agreement: the executor's «yes» and the one-hour timer race for one order."""

import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.application.errors.shop import Conflict
from app.application.interactors.cancel_request import CancelRequestInteractor
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.enums.order import OrderStatus
from tests.application import test_deal_money_db as deal
from tests.application.test_deal_money_db import BUYER, EXECUTOR, Env, Rig

env = deal.env  # the same buyer, executor and order the deal tests use


def _cancels(rig: Rig) -> CancelRequestInteractor:
    return CancelRequestInteractor(rig.uow, rig.orders, rig.disputes, rig.review)


async def _asked_an_hour_ago(env: Env) -> None:
    """The order is in work, the buyer asked to cancel more than an hour ago."""
    async with AsyncSession(env.engine) as s:
        await s.execute(
            text(
                "UPDATE orders SET status = 'assigned', ready_at = NULL, "
                "deadline_at = now() + interval '1 hour' WHERE id = :id"
            ),
            {"id": env.order_id},
        )
        await s.commit()
    async with AsyncSession(env.engine) as s:
        await _cancels(Rig(s)).request(BUYER, env.order_id)
    async with AsyncSession(env.engine) as s:
        await s.execute(
            text(
                "UPDATE order_events SET created_at = now() - interval '61 minutes' "
                "WHERE type = 'cancel_requested'"
            )
        )
        await s.commit()


async def _executor_agrees(env: Env) -> bool:
    async with AsyncSession(env.engine) as s:
        try:
            await _cancels(Rig(s)).answer(EXECUTOR, env.order_id, 1, True)
        except Conflict:
            return False
        return True


async def _timer_agrees(engine: AsyncEngine) -> int:
    async with AsyncSession(engine) as s:
        return len(await _cancels(Rig(s)).agree_due())


@pytest.mark.db
async def test_executor_yes_and_the_timer_at_once_refund_once(env: Env) -> None:
    await _asked_an_hour_ago(env)
    said, timed = await asyncio.gather(_executor_agrees(env), _timer_agrees(env.engine))
    assert int(said) + timed == 1  # exactly one of them cancelled the order
    assert await _timer_agrees(env.engine) == 0
    assert await env.status() is OrderStatus.refunded
    assert await env.count(BUYER, LedgerKind.refund) == 1
    assert await env.count(BUYER, LedgerKind.order_release) == 1
    assert await env.count(BUYER, LedgerKind.order_capture) == 0
    assert await env.balance(BUYER, LedgerAccount.main) == Decimal("10.00")
    assert await env.balance(BUYER, LedgerAccount.buyer_hold) == 0
