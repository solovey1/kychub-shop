"""The money paths of an order that the buyer confirms, the timer confirms or support resolves.
Two sessions on two connections race for the same order, like two requests would."""

import asyncio
from collections.abc import AsyncIterator
from datetime import timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.application.errors.shop import OrderUnavailable
from app.application.interactors.auto_confirm import AutoConfirmInteractor
from app.application.interactors.cards import CardBuilder
from app.application.interactors.ledger import LedgerService
from app.application.interactors.order_review import OrderReviewInteractor
from app.application.interactors.payouts import order_ref
from app.domain.catalog import Category, Product, ProductVariant, Service
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.enums.order import OrderStatus
from app.domain.executor import ExecutorProfile
from app.domain.ledger import LedgerEntry
from app.domain.order import Order
from app.domain.settings import Setting
from app.domain.user import User
from app.infrastructure.postgres.repositories.catalog import CatalogRepository
from app.infrastructure.postgres.repositories.executors import ExecutorsRepository
from app.infrastructure.postgres.repositories.ledger import LedgerRepository
from app.infrastructure.postgres.repositories.orders import OrdersRepository
from app.infrastructure.postgres.repositories.settings import SettingsRepository
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW
from app.utils.time import datetime_now

BUYER = 910_201
EXECUTOR = 910_202
TOTAL = Decimal("7.00")
EARNING = Decimal("3.50")  # 50 % of 7.00


class Rig:
    """The interactors of one request: one session, one transaction."""

    def __init__(self, session: AsyncSession) -> None:
        def helper[T: Setting | Order | LedgerEntry | Category | ExecutorProfile](
            model: type[T],
        ) -> SqlRepositoryHelper[T]:
            return SqlRepositoryHelper(session, model)

        uow = UoW(session)
        self.session = session
        self.uow = uow
        self.orders = OrdersRepository(uow, helper(Order))
        self.ledger_gateway = LedgerRepository(helper(LedgerEntry))
        self.catalog = CatalogRepository(helper(Category))
        self.executors = ExecutorsRepository(uow, helper(ExecutorProfile))
        self.settings = SettingsRepository(helper(Setting))
        self.ledger = LedgerService(self.ledger_gateway)
        self.review = OrderReviewInteractor(
            uow,
            self.orders,
            self.catalog,
            self.executors,
            self.ledger,
            self.ledger_gateway,
            self.settings,
            CardBuilder(self.catalog, self.executors),
        )
        self.auto = AutoConfirmInteractor(uow, self.orders, self.settings, self.review)


class Env:
    def __init__(self, engine: AsyncEngine, order_id: int) -> None:
        self.engine = engine
        self.order_id = order_id

    async def balance(self, user_id: int, account: LedgerAccount) -> Decimal:
        async with AsyncSession(self.engine) as s:
            return await LedgerRepository(SqlRepositoryHelper(s, LedgerEntry)).balance(
                user_id, account
            )

    async def count(self, user_id: int, kind: LedgerKind) -> int:
        async with AsyncSession(self.engine) as s:
            query = select(func.count()).where(
                LedgerEntry.user_id == user_id, LedgerEntry.kind == kind
            )
            return int(await s.scalar(query) or 0)

    async def status(self) -> OrderStatus:
        async with AsyncSession(self.engine) as s:
            order = await s.get(Order, self.order_id, populate_existing=True)
            assert order is not None
            return order.status


