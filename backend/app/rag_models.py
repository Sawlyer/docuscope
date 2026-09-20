from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class RagDocument(Base):
    __tablename__ = "rag_documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(300))
    department: Mapped[str] = mapped_column(String(120), default="Général")
    mime_type: Mapped[str] = mapped_column(String(100))
    object_key: Mapped[str | None] = mapped_column(String(500), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="PENDING")
    page_count: Mapped[int] = mapped_column(Integer, default=0)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    allowed_roles: Mapped[list[str]] = mapped_column(JSON, default=list)
    allowed_teams: Mapped[list[str]] = mapped_column(JSON, default=list)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    chunks: Mapped[list["RagChunk"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class RagChunk(Base):
    __tablename__ = "rag_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("rag_documents.id", ondelete="CASCADE"), index=True)
    page: Mapped[int] = mapped_column(Integer)
    chunk_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(Text)
    embedding: Mapped[list[float]] = mapped_column(Vector(384))
    document: Mapped[RagDocument] = relationship(back_populates="chunks")
