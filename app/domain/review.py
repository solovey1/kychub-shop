from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.custom_types import Int64

from .base import Base
from .mixins.timestamp import NowFunc


class OrderReview(Base):
    __tablename__ = "order_reviews"

    id: Mapped[int] = mapped_column(primary_key=True)
    order_id: Mapped[int] = mapped_column(ForeignKey("orders.id", ondelete="CASCADE"), unique=True)
    user_id: Mapped[Int64] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    executor_id: Mapped[Int64] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    score: Mapped[int] = mapped_column()
    comment: Mapped[Optional[str]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=NowFunc)

    __table_args__ = (CheckConstraint("score BETWEEN 1 AND 5", name="review_score_range"),)
