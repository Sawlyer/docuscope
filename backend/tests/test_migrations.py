import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import inspect

from app.database import engine


REQUIRED_TABLES = {
    "alembic_version",
    "audit_events",
    "conversations",
    "messages",
    "rag_chunks",
    "rag_documents",
    "teams",
    "user_teams",
    "users",
}


def test_alembic_upgrade_is_idempotent_and_builds_complete_schema():
    backend = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["DATABASE_URL"] = engine.url.render_as_string(hide_password=False)

    first = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=backend,
        env=environment,
        capture_output=True,
        text=True,
    )
    second = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=backend,
        env=environment,
        capture_output=True,
        text=True,
    )

    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert REQUIRED_TABLES <= set(inspect(engine).get_table_names())


def test_application_models_define_cascading_conversation_ownership():
    from app.models import ConversationRecord, MessageRecord, UserRecord

    assert next(iter(ConversationRecord.__table__.c.owner_id.foreign_keys)).ondelete == "CASCADE"
    assert next(iter(MessageRecord.__table__.c.conversation_id.foreign_keys)).ondelete == "CASCADE"
    assert UserRecord.__table__.c.email.unique is True
