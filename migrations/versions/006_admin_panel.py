"""admin panel: withdrawal payout details, broadcast progress

Revision ID: 006
Revises: 005
Create Date: 2026-11-22 18:00:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Optional[str] = "005"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None

OLD_STATUSES = ("draft", "sending", "sent", "failed")
NEW_STATUSES = (*OLD_STATUSES, "stopped")


def _status_check(values: tuple[str, ...]) -> None:
    quoted = ", ".join(f"'{v}'" for v in values)
    op.create_check_constraint(
        "ck_broadcaststatus", "broadcasts", sa.text(f"status IN ({quoted})")
    )


def upgrade() -> None:
    op.add_column("withdrawals", sa.Column("tx_hash", sa.String(), nullable=True))
    op.add_column("withdrawals", sa.Column("reject_reason", sa.String(), nullable=True))
    op.add_column(
        "withdrawals", sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True)
    )
    # rows decided before this revision carry no details: a placeholder keeps the CHECKs true
    op.execute("UPDATE withdrawals SET tx_hash = '-' WHERE status = 'paid'")
    op.execute("UPDATE withdrawals SET reject_reason = '-' WHERE status = 'rejected'")
    op.create_check_constraint(
        "withdrawal_paid_has_tx", "withdrawals", sa.text("status <> 'paid' OR tx_hash IS NOT NULL")
    )
    op.create_check_constraint(
        "withdrawal_rejected_has_reason",
        "withdrawals",
        sa.text("status <> 'rejected' OR reject_reason IS NOT NULL"),
    )

    op.add_column("broadcasts", sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("broadcasts", sa.Column("total_count", sa.Integer(), nullable=True))
    op.add_column(
        "broadcasts",
        sa.Column("cursor_user_id", sa.BigInteger(), server_default="0", nullable=False),
    )
    op.create_check_constraint(
        "broadcast_text_length", "broadcasts", sa.text("char_length(text) BETWEEN 1 AND 4096")
    )
    op.drop_constraint("ck_broadcaststatus", "broadcasts", type_="check")
    _status_check(NEW_STATUSES)


def downgrade() -> None:
    op.drop_constraint("ck_broadcaststatus", "broadcasts", type_="check")
    op.execute("UPDATE broadcasts SET status = 'failed' WHERE status = 'stopped'")
    _status_check(OLD_STATUSES)
    op.drop_constraint("broadcast_text_length", "broadcasts", type_="check")
    op.drop_column("broadcasts", "cursor_user_id")
    op.drop_column("broadcasts", "total_count")
    op.drop_column("broadcasts", "started_at")

    op.drop_constraint("withdrawal_rejected_has_reason", "withdrawals", type_="check")
    op.drop_constraint("withdrawal_paid_has_tx", "withdrawals", type_="check")
    op.drop_column("withdrawals", "processed_at")
    op.drop_column("withdrawals", "reject_reason")
    op.drop_column("withdrawals", "tx_hash")
