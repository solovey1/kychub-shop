"""drop users.timezone: every time is shown in UTC

Revision ID: 013
Revises: 012
Create Date: 2026-11-23 01:00:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "013"
down_revision: Optional[str] = "012"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    op.drop_column("users", "timezone")


def downgrade() -> None:
    op.add_column("users", sa.Column("timezone", sa.String(length=64), nullable=True))
