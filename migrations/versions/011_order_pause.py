"""order pause: the executor needs data from the buyer

Revision ID: 011
Revises: 010
Create Date: 2026-11-22 23:50:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "011"
down_revision: Optional[str] = "010"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("paused_at", sa.DateTime(timezone=True), nullable=True))
    op.create_index(
        "ix_orders_paused",
        "orders",
        ["paused_at"],
        postgresql_where=sa.text("status = 'assigned' AND paused_at IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index("ix_orders_paused", table_name="orders")
    op.drop_column("orders", "paused_at")
