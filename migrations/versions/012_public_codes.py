"""public codes of orders and tickets

Revision ID: 012
Revises: 011
Create Date: 2026-11-23 00:30:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

from app.utils.codes import new_code

# revision identifiers, used by Alembic.
revision: str = "012"
down_revision: Optional[str] = "011"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None

TABLES = ("orders", "tickets")


def upgrade() -> None:
    conn = op.get_bind()
    for table in TABLES:
        op.add_column(table, sa.Column("code", sa.String(length=5), nullable=True))
        ids = conn.execute(sa.text(f"SELECT id FROM {table}")).scalars().all()
        used: set[str] = set()
        for row_id in ids:
            code = new_code()
            while code in used:
                code = new_code()
            used.add(code)
            conn.execute(
                sa.text(f"UPDATE {table} SET code = :code WHERE id = :id"),
                {"code": code, "id": row_id},
            )
        op.alter_column(table, "code", nullable=False)
        op.create_unique_constraint(f"{table}_code_key", table, ["code"])


def downgrade() -> None:
    for table in TABLES:
        op.drop_constraint(f"{table}_code_key", table, type_="unique")
        op.drop_column(table, "code")
