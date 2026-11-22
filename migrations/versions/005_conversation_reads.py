"""conversation reads: how far each user has read each conversation

Revision ID: 005
Revises: 004
Create Date: 2026-11-22 12:00:00.000000

"""

from typing import Optional, Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Optional[str] = "004"
branch_labels: Optional[Sequence[str]] = None
depends_on: Optional[Sequence[str]] = None


def upgrade() -> None:
    op.create_table(
        "conversation_reads",
        sa.Column("conversation_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("last_read_message_id", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("conversation_id", "user_id"),
    )
    # (conversation_id, id) covers everything the single-column index did
    op.create_index("ix_messages_conversation_id_id", "messages", ["conversation_id", "id"])
    op.drop_index(op.f("ix_messages_conversation_id"), table_name="messages")


def downgrade() -> None:
    op.create_index(
        op.f("ix_messages_conversation_id"), "messages", ["conversation_id"], unique=False
    )
    op.drop_index("ix_messages_conversation_id_id", table_name="messages")
    op.drop_table("conversation_reads")
