"""user time zone

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


def downgrade() -> None:
    op.drop_column("users", "timezone")
