from collections.abc import Collection
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ColumnElement, cast, exists, func, select
from sqlalchemy.dialects.postgresql import JSONB

from app.application.ports.repositories.orders import OrdersGateway
from app.domain.catalog import Category, Country, Product, ProductVariant
from app.domain.dispute import Dispute
from app.domain.enums.ledger import LedgerAccount, LedgerKind
from app.domain.enums.order import OrderStatus
from app.domain.ledger import LedgerEntry
from app.domain.order import Order, OrderEvent
from app.infrastructure.postgres.repository_helper import SqlRepositoryHelper
from app.infrastructure.postgres.uow import UoW


def _no_dispute() -> ColumnElement[bool]:
    """The order has no open dispute: its clocks (deadline, auto-confirm) run."""
    return ~exists().where(Dispute.order_id == Order.id, Dispute.resolved_at.is_(None))


@dataclass
class OrdersRepository(OrdersGateway):
    _uow: UoW
    _helper: SqlRepositoryHelper[Order]

    async def add(self, order: Order) -> None:
        await self._uow.flush_coded(order)

    async def code(self, order_id: int) -> str:
        return await self._helper.session.scalar(
            select(Order.code).where(Order.id == order_id)
        ) or str(order_id)

    async def add_event(self, event: OrderEvent) -> None:
        await self._uow.flush(event)

    async def get_for_user(self, user_id: int, order_id: int) -> Order | None:
        return await self._helper.get_one(Order.id == order_id, Order.user_id == user_id)

    async def list_for_user(self, user_id: int, offset: int, limit: int) -> list[Order]:
        query = (
            select(Order)
            .where(Order.user_id == user_id)
            .order_by(Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(await self._helper.session.scalars(query))

    async def count_for_user(self, user_id: int) -> int:
        return await self._helper.count(Order.user_id == user_id)

    async def active_for_user(self, user_id: int) -> list[Order]:
        query = select(Order).where(
            Order.user_id == user_id,
            Order.status.in_(
                (OrderStatus.paid, OrderStatus.in_queue, OrderStatus.assigned, OrderStatus.ready)
            ),
        )
        return list(await self._helper.session.scalars(query))

    async def events(self, order_id: int) -> list[OrderEvent]:
        query = select(OrderEvent).where(OrderEvent.order_id == order_id).order_by(OrderEvent.id)
        return list(await self._helper.session.scalars(query))

    async def in_work_for_executor(self, executor_id: int) -> list[Order]:
        query = select(Order).where(
            Order.executor_id == executor_id,
            Order.status.in_((OrderStatus.assigned, OrderStatus.ready)),
        )
        return list(await self._helper.session.scalars(query))

    async def extension_events(
        self, order_ids: Collection[int], types: Collection[str]
    ) -> dict[int, list[OrderEvent]]:
        found: dict[int, list[OrderEvent]] = {}
        if not order_ids:
            return found
        query = (
            select(OrderEvent)
            .where(OrderEvent.order_id.in_(order_ids), OrderEvent.type.in_(types))
            .order_by(OrderEvent.id)
        )
        for event in await self._helper.session.scalars(query):
            found.setdefault(event.order_id, []).append(event)
        return found

    async def recent_with_input(self, user_id: int, product_id: int, limit: int) -> list[Order]:
        query = (
            select(Order)
            .join(ProductVariant, ProductVariant.id == Order.variant_id)
            .where(
                Order.user_id == user_id,
                ProductVariant.product_id == product_id,
                Order.input_data != cast({}, JSONB),
            )
            .order_by(Order.id.desc())
            .limit(limit)
        )
        return list(await self._helper.session.scalars(query))

    async def reorderable(
        self, user_id: int, limit: int
    ) -> list[tuple[ProductVariant, Product, Country | None]]:
        last = func.max(Order.id)
        recent = (
            select(Order.variant_id.label("variant_id"), last.label("last_id"))
            .where(
                Order.user_id == user_id,
                Order.status.notin_((OrderStatus.awaiting_input, OrderStatus.cancelled)),
            )
            .group_by(Order.variant_id)
            .subquery()
        )
        query = (
            select(ProductVariant, Product, Country)
            .join(recent, recent.c.variant_id == ProductVariant.id)
            .join(Product, Product.id == ProductVariant.product_id)
            .join(Category, Category.id == Product.category_id)
            .outerjoin(Country, Country.code == ProductVariant.country_code)
            .where(ProductVariant.is_active, Product.is_active, Category.is_active)
            .order_by(recent.c.last_id.desc())
            .limit(limit)
        )
        return [(v, p, c) for v, p, c in (await self._helper.session.execute(query)).all()]

    async def variant_orderable(self, variant_id: int) -> bool:
        query = (
            select(ProductVariant.id)
            .join(Product, Product.id == ProductVariant.product_id)
            .join(Category, Category.id == Product.category_id)
            .where(
                ProductVariant.id == variant_id,
                ProductVariant.is_active,
                Product.is_active,
                Category.is_active,
            )
        )
        return await self._helper.session.scalar(query) is not None

    async def find_by_token(self, user_id: int, token: str) -> Order | None:
        return await self._helper.get_one(
            Order.user_id == user_id, Order.snapshot.op("->>")("token") == token
        )

    async def get(self, order_id: int) -> Order | None:
        return await self._helper.get_one(Order.id == order_id)

    async def get_for_update(self, order_id: int) -> Order | None:
        query = (
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        order: Order | None = await self._helper.session.scalar(query)
        return order

    async def has_event(self, order_id: int, event_type: str) -> bool:
        query = select(OrderEvent.id).where(
            OrderEvent.order_id == order_id, OrderEvent.type == event_type
        )
        return await self._helper.session.scalar(query.limit(1)) is not None

    async def excluded_executor_ids(self, order_id: int) -> set[int]:
        query = select(OrderEvent.payload.op("->>")("executor_id")).where(
            OrderEvent.order_id == order_id, OrderEvent.type.in_(("refused", "overdue", "ignored"))
        )
        return {int(v) for v in await self._helper.session.scalars(query) if v is not None}

    async def overdue_ids(self, now: datetime) -> list[int]:
        query = (
            select(Order.id)
            .where(
                Order.status == OrderStatus.assigned,
                Order.deadline_at < now,
                Order.paused_at.is_(None),  # the clock stands while the buyer is asked
                _no_dispute(),
            )
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))

    async def paused_before(self, cutoff: datetime) -> list[int]:
        query = (
            select(Order.id)
            .where(
                Order.status == OrderStatus.assigned,
                Order.paused_at < cutoff,
                _no_dispute(),
            )
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))

    async def unaccepted_ids(self, now: datetime) -> list[int]:
        query = (
            select(Order.id)
            .where(Order.status == OrderStatus.assigned, Order.accept_until < now, _no_dispute())
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))

    async def cancel_request_ids(self, cutoff: datetime) -> list[int]:
        asked = exists().where(
            OrderEvent.order_id == Order.id,
            OrderEvent.type == "cancel_requested",
            OrderEvent.created_at < cutoff,
        )
        query = (
            select(Order.id)
            .where(Order.status == OrderStatus.assigned, asked, _no_dispute())
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))

    async def assigned_with_deadline(self, now: datetime) -> list[Order]:
        query = (
            select(Order)
            .where(
                Order.status == OrderStatus.assigned,
                Order.deadline_at >= now,
                Order.paused_at.is_(None),
                _no_dispute(),
            )
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))

    async def ready_before(self, cutoff: datetime) -> list[Order]:
        query = (
            select(Order)
            .where(Order.status == OrderStatus.ready, Order.ready_at < cutoff, _no_dispute())
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))

    async def stale_ids(self, cutoff: datetime) -> list[int]:
        last_dispatch = (
            select(func.max(OrderEvent.created_at))
            .where(OrderEvent.order_id == Order.id, OrderEvent.type == "dispatch")
            .scalar_subquery()
        )
        query = (
            select(Order.id)
            .where(
                Order.status == OrderStatus.in_queue,
                Order.executor_id.is_(None),
                func.coalesce(last_dispatch, Order.updated_at) < cutoff,
            )
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))

    async def list_for_executor(self, executor_id: int, offset: int, limit: int) -> list[Order]:
        query = (
            select(Order)
            .where(Order.executor_id == executor_id)
            .order_by(Order.id.desc())
            .offset(offset)
            .limit(limit)
        )
        return list(await self._helper.session.scalars(query))

    async def count_for_executor(self, executor_id: int) -> int:
        return await self._helper.count(Order.executor_id == executor_id)

    async def held_earnings(self, executor_id: int) -> list[tuple[datetime, Decimal]]:
        query = (
            select(Order.hold_until, LedgerEntry.amount)
            .join(
                LedgerEntry,
                (LedgerEntry.user_id == Order.executor_id)
                & (LedgerEntry.ref == func.concat("order:", Order.id)),
            )
            .where(
                Order.executor_id == executor_id,
                Order.status == OrderStatus.completed,
                Order.hold_until.is_not(None),
                LedgerEntry.account == LedgerAccount.executor_hold,
                LedgerEntry.kind == LedgerKind.executor_earning,
            )
            .order_by(Order.hold_until)
        )
        return [(at, amount) for at, amount in (await self._helper.session.execute(query)).all()]

    async def hold_due_ids(self, now: datetime) -> list[int]:
        def entry(kind: LedgerKind) -> ColumnElement[bool]:
            return exists().where(
                LedgerEntry.user_id == Order.executor_id,
                LedgerEntry.account == LedgerAccount.executor_hold,
                LedgerEntry.kind == kind,
                LedgerEntry.ref == func.concat("order:", Order.id),
            )

        query = (
            select(Order.id)
            .where(
                Order.status == OrderStatus.completed,
                Order.hold_until <= now,
                entry(LedgerKind.executor_earning),
                ~entry(LedgerKind.hold_release),
            )
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))

    async def review_due_ids(self, now: datetime) -> list[int]:
        asked = exists().where(
            OrderEvent.order_id == Order.id, OrderEvent.type == "review_requested"
        )
        query = (
            select(Order.id)
            .where(
                Order.status == OrderStatus.completed,
                Order.executor_id.is_not(None),
                Order.review_due_at <= now,
                ~asked,
            )
            .order_by(Order.id)
        )
        return list(await self._helper.session.scalars(query))

    async def queue(self, limit: int) -> list[Order]:
        query = (
            select(Order)
            .where(Order.status == OrderStatus.in_queue, Order.executor_id.is_(None))
            .order_by(Order.id)
            .limit(limit)
        )
        return list(await self._helper.session.scalars(query))

    async def list_by_status(self, status: OrderStatus, limit: int) -> list[Order]:
        query = select(Order).where(Order.status == status).order_by(Order.id.desc()).limit(limit)
        return list(await self._helper.session.scalars(query))
