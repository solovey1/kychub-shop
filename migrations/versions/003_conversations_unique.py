"""one conversation per order and per ticket

Revision ID: 003
Revises: 002
Create Date: 2026-11-21 18:00:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Optional[str] = "002"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    op.create_index(
        "uq_conversations_order",
        "conversations",
        ["order_id"],
        unique=True,
        postgresql_where=sa.text("kind = 'order'"),
    )
    op.create_index("uq_conversations_ticket", "conversations", ["ticket_id"], unique=True)


def downgrade() -> None:
    op.drop_index("uq_conversations_ticket", table_name="conversations")
    op.drop_index("uq_conversations_order", table_name="conversations")
