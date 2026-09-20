"""Create durable DocuScope application state without replacing existing RAG data."""

from alembic import op
from pgvector.sqlalchemy import Vector
import sqlalchemy as sa


revision = "20260920_0001"
down_revision = None
branch_labels = None
depends_on = None


def _has_table(name: str) -> bool:
    return sa.inspect(op.get_bind()).has_table(name)


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    if not _has_table("rag_documents"):
        op.create_table(
            "rag_documents",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("title", sa.String(300), nullable=False),
            sa.Column("department", sa.String(120), nullable=False, server_default="Général"),
            sa.Column("mime_type", sa.String(100), nullable=False),
            sa.Column("object_key", sa.String(500)),
            sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
            sa.Column("page_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("allowed_roles", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("allowed_teams", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("error", sa.Text()),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _has_table("rag_chunks"):
        op.create_table(
            "rag_chunks",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("document_id", sa.String(64), sa.ForeignKey("rag_documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("page", sa.Integer(), nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("text", sa.Text(), nullable=False),
            sa.Column("embedding", Vector(384), nullable=False),
        )
        op.create_index("ix_rag_chunks_document_id", "rag_chunks", ["document_id"])
    op.execute("CREATE INDEX IF NOT EXISTS rag_chunks_embedding_hnsw ON rag_chunks USING hnsw (embedding vector_cosine_ops)")

    if not _has_table("users"):
        op.create_table(
            "users",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("email", sa.String(200), nullable=False, unique=True),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("password_hash", sa.String(500), nullable=False),
            sa.Column("role", sa.String(30), nullable=False),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_users_email", "users", ["email"], unique=True)
        op.create_index("ix_users_role", "users", ["role"])
    if not _has_table("teams"):
        op.create_table(
            "teams",
            sa.Column("slug", sa.String(40), primary_key=True),
            sa.Column("label", sa.String(80), nullable=False, unique=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
    if not _has_table("user_teams"):
        op.create_table(
            "user_teams",
            sa.Column("user_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
            sa.Column("team_slug", sa.String(40), sa.ForeignKey("teams.slug", ondelete="CASCADE"), primary_key=True),
        )
    if not _has_table("audit_events"):
        op.create_table(
            "audit_events",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("actor_email", sa.String(200), nullable=False),
            sa.Column("actor_name", sa.String(120), nullable=False),
            sa.Column("action", sa.String(80), nullable=False),
            sa.Column("target", sa.String(500), nullable=False),
            sa.Column("detail", sa.Text(), nullable=False, server_default=""),
            sa.Column("meta", sa.JSON(), nullable=False, server_default="{}"),
        )
        op.create_index("ix_audit_events_timestamp", "audit_events", ["timestamp"])
        op.create_index("ix_audit_events_actor_email", "audit_events", ["actor_email"])
        op.create_index("ix_audit_events_action", "audit_events", ["action"])
    if not _has_table("conversations"):
        op.create_table(
            "conversations",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("owner_id", sa.String(64), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("title", sa.String(160), nullable=False, server_default="Nouvelle conversation"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )
        op.create_index("ix_conversations_owner_id", "conversations", ["owner_id"])
        op.create_index("ix_conversations_updated_at", "conversations", ["updated_at"])
    if not _has_table("messages"):
        op.create_table(
            "messages",
            sa.Column("id", sa.String(64), primary_key=True),
            sa.Column("conversation_id", sa.String(64), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
            sa.Column("position", sa.Integer(), nullable=False),
            sa.Column("role", sa.String(20), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("sources", sa.JSON(), nullable=False, server_default="[]"),
            sa.Column("status", sa.String(20), nullable=False, server_default="COMPLETE"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.UniqueConstraint("conversation_id", "position", name="uq_messages_conversation_position"),
        )
        op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
        op.create_index("ix_messages_conversation_created", "messages", ["conversation_id", "created_at"])


def downgrade() -> None:
    for table in ("messages", "conversations", "audit_events", "user_teams", "teams", "users"):
        if _has_table(table):
            op.drop_table(table)
