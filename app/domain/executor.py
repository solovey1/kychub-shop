from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, false, true
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.custom_types import Int64

from .base import Base
from .mixins.timestamp import TimestampMixin


class ExecutorProfile(Base, TimestampMixin):
    __tablename__ = "executor_profiles"

    user_id: Mapped[Int64] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    alias: Mapped[str] = mapped_column(unique=True)
    is_active: Mapped[bool] = mapped_column(default=True, server_default=true())
    # The executor's own switch: offline ones get no offers and no auto-assignments.
    is_online: Mapped[bool] = mapped_column(default=False, server_default=false())
    online_changed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    percent_override: Mapped[Optional[int]] = mapped_column()
    max_parallel_orders: Mapped[int] = mapped_column(default=1, server_default="1")
    # Payout wallet is set by the executor; payouts are a stub for now (spec 15b).
    payout_wallet: Mapped[Optional[str]] = mapped_column()

    __table_args__ = (
        CheckConstraint("max_parallel_orders >= 1", name="executor_parallel_positive"),
        CheckConstraint(
            "percent_override IS NULL OR percent_override BETWEEN 0 AND 100",
            name="executor_percent_range",
        ),
    )


class ExecutorPermission(Base):
    __tablename__ = "executor_permissions"

    executor_id: Mapped[Int64] = mapped_column(
        ForeignKey("executor_profiles.user_id", ondelete="CASCADE"), primary_key=True
    )
    service_id: Mapped[int] = mapped_column(
        ForeignKey("services.id", ondelete="CASCADE"), primary_key=True
    )
    country_code: Mapped[str] = mapped_column(
        String(2), ForeignKey("countries.code", ondelete="CASCADE"), primary_key=True
    )
