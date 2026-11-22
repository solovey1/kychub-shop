"""«Need data»: the buyer's answer and the 24 h refund of an unanswered question race."""

import asyncio
from decimal import Decimal

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.application.errors.shop import ChatForbidden
from app.application.interactors.conversations import ConversationInteractor
from app.application.interactors.info_request import InfoRequestInteractor
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.enums.order import OrderStatus
from app.domain.order import Order
from app.domain.support import Ticket
from app.domain.user import User
from app.infrastructure.postgres.repositories.support import SupportRepository
from app.infrastructure.postgres.repositories.users import UsersRepository
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from tests.application import test_deal_money_db as deal
from tests.application.test_deal_money_db import BUYER, Env, Rig

env = deal.env  # the same buyer, executor and order the deal tests use


def _chat(rig: Rig) -> ConversationInteractor:
    return ConversationInteractor(
        rig.uow,
        SupportRepository(rig.uow, SqlRepositoryHelper(rig.session, Ticket)),
        rig.orders,
        UsersRepository(rig.uow, SqlRepositoryHelper(rig.session, User)),
        rig.executors,
        rig.disputes,
    )


def _info(rig: Rig) -> InfoRequestInteractor:
    return InfoRequestInteractor(rig.uow, rig.orders, rig.disputes, _chat(rig), rig.review)


async def _asked_a_day_ago(env: Env) -> int:
    """The order is in work, the executor asked a question 24 h and a minute ago. Returns the id
    of the order chat."""
    async with AsyncSession(env.engine) as s:
        await s.execute(
            text(
                "UPDATE orders SET status = 'assigned', ready_at = NULL, "
                "deadline_at = now() + interval '1 hour', "
                "paused_at = now() - interval '24 hours 1 minute' WHERE id = :id"
            ),
            {"id": env.order_id},
        )
        await s.execute(
            text(
                "INSERT INTO order_events (order_id, type, payload) "
                "VALUES (:id, 'info_requested', '{\"question\": \"which email?\"}')"
            ),
            {"id": env.order_id},
        )
        await s.commit()
    async with AsyncSession(env.engine, expire_on_commit=False) as s:
        conversation = await _chat(Rig(s)).order_conversation(BUYER, env.order_id)
        return conversation.id


async def _buyer_answers(env: Env, conversation_id: int) -> bool:
    async with AsyncSession(env.engine, expire_on_commit=False) as s:
        try:
            await _chat(Rig(s)).post(conversation_id, BUYER, "the second one", None)
        except ChatForbidden:  # the timer refunded the order first: the chat is closed
            return False
        return True


async def _timer_refunds(engine: AsyncEngine) -> int:
    async with AsyncSession(engine) as s:
        return len(await _info(Rig(s)).timeout_due())


async def _paused(env: Env) -> bool:
    async with AsyncSession(env.engine) as s:
        order = await s.get(Order, env.order_id, populate_existing=True)
        assert order is not None
        return order.paused_at is not None


async def _no_refund(env: Env) -> None:
    assert await env.status() is OrderStatus.assigned
    assert not await _paused(env)
    assert await env.count(BUYER, LedgerKind.refund) == 0
    assert await env.balance(BUYER, LedgerAccount.buyer_hold) == deal.TOTAL


@pytest.mark.db
async def test_answer_and_the_timeout_at_once_never_refund_twice(env: Env) -> None:
    conversation_id = await _asked_a_day_ago(env)
    answered, refunded = await asyncio.gather(
        _buyer_answers(env, conversation_id), _timer_refunds(env.engine)
    )
    assert int(answered) + refunded == 1  # one of them wins, never both
    assert await _timer_refunds(env.engine) == 0
    if answered:
        await _no_refund(env)
    else:
        assert await env.status() is OrderStatus.refunded
        assert await env.count(BUYER, LedgerKind.refund) == 1
        assert await env.balance(BUYER, LedgerAccount.main) == Decimal("10.00")
        assert await env.balance(BUYER, LedgerAccount.buyer_hold) == 0


@pytest.mark.db
async def test_answer_first_means_no_refund_and_more_time(env: Env) -> None:
    conversation_id = await _asked_a_day_ago(env)
    assert await _buyer_answers(env, conversation_id)
    assert await _timer_refunds(env.engine) == 0
    await _no_refund(env)
    async with AsyncSession(env.engine) as s:
        order = await s.get(Order, env.order_id, populate_existing=True)
        assert order is not None and order.deadline_at is not None
        # the 24 h of the pause were added to the hour that was left
        gained = await s.scalar(text("SELECT :d - now()").bindparams(d=order.deadline_at))
        assert gained is not None and gained.total_seconds() > 24 * 3600