@pytest_asyncio.fixture(loop_scope="session")
async def env(engine: AsyncEngine) -> AsyncIterator[Env]:
    """A buyer who paid 7.00 (held), and an executor who handed the order in 25 hours ago."""
    ids: dict[str, int] = {}
    async with AsyncSession(engine) as s:
        for uid in (BUYER, EXECUTOR):
            s.add(User(id=uid, name="t", language="ru", language_code=None))
        category = Category(title_i18n={"ru": "c"})
        service = Service(code="t-deal", title="t", deadline_minutes=60, executor_percent=50)
        s.add_all([category, service])
        await s.flush()
        s.add(ExecutorProfile(user_id=EXECUTOR, alias="t-deal-alias"))
        product = Product(
            category_id=category.id,
            service_id=service.id,
            title_i18n={"ru": "p"},
            fulfillment_type="executor",
        )
        s.add(product)
        await s.flush()
        variant = ProductVariant(product_id=product.id, price=TOTAL)
        s.add(variant)
        await s.flush()
        now = datetime_now()
        order = Order(
            user_id=BUYER,
            variant_id=variant.id,
            snapshot={},
            price=TOTAL,
            status=OrderStatus.ready,
            executor_id=EXECUTOR,
            assigned_at=now - timedelta(hours=26),
            deadline_at=now - timedelta(hours=25),
            ready_at=now - timedelta(hours=25),
            result={"text": "done", "files": []},
        )
        s.add(order)
        await s.flush()
        ids.update(
            category=category.id,
            service=service.id,
            product=product.id,
            variant=variant.id,
            order=order.id,
        )
        ledger = LedgerService(LedgerRepository(SqlRepositoryHelper(s, LedgerEntry)))
        ref = order_ref(order)
        await ledger.post(BUYER, LedgerAccount.main, Decimal("10.00"), LedgerKind.topup)
        await ledger.post(
            BUYER, LedgerAccount.main, -TOTAL, LedgerKind.purchase, order_id=order.id, ref="p:1"
        )
        await ledger.post(
            BUYER,
            LedgerAccount.buyer_hold,
            TOTAL,
            LedgerKind.order_hold,
            order_id=order.id,
            ref=ref,
        )
        await s.commit()
    try:
        yield Env(engine, ids["order"])
    finally:
        async with AsyncSession(engine) as s:
            await s.execute(delete(LedgerEntry).where(LedgerEntry.user_id.in_((BUYER, EXECUTOR))))
            await s.execute(delete(Order).where(Order.user_id == BUYER))
            await s.execute(delete(ProductVariant).where(ProductVariant.id == ids["variant"]))
            await s.execute(delete(Product).where(Product.id == ids["product"]))
            await s.execute(delete(ExecutorProfile).where(ExecutorProfile.user_id == EXECUTOR))
            await s.execute(delete(Service).where(Service.id == ids["service"]))
            await s.execute(delete(Category).where(Category.id == ids["category"]))
            await s.execute(delete(User).where(User.id.in_((BUYER, EXECUTOR))))
            await s.commit()


async def _buyer_confirms(engine: AsyncEngine, order_id: int) -> bool:
    async with AsyncSession(engine) as s:
        try:
            await Rig(s).review.confirm_by_buyer(BUYER, order_id)
        except OrderUnavailable:
            return False
        return True


async def _timer_confirms(engine: AsyncEngine) -> int:
    async with AsyncSession(engine) as s:
        return len(await Rig(s).auto.confirm_due())


@pytest.mark.db
async def test_buyer_and_timer_confirm_at_once_pay_once(env: Env) -> None:
    bought, timed = await asyncio.gather(
        _buyer_confirms(env.engine, env.order_id), _timer_confirms(env.engine)
    )
    assert int(bought) + timed == 1  # exactly one of them completed the order
    assert await env.status() is OrderStatus.completed
    assert await env.count(BUYER, LedgerKind.order_capture) == 1
    assert await env.count(EXECUTOR, LedgerKind.executor_earning) == 1
    assert await env.balance(BUYER, LedgerAccount.buyer_hold) == 0
    assert await env.balance(BUYER, LedgerAccount.main) == Decimal("3.00")
    assert await env.balance(EXECUTOR, LedgerAccount.executor_hold) == EARNING


@pytest.mark.db
async def test_somebody_else_cannot_confirm(env: Env) -> None:
    async with AsyncSession(env.engine) as s:
        with pytest.raises(OrderUnavailable):
            await Rig(s).review.confirm_by_buyer(EXECUTOR, env.order_id)
    assert await env.status() is OrderStatus.ready
