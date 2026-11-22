from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import String, and_, cast, exists, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.ports.repositories.admin import (
    AdminGateway,
    ExecutorRow,
    StatsData,
    TopProduct,
)
from app.domain.audit import AuditLog
from app.domain.base import Base
from app.domain.broadcast import Broadcast
from app.domain.catalog import (
    Category,
    Country,
    Product,
    ProductVariant,
    Service,
    StockUnit,
)
from app.domain.enums.broadcast import BroadcastStatus
from app.domain.enums.ledger import LedgerAccount, LedgerKind, WithdrawalStatus
from app.domain.enums.order import OrderStatus
from app.domain.enums.roles import Role
from app.domain.executor import ExecutorPermission, ExecutorProfile
from app.domain.ledger import LedgerEntry, Withdrawal
from app.domain.order import Order
from app.domain.promo import PromoCode, PromoCodeUsage
from app.domain.review import OrderReview
from app.domain.settings import Setting
from app.domain.user import User
from app.utils.time import datetime_now


@dataclass
class AdminRepository(AdminGateway):
    _session: AsyncSession

    async def get[T: Base](self, model: type[T], pk: object) -> T | None:
        return await self._session.get(model, pk)

    async def lock[T: Base](self, model: type[T], pk: object) -> T | None:
        return await self._session.get(model, pk, with_for_update=True, populate_existing=True)

    async def add(self, *items: Base) -> None:
        self._session.add_all(items)
        await self._session.flush()

    async def delete(self, item: Base) -> None:
        await self._session.delete(item)
        await self._session.flush()

    async def flush(self) -> None:
        await self._session.flush()

    async def audit(
        self, actor_id: int, action: str, target: str | None, payload: dict[str, Any]
    ) -> None:
        self._session.add(
            AuditLog(actor_id=actor_id, action=action, target=target, payload=payload)
        )
        await self._session.flush()

    # --- catalog
    async def categories(self) -> list[Category]:
        query = select(Category).order_by(Category.position, Category.id)
        return list(await self._session.scalars(query))

    async def category_counts(self) -> dict[int, tuple[int, int]]:
        counts: dict[int, tuple[int, int]] = {}
        children = (
            select(Category.parent_id, func.count())
            .where(Category.parent_id.is_not(None))
            .group_by(Category.parent_id)
        )
        for pid, n in (await self._session.execute(children)).all():
            counts[int(pid)] = (int(n), 0)
        products = select(Product.category_id, func.count()).group_by(Product.category_id)
        for cid, n in (await self._session.execute(products)).all():
            counts[int(cid)] = (counts.get(int(cid), (0, 0))[0], int(n))
        return counts

    async def products_of(self, category_id: int) -> list[tuple[Product, int, Decimal | None]]:
        query = (
            select(
                Product,
                func.count(ProductVariant.id),
                func.min(ProductVariant.price).filter(ProductVariant.is_active),
            )
            .outerjoin(ProductVariant, ProductVariant.product_id == Product.id)
            .where(Product.category_id == category_id)
            .group_by(Product.id)
            .order_by(Product.position, Product.id)
        )
        return [
            (p, int(n), None if price is None else Decimal(price))
            for p, n, price in (await self._session.execute(query)).all()
        ]

    async def variants_of(self, product_id: int) -> list[ProductVariant]:
        query = (
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.id)
        )
        return list(await self._session.scalars(query))

    async def free_stock(self, variant_ids: list[int]) -> dict[int, int]:
        if not variant_ids:
            return {}
        query = (
            select(StockUnit.variant_id, func.count())
            .where(
                StockUnit.variant_id.in_(variant_ids),
                StockUnit.sold_order_id.is_(None),
                StockUnit.is_unlimited.is_(False),
            )
            .group_by(StockUnit.variant_id)
        )
        found = {int(v): int(n) for v, n in (await self._session.execute(query)).all()}
        return {v: found.get(v, 0) for v in variant_ids}

    async def product_used(self, product_id: int) -> str | None:
        ordered = select(
            exists(
                select(Order.id)
                .join(ProductVariant, ProductVariant.id == Order.variant_id)
                .where(ProductVariant.product_id == product_id)
            )
        )
        if await self._session.scalar(ordered):
            return "has_orders"
        promo = select(exists(select(PromoCode.id).where(PromoCode.product_id == product_id)))
        return "has_promo" if await self._session.scalar(promo) else None

    async def variant_has_orders(self, variant_id: int) -> bool:
        query = select(exists(select(Order.id).where(Order.variant_id == variant_id)))
        return bool(await self._session.scalar(query))

    async def services(self) -> list[Service]:
        return list(await self._session.scalars(select(Service).order_by(Service.id)))

    async def service_products(self, service_id: int) -> int:
        query = select(func.count()).where(Product.service_id == service_id)
        return int(await self._session.scalar(query) or 0)

    async def service_by_code(self, code: str) -> Service | None:
        service: Service | None = await self._session.scalar(
            select(Service).where(Service.code == code)
        )
        return service

    async def countries(self) -> list[Country]:
        return list(await self._session.scalars(select(Country).order_by(Country.code)))

    async def country_used(self, code: str) -> bool:
        query = select(
            exists(select(ProductVariant.id).where(ProductVariant.country_code == code))
            | exists(
                select(ExecutorPermission.executor_id).where(
                    ExecutorPermission.country_code == code
                )
            )
        )
        return bool(await self._session.scalar(query))

    async def stock_recent(self, variant_id: int, limit: int) -> list[StockUnit]:
        query = (
            select(StockUnit)
            .where(
                StockUnit.variant_id == variant_id,
                StockUnit.sold_order_id.is_(None),
                StockUnit.is_unlimited.is_(False),
            )
            .order_by(StockUnit.id.desc())
            .limit(limit)
        )
        return list(await self._session.scalars(query))

    async def stock_unlimited(self, variant_id: int) -> StockUnit | None:
        query = select(StockUnit).where(
            and_(StockUnit.variant_id == variant_id, StockUnit.is_unlimited.is_(True))
        )
        unit: StockUnit | None = await self._session.scalar(query.limit(1))
        return unit

    async def stock_payloads(self, variant_id: int, payloads: list[str]) -> set[str]:
        if not payloads:
            return set()
        query = select(StockUnit.payload).where(
            StockUnit.variant_id == variant_id,
            StockUnit.sold_order_id.is_(None),
            StockUnit.payload.in_(payloads),
        )
        return set(await self._session.scalars(query))

    # --- people
    async def users_search(self, text: str, limit: int) -> list[User]:
        text = text.strip().lstrip("@")
        escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        match = (
            cast(User.id, String) == text
            if text.isdigit()
            else User.name.ilike(f"%{escaped}%", escape="\\")
        )
        query = select(User).where(match).order_by(User.id.desc()).limit(limit)
        return list(await self._session.scalars(query))

    async def orders_of_user(self, user_id: int, limit: int) -> list[Order]:
        query = (
            select(Order).where(Order.user_id == user_id).order_by(Order.id.desc()).limit(limit)
        )
        return list(await self._session.scalars(query))

    async def executor_rows(self) -> list[ExecutorRow]:
        mine = Order.executor_id == ExecutorProfile.user_id
        in_work = (
            select(func.count())
            .where(mine, Order.status.in_((OrderStatus.assigned, OrderStatus.ready)))
            .correlate(ExecutorProfile)
            .scalar_subquery()
        )
        done = (
            select(func.count())
            .where(mine, Order.status == OrderStatus.completed)
            .correlate(ExecutorProfile)
            .scalar_subquery()
        )
        score = (
            select(func.avg(OrderReview.score))
            .where(OrderReview.executor_id == ExecutorProfile.user_id)
            .correlate(ExecutorProfile)
            .scalar_subquery()
        )
        query = select(ExecutorProfile, in_work, done, score).order_by(ExecutorProfile.alias)
        return [
            ExecutorRow(p, int(w), int(d), None if a is None else float(a))
            for p, w, d, a in (await self._session.execute(query)).all()
        ]

    async def managers(self) -> list[User]:
        query = select(User).where(User.roles.op("&")(int(Role.MANAGER)) != 0).order_by(User.id)
        return list(await self._session.scalars(query))

    async def user_names(self, ids: list[int]) -> dict[int, str]:
        if not ids:
            return {}
        query = select(User.id, User.name).where(User.id.in_(ids))
        return {int(i): n for i, n in (await self._session.execute(query)).all()}

    async def executor_aliases(self, ids: list[int]) -> dict[int, str]:
        if not ids:
            return {}
        query = select(ExecutorProfile.user_id, ExecutorProfile.alias).where(
            ExecutorProfile.user_id.in_(ids)
        )
        return {int(i): a for i, a in (await self._session.execute(query)).all()}

    # --- orders
    async def orders_filtered(
        self,
        status: OrderStatus | None,
        product_id: int | None,
        user_id: int | None,
        executor_id: int | None,
        offset: int,
        limit: int,
    ) -> tuple[list[Order], int]:
        conditions = []
        if status is not None:
            conditions.append(Order.status == status)
        if user_id is not None:
            conditions.append(Order.user_id == user_id)
        if executor_id is not None:
            conditions.append(Order.executor_id == executor_id)
        if product_id is not None:
            conditions.append(
                Order.variant_id.in_(
                    select(ProductVariant.id).where(ProductVariant.product_id == product_id)
                )
            )
        count = select(func.count()).select_from(Order).where(*conditions)
        query = (
            select(Order).where(*conditions).order_by(Order.id.desc()).offset(offset).limit(limit)
        )
        return list(await self._session.scalars(query)), int(
            await self._session.scalar(count) or 0
        )

    async def entries_for_order(self, order_id: int) -> list[LedgerEntry]:
        query = (
            select(LedgerEntry).where(LedgerEntry.order_id == order_id).order_by(LedgerEntry.id)
        )
        return list(await self._session.scalars(query))

    async def assignable(
        self, service_id: int, country_code: str | None
    ) -> list[tuple[ExecutorProfile, int]]:
        permitted = select(ExecutorPermission.executor_id).where(
            ExecutorPermission.executor_id == ExecutorProfile.user_id,
            ExecutorPermission.service_id == service_id,
        )
        if country_code is not None:
            permitted = permitted.where(ExecutorPermission.country_code == country_code)
        load = (
            select(func.count())
            .where(
                Order.executor_id == ExecutorProfile.user_id,
                Order.status.in_((OrderStatus.assigned, OrderStatus.ready)),
            )
            .correlate(ExecutorProfile)
            .scalar_subquery()
        )
        query = (
            select(ExecutorProfile, load)
            .where(ExecutorProfile.is_active, exists(permitted.correlate(ExecutorProfile)))
            .order_by(ExecutorProfile.alias)
        )
        return [(p, int(n)) for p, n in (await self._session.execute(query)).all()]

    # --- money, promo
    async def withdrawals(self, status: WithdrawalStatus, limit: int) -> list[Withdrawal]:
        order = Withdrawal.id if status is WithdrawalStatus.pending else Withdrawal.id.desc()
        query = select(Withdrawal).where(Withdrawal.status == status).order_by(order).limit(limit)
        return list(await self._session.scalars(query))

    async def promos(self) -> list[PromoCode]:
        return list(await self._session.scalars(select(PromoCode).order_by(PromoCode.id.desc())))

    async def promo_by_code(self, code: str) -> PromoCode | None:
        found: PromoCode | None = await self._session.scalar(
            select(PromoCode).where(PromoCode.code == code)
        )
        return found

    async def promo_usages(self, promo_id: int, limit: int) -> list[PromoCodeUsage]:
        query = (
            select(PromoCodeUsage)
            .where(PromoCodeUsage.promo_code_id == promo_id)
            .order_by(PromoCodeUsage.id.desc())
            .limit(limit)
        )
        return list(await self._session.scalars(query))

    # --- broadcasts
    async def broadcasts(self, limit: int) -> list[Broadcast]:
        query = select(Broadcast).order_by(Broadcast.id.desc()).limit(limit)
        return list(await self._session.scalars(query))

    async def recipients_count(self) -> int:
        query = select(func.count()).select_from(User).where(User.blocked_at.is_(None))
        return int(await self._session.scalar(query) or 0)

    async def next_sending(self) -> Broadcast | None:
        query = (
            select(Broadcast)
            .where(Broadcast.status == BroadcastStatus.sending)
            .order_by(Broadcast.id)
            .limit(1)
        )
        found: Broadcast | None = await self._session.scalar(query)
        return found

    async def broadcast_batch(self, after_id: int, limit: int) -> list[int]:
        query = (
            select(User.id)
            .where(User.id > after_id, User.blocked_at.is_(None))
            .order_by(User.id)
            .limit(limit)
        )
        return [int(i) for i in await self._session.scalars(query)]

    async def mark_blocked(self, user_ids: list[int]) -> None:
        if user_ids:
            await self._session.execute(
                update(User).where(User.id.in_(user_ids)).values(blocked_at=datetime_now())
            )

    # --- statistics, settings, log
    async def stats(self, since: datetime) -> StatsData:
        session = self._session

        async def ledger(kind: LedgerKind, account: LedgerAccount, *, period: bool) -> Decimal:
            query = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.kind == kind, LedgerEntry.account == account
            )
            if period:
                query = query.where(LedgerEntry.created_at >= since)
            return Decimal(await session.scalar(query) or 0)

        async def balance(account: LedgerAccount) -> Decimal:
            query = select(func.coalesce(func.sum(LedgerEntry.amount), 0)).where(
                LedgerEntry.account == account
            )
            return Decimal(await session.scalar(query) or 0)

        main = LedgerAccount.main
        paid_out = await session.scalar(
            select(func.coalesce(func.sum(Withdrawal.amount), 0)).where(
                Withdrawal.status == WithdrawalStatus.paid, Withdrawal.processed_at >= since
            )
        )
        by_status = await session.execute(
            select(Order.status, func.count())
            .where(Order.created_at >= since)
            .group_by(Order.status)
        )
        revenue = func.sum(Order.price - Order.discount)
        top = await session.execute(
            select(Product.id, Product.title_i18n, func.count(Order.id), revenue)
            .join(ProductVariant, ProductVariant.product_id == Product.id)
            .join(Order, Order.variant_id == ProductVariant.id)
            .where(
                Order.created_at >= since,
                Order.status.not_in((OrderStatus.awaiting_input, OrderStatus.cancelled)),
            )
            .group_by(Product.id)
            .order_by(func.count(Order.id).desc(), revenue.desc())
            .limit(10)
        )
        return StatsData(
            revenue=-await ledger(LedgerKind.purchase, main, period=True),
            refunds=await ledger(LedgerKind.refund, main, period=True),
            topups=await ledger(LedgerKind.topup, main, period=True),
            paid_out=Decimal(paid_out or 0),
            orders={status.value: int(n) for status, n in by_status.all()},
            top=[TopProduct(int(i), t, int(n), Decimal(r or 0)) for i, t, n, r in top.all()],
            hold=await balance(LedgerAccount.executor_hold),
            available=await balance(LedgerAccount.executor_available),
            buyers=await balance(main),
            buyers_hold=await balance(LedgerAccount.buyer_hold),
        )

    async def set_setting(self, key: str, value: Any) -> None:
        row = await self._session.get(Setting, key)
        if row is None:
            self._session.add(Setting(key=key, value=value))
        else:
            row.value = value
        await self._session.flush()

    async def audit_rows(
        self, actor_id: int | None, action: str | None, limit: int
    ) -> list[tuple[AuditLog, str | None]]:
        query = (
            select(AuditLog, User.name)
            .outerjoin(User, User.id == AuditLog.actor_id)
            .order_by(AuditLog.id.desc())
            .limit(limit)
        )
        if actor_id is not None:
            query = query.where(AuditLog.actor_id == actor_id)
        if action:
            escaped = action.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.where(AuditLog.action.like(f"{escaped}%", escape="\\"))
        return [(row, name) for row, name in (await self._session.execute(query)).all()]

    async def audit_actions(self) -> list[str]:
        query = select(AuditLog.action).distinct().order_by(AuditLog.action)
        return list(await self._session.scalars(query))
