from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import ForeignKey, Index
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
        ForeignKey("promo_codes.id", ondelete="SET NULL")
    )
    input_data: Mapped[DictStrAny] = mapped_column(default=dict, server_default="{}")
    status: Mapped[OrderStatus] = mapped_column(default=OrderStatus.awaiting_input)
    executor_id: Mapped[Optional[Int64]] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT")
    )
    assigned_at: Mapped[Optional[datetime]] = mapped_column()
    deadline_at: Mapped[Optional[datetime]] = mapped_column()
    ready_at: Mapped[Optional[datetime]] = mapped_column()
    completed_at: Mapped[Optional[datetime]] = mapped_column()
    hold_until: Mapped[Optional[datetime]] = mapped_column()
    review_due_at: Mapped[Optional[datetime]] = mapped_column()
    result: Mapped[Optional[DictStrAny]] = mapped_column()

    __table_args__ = (
        Index("ix_orders_status", "status"),
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
