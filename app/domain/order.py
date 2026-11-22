from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.order import OrderStatus
from app.utils.custom_types import DictStrAny, Int64, Money

from .base import Base
from .mixins.timestamp import NowFunc, TimestampMixin


class Order(Base, TimestampMixin):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Int64] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    variant_id: Mapped[int] = mapped_column(ForeignKey("product_variants.id", ondelete="RESTRICT"))
    snapshot: Mapped[DictStrAny] = mapped_column()
    price: Mapped[Money] = mapped_column()
    discount: Mapped[Money] = mapped_column(default=Decimal(0), server_default="0")
    promo_code_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("promo_codes.id", ondelete="RESTRICT")
    )
    input_data: Mapped[DictStrAny] = mapped_column(default=dict, server_default="{}")
    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.awaiting_input)
    executor_id: Mapped[Optional[Int64]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column()
    deadline_at: Mapped[Optional[datetime]] = mapped_column()
    # auto-assigned: the executor has to accept until then; the deadline starts at acceptance
    accept_until: Mapped[Optional[datetime]] = mapped_column()
    # the executor asked the buyer for data: the deadline clock is stopped since then
    paused_at: Mapped[Optional[datetime]] = mapped_column()
    ready_at: Mapped[Optional[datetime]] = mapped_column()
    completed_at: Mapped[Optional[datetime]] = mapped_column()
    hold_until: Mapped[Optional[datetime]] = mapped_column()
    review_due_at: Mapped[Optional[datetime]] = mapped_column()
    result: Mapped[Optional[DictStrAny]] = mapped_column()

    __table_args__ = (
        CheckConstraint("price >= 0", name="order_price_non_negative"),
        CheckConstraint("discount >= 0 AND discount <= price", name="order_discount_le_price"),
        CheckConstraint(
            "status NOT IN ('assigned', 'ready') OR executor_id IS NOT NULL",
            name="order_assigned_has_executor",
        ),
        Index("ix_orders_status", "status"),
        Index(
            "ix_orders_hold_due",
            "hold_until",
            postgresql_where=text("status = 'completed' AND hold_until IS NOT NULL"),
        ),
        Index(
            "ix_orders_review_due",
            "review_due_at",
            postgresql_where=text("status = 'completed' AND review_due_at IS NOT NULL"),
        ),
        Index(
            "ix_orders_accept_due",
            "accept_until",
            postgresql_where=text("status = 'assigned' AND accept_until IS NOT NULL"),
        ),
        Index(
            "ix_orders_paused",
            "paused_at",
            postgresql_where=text("status = 'assigned' AND paused_at IS NOT NULL"),
        ),
        Index("ix_orders_executor_status", "executor_id", "status"),
        Index("ix_orders_user_id", "user_id"),
    )


class OrderEvent(Base):
    __tablename__ = "order_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), index=True)
    actor_id: Mapped[Optional[Int64]] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    type: Mapped[str] = mapped_column()
    payload: Mapped[DictStrAny] = mapped_column(default=dict, server_default="{}")
    created_at: Mapped[datetime] = mapped_column(server_default=NowFunc)

    __table_args__ = (
        Index("ix_order_events_type_executor", "type", text("(payload->>'executor_id')")),
    )
