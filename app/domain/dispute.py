from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.dispute import DisputeResolution
from app.utils.custom_types import Int64

from .base import Base
from .mixins.timestamp import NowFunc


class Dispute(Base):
    """«Call support» on an order: one open dispute per order. While it is open the executor's
    deadline and the auto-confirmation do not run; `awaiting_*` is the side that has to answer
    in the order chat before the deadline, or the dispute resolves itself against it."""

    __tablename__ = "disputes"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"))
    opened_by: Mapped[Int64] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    opened_role: Mapped[str] = mapped_column(String(16))  # DisputeSide
    reason: Mapped[Optional[str]] = mapped_column(String(500))
    opened_at: Mapped[datetime] = mapped_column(server_default=NowFunc)
    awaiting_role: Mapped[Optional[str]] = mapped_column(String(16))  # DisputeSide
    awaiting_until: Mapped[Optional[datetime]] = mapped_column()
    resolved_at: Mapped[Optional[datetime]] = mapped_column()
    resolution: Mapped[Optional[DisputeResolution]] = mapped_column()
    resolved_by: Mapped[Optional[Int64]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )  # None: the system

    __table_args__ = (
        CheckConstraint("opened_role IN ('buyer', 'executor')", name="dispute_opened_role"),
        CheckConstraint(
            "awaiting_role IS NULL OR awaiting_role IN ('buyer', 'executor')",
            name="dispute_awaiting_role",
        ),
        CheckConstraint(
            "(resolved_at IS NULL) = (resolution IS NULL)", name="dispute_resolved_together"
        ),
        # one open dispute per order
        Index(
            "uq_disputes_open",
            "order_id",
            unique=True,
            postgresql_where=text("resolved_at IS NULL"),
        ),
        Index(
            "ix_disputes_awaiting_until",
            "awaiting_until",
            postgresql_where=text("resolved_at IS NULL AND awaiting_until IS NOT NULL"),
        ),
    )
