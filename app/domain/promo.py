from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, false, true
from sqlalchemy.orm import Mapped, mapped_column

from app.utils.custom_types import Int64, Money

from .base import Base
from .mixins.timestamp import NowFunc, TimestampMixin


class PromoCode(Base, TimestampMixin):
    __tablename__ = "promo_codes"

    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(unique=True)  # stored UPPER
    discount_percent: Mapped[Optional[int]] = mapped_column()
    discount_amount: Mapped[Optional[Money]] = mapped_column()
    bonus_amount: Mapped[Optional[Money]] = mapped_column()
    usage_limit: Mapped[Optional[int]] = mapped_column()
    times_used: Mapped[int] = mapped_column(default=0, server_default="0")
    expires_at: Mapped[Optional[datetime]] = mapped_column()
    product_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE")
    )
    min_amount: Mapped[Optional[Money]] = mapped_column()
    new_users_only: Mapped[bool] = mapped_column(default=False, server_default=false())
    allowed_user_ids: Mapped[list[int]] = mapped_column(default=list, server_default="{}")
    reusable: Mapped[bool] = mapped_column(default=False, server_default=false())
    active: Mapped[bool] = mapped_column(default=True, server_default=true())

    __table_args__ = (
        CheckConstraint(
            "num_nonnulls(discount_percent, discount_amount, bonus_amount) = 1",
            name="promo_exactly_one_kind",
        ),
        CheckConstraint(
            "usage_limit IS NULL OR times_used <= usage_limit", name="promo_usage_within_limit"
        ),
        CheckConstraint("times_used >= 0", name="promo_times_used_non_negative"),
    )


class PromoCodeUsage(Base):
    __tablename__ = "promo_code_usages"

    id: Mapped[int] = mapped_column(primary_key=True)
    promo_code_id: Mapped[int] = mapped_column(
        ForeignKey("promo_codes.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[Int64] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(server_default=NowFunc)
