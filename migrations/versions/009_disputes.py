"""disputes: «call support» on an order, with a reply deadline

Revision ID: 009
Revises: 008
Create Date: 2026-11-22 23:00:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "009"
down_revision: Optional[str] = "008"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None

RESOLUTIONS = ("completed", "refunded", "sent_back", "closed")


def upgrade() -> None:
    quoted = ", ".join(f"'{v}'" for v in RESOLUTIONS)
    op.create_table(
        "disputes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("order_id", sa.Integer(), nullable=False),
        sa.Column("opened_by", sa.BigInteger(), nullable=False),
        sa.Column("opened_role", sa.String(length=16), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "opened_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("timezone('UTC', now())"),
            nullable=False,
        ),
        sa.Column("awaiting_role", sa.String(length=16), nullable=True),
        sa.Column("awaiting_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution", sa.String(length=32), nullable=True),
        sa.Column("resolved_by", sa.BigInteger(), nullable=True),
        sa.CheckConstraint("opened_role IN ('buyer', 'executor')", name="dispute_opened_role"),
        sa.CheckConstraint(
            "awaiting_role IS NULL OR awaiting_role IN ('buyer', 'executor')",
            name="dispute_awaiting_role",
        ),
        sa.CheckConstraint(
            "(resolved_at IS NULL) = (resolution IS NULL)", name="dispute_resolved_together"
        ),
        sa.CheckConstraint(f"resolution IN ({quoted})", name="ck_disputeresolution"),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["opened_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["resolved_by"], ["users.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "uq_disputes_open",
        "disputes",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("resolved_at IS NULL"),
    )
    op.create_index(
        "ix_disputes_awaiting_until",
        "disputes",
        ["awaiting_until"],
        postgresql_where=sa.text("resolved_at IS NULL AND awaiting_until IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_disputes_awaiting_until", table_name="disputes")
    op.drop_index("uq_disputes_open", table_name="disputes")
    op.drop_table("disputes")
