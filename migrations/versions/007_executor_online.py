"""executor online status

Revision ID: 007
Revises: 006
Create Date: 2026-11-22 20:00:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "007"
down_revision: Optional[str] = "006"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    op.add_column(
        "executor_profiles",
        sa.Column("is_online", sa.Boolean(), server_default=sa.false(), nullable=False),
    )
    op.add_column(
        "executor_profiles",
        sa.Column("online_changed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("executor_profiles", "online_changed_at")
    op.drop_column("executor_profiles", "is_online")
