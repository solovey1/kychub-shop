from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.support import ChatRole, ConversationKind, TicketStatus
from app.utils.custom_types import DictStrAny, Int64

from .base import Base
from .mixins.timestamp import NowFunc


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[Int64] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), index=True)
    order_id: Mapped[Optional[int]] = mapped_column(ForeignKey("orders.id", ondelete="SET NULL"))
    manager_id: Mapped[Optional[Int64]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL")
    )
    status: Mapped[TicketStatus] = mapped_column(default=TicketStatus.open)
    created_at: Mapped[datetime] = mapped_column(server_default=NowFunc)
    taken_at: Mapped[Optional[datetime]] = mapped_column()
    closed_at: Mapped[Optional[datetime]] = mapped_column()

    __table_args__ = (
        Index("ix_tickets_status", "status"),
        # one live ticket per (user, order); order_id NULL = the general ticket (PG15+)
        Index(
            "uq_tickets_open",
            "user_id",
            "order_id",
            unique=True,
            postgresql_where=text("status IN ('open', 'taken')"),
            postgresql_nulls_not_distinct=True,
        ),
    )


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[ConversationKind] = mapped_column()
    ticket_id: Mapped[Optional[int]] = mapped_column(ForeignKey("tickets.id", ondelete="CASCADE"))
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    thread_id: Mapped[Optional[int]] = mapped_column(index=True)

    __table_args__ = (
        CheckConstraint(
            "(kind = 'order' AND order_id IS NOT NULL AND ticket_id IS NULL)"
            " OR (kind = 'ticket' AND ticket_id IS NOT NULL AND order_id IS NULL)",
            name="conversation_kind_target",
        ),
        Index(
            "uq_conversations_order",
            "order_id",
            unique=True,
            postgresql_where=text("kind = 'order'"),
        ),
        Index("uq_conversations_ticket", "ticket_id", unique=True),
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE")
    )
    sender_id: Mapped[Int64] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    sender_role: Mapped[ChatRole] = mapped_column()
    text: Mapped[Optional[str]] = mapped_column()
    media: Mapped[Optional[DictStrAny]] = mapped_column()
    tg_message_id: Mapped[Optional[Int64]] = mapped_column()
    tg_chat_id: Mapped[Optional[Int64]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=NowFunc)

    # reply routing: (chat, message) -> conversation
    __table_args__ = (
        Index("ix_messages_tg_chat_message", "tg_chat_id", "tg_message_id"),
        # history pages and unread counts both walk one conversation by id
        Index("ix_messages_conversation_id_id", "conversation_id", "id"),
    )


class ConversationRead(Base):
    """How far a user has read a conversation; no row means nothing yet."""

    __tablename__ = "conversation_reads"

    conversation_id: Mapped[int] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[Int64] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    last_read_message_id: Mapped[int] = mapped_column(BigInteger, server_default=text("0"))
    updated_at: Mapped[datetime] = mapped_column(server_default=NowFunc)
