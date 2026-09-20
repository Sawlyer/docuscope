from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UserTeamRecord(Base):
    __tablename__ = "user_teams"

    user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    team_slug: Mapped[str] = mapped_column(ForeignKey("teams.slug", ondelete="CASCADE"), primary_key=True)


class UserRecord(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    email: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    password_hash: Mapped[str] = mapped_column(String(500))
    role: Mapped[str] = mapped_column(String(30), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    teams: Mapped[list["TeamRecord"]] = relationship(secondary="user_teams", back_populates="members")
    conversations: Mapped[list["ConversationRecord"]] = relationship(back_populates="owner", cascade="all, delete-orphan")


class TeamRecord(Base):
    __tablename__ = "teams"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    label: Mapped[str] = mapped_column(String(80), unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    members: Mapped[list[UserRecord]] = relationship(secondary="user_teams", back_populates="teams")


class AuditEventRecord(Base):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    actor_email: Mapped[str] = mapped_column(String(200), index=True)
    actor_name: Mapped[str] = mapped_column(String(120))
    action: Mapped[str] = mapped_column(String(80), index=True)
    target: Mapped[str] = mapped_column(String(500))
    detail: Mapped[str] = mapped_column(Text, default="")
    event_meta: Mapped[dict] = mapped_column("meta", JSON, default=dict)


class ConversationRecord(Base):
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(160), default="Nouvelle conversation")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, index=True)
    owner: Mapped[UserRecord] = relationship(back_populates="conversations")
    messages: Mapped[list["MessageRecord"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="MessageRecord.position"
    )


class MessageRecord(Base):
    __tablename__ = "messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "position", name="uq_messages_conversation_position"),
        Index("ix_messages_conversation_created", "conversation_id", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    sources: Mapped[list[dict]] = mapped_column(JSON, default=list)
    status: Mapped[str] = mapped_column(String(20), default="COMPLETE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    conversation: Mapped[ConversationRecord] = relationship(back_populates="messages")
