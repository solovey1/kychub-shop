from datetime import datetime
from typing import Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.ledger import LedgerAccount, LedgerKind, PaymentStatus, WithdrawalStatus
from app.utils.custom_types import DictStrAny, Int64, Money

from .base import Base
from .mixins.timestamp import NowFunc, TimestampMixin


class LedgerEntry(Base):
    """Append-only. Balance of an account is the sum of its entries."""

    __tablename__ = "ledger_entries"

    id: Mapped[Int64] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[Int64] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    account: Mapped[LedgerAccount] = mapped_column()
    amount: Mapped[Money] = mapped_column()
    kind: Mapped[LedgerKind] = mapped_column()
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    ref: Mapped[Optional[str]] = mapped_column()
    balance_after: Mapped[Money] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=NowFunc)

    __table_args__ = (
        CheckConstraint("amount <> 0", name="ledger_amount_non_zero"),
        Index("ix_ledger_user_account_id", "user_id", "account", "id"),
        Index(
            "uq_ledger_kind_ref",
            "kind",
            "ref",
            unique=True,
            postgresql_where=text("ref IS NOT NULL"),
        ),
    )


class Payment(Base, TimestampMixin):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Int64] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    provider: Mapped[str] = mapped_column()
    external_id: Mapped[str] = mapped_column()
    amount: Mapped[Money] = mapped_column()
    status: Mapped[PaymentStatus] = mapped_column(default=PaymentStatus.created)
    raw: Mapped[DictStrAny] = mapped_column(default=dict, server_default="{}")

    __table_args__ = (UniqueConstraint("provider", "external_id", name="uq_payment_provider_ext"),)


class Withdrawal(Base, TimestampMixin):
    __tablename__ = "withdrawals"

    id: Mapped[int] = mapped_column(primary_key=True)
    executor_id: Mapped[Int64] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    amount: Mapped[Money] = mapped_column()
    address: Mapped[str] = mapped_column()
    status: Mapped[WithdrawalStatus] = mapped_column(default=WithdrawalStatus.pending)
    processed_by: Mapped[Optional[Int64]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )

    __table_args__ = (CheckConstraint("amount > 0", name="withdrawal_amount_positive"),)
