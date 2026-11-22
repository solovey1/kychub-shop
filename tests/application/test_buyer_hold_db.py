from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.application.interactors.ledger import LedgerService
from app.application.interactors.payouts import capture_buyer, order_ref, refund_buyer
from app.domain.catalog import Category, Product, ProductVariant
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.enums.order import OrderStatus
from app.domain.ledger import LedgerEntry
from app.domain.order import Order
from app.domain.user import User
from app.infrastructure.postgres.repositories.ledger import LedgerRepository
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper

USER_ID = 910_101
TOTAL = Decimal("7.00")


class Env:
    def __init__(self, session: AsyncSession, order: Order) -> None:
        self.session = session
        self.order = order
        self.gateway = LedgerRepository(SqlRepositoryHelper(session, LedgerEntry))
        self.ledger = LedgerService(self.gateway)

    async def balance(self, account: LedgerAccount) -> Decimal:
        return await self.gateway.balance(USER_ID, account)

    async def count(self, kind: LedgerKind) -> int:
        query = select(func.count()).where(
            LedgerEntry.user_id == USER_ID, LedgerEntry.kind == kind
        )
        return int(await self.session.scalar(query) or 0)


@pytest_asyncio.fixture(loop_scope="session")
async def env(engine: AsyncEngine) -> AsyncIterator[Env]:
    """A buyer with 10.00, who bought for 7.00 an order that waits for an executor: the money is
    moved to the hold exactly like PurchaseInteractor does."""
    async with AsyncSession(engine) as s:
        s.add(User(id=USER_ID, name="t", language="ru", language_code=None))
        category = Category(title_i18n={"ru": "c"})
        s.add(category)
        await s.flush()
        product = Product(
            category_id=category.id, title_i18n={"ru": "p"}, fulfillment_type="executor"
        )
        s.add(product)
        await s.flush()
        variant = ProductVariant(product_id=product.id, price=TOTAL)
        s.add(variant)
        await s.flush()
        order = Order(
            user_id=USER_ID,
            variant_id=variant.id,
            snapshot={},
            price=TOTAL,
            status=OrderStatus.in_queue,
        )
        s.add(order)
        await s.flush()
        e = Env(s, order)
        ref, oid = order_ref(order), order.id
        await e.ledger.post(USER_ID, LedgerAccount.main, Decimal("10.00"), LedgerKind.topup)
        await e.ledger.post(
            USER_ID, LedgerAccount.main, -TOTAL, LedgerKind.purchase, order_id=oid, ref="p:1"
        )
        await e.ledger.post(
            USER_ID, LedgerAccount.buyer_hold, TOTAL, LedgerKind.order_hold, order_id=oid, ref=ref
        )
        assert await e.balance(LedgerAccount.main) == Decimal("3.00")
        assert await e.balance(LedgerAccount.buyer_hold) == TOTAL
        try:
            yield e
        finally:
            await s.rollback()
            await s.execute(delete(LedgerEntry).where(LedgerEntry.user_id == USER_ID))
            await s.execute(delete(Order).where(Order.user_id == USER_ID))
            await s.execute(delete(ProductVariant).where(ProductVariant.id == variant.id))
            await s.execute(delete(Product).where(Product.id == product.id))
            await s.execute(delete(Category).where(Category.id == category.id))
            await s.execute(delete(User).where(User.id == USER_ID))
            await s.commit()


@pytest.mark.db
async def test_double_refund_before_capture(env: Env) -> None:
    for _ in range(2):
        assert await refund_buyer(env.ledger, env.gateway, env.order) == TOTAL
    assert await env.balance(LedgerAccount.main) == Decimal("10.00")
    assert await env.balance(LedgerAccount.buyer_hold) == 0
    assert await env.count(LedgerKind.order_release) == 1
    assert await env.count(LedgerKind.refund) == 1
    # a done-after-refund call must not spend the released money again
    assert await capture_buyer(env.ledger, env.gateway, env.order) is False
    assert await env.count(LedgerKind.order_capture) == 0


@pytest.mark.db
async def test_refund_after_capture_leaves_the_hold_alone(env: Env) -> None:
    assert await capture_buyer(env.ledger, env.gateway, env.order) is True
    assert await env.balance(LedgerAccount.buyer_hold) == 0
    for _ in range(2):
        await refund_buyer(env.ledger, env.gateway, env.order)
    assert await env.balance(LedgerAccount.main) == Decimal("10.00")
    assert await env.balance(LedgerAccount.buyer_hold) == 0
    assert await env.count(LedgerKind.order_release) == 0
    assert await env.count(LedgerKind.refund) == 1


@pytest.mark.db
async def test_capture_twice_posts_once(env: Env) -> None:
    assert await capture_buyer(env.ledger, env.gateway, env.order) is True
    assert await capture_buyer(env.ledger, env.gateway, env.order) is False
    assert await env.count(LedgerKind.order_capture) == 1
    assert await env.balance(LedgerAccount.buyer_hold) == 0
    assert await env.balance(LedgerAccount.main) == Decimal("3.00")
