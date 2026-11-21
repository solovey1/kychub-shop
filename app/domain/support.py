from datetime import datetime
from typing import Optional

from sqlalchemy import ForeignKey, Index, text
from sqlalchemy.orm import Mapped, mapped_column

from app.domain.enums.support import ConversationKind, TicketStatus
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

    __table_args__ = (Index("ix_tickets_status", "status"),)


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[ConversationKind] = mapped_column()
    ticket_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("tickets.id", ondelete="CASCADE"), index=True
    )
    order_id: Mapped[Optional[int]] = mapped_column(
        ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    thread_id: Mapped[Optional[int]] = mapped_column(index=True)

    __table_args__ = (
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
        ForeignKey("conversations.id", ondelete="CASCADE"), index=True
    )
    sender_id: Mapped[Int64] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"))
    sender_role: Mapped[str] = mapped_column()
    text: Mapped[Optional[str]] = mapped_column()
    media: Mapped[Optional[DictStrAny]] = mapped_column()
    tg_message_id: Mapped[Optional[Int64]] = mapped_column()
    tg_chat_id: Mapped[Optional[Int64]] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(server_default=NowFunc)

    # reply routing: (chat, message) -> conversation
    __table_args__ = (Index("ix_messages_tg_chat_message", "tg_chat_id", "tg_message_id"),)
