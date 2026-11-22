"""user time zone, acceptance of auto-assigned orders

Revision ID: 010
Revises: 009
Create Date: 2026-11-22 23:30:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "010"
down_revision: Optional[str] = "009"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("timezone", sa.String(length=64), nullable=True))
    op.add_column("orders", sa.Column("accept_until", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_orders_accept_due",
        "orders",
        ["accept_until"],
        postgresql_where=sa.text("status = 'assigned' AND accept_until IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_orders_accept_due", table_name="orders")
    op.drop_column("orders", "accept_until")
    op.drop_column("users", "timezone")
