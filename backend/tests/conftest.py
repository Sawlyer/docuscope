import copy
import os

import psycopg
import pytest
from sqlalchemy import text


TEST_DATABASE_URL = "postgresql+psycopg://docuscope:docuscope@postgres:5432/docuscope_test"
CONFIGURED_DATABASE_URL = os.environ.get("DATABASE_URL", TEST_DATABASE_URL)


def _ensure_test_database() -> None:
    admin_url = CONFIGURED_DATABASE_URL.replace("postgresql+psycopg://", "postgresql://").replace("/docuscope_test", "/postgres")
    with psycopg.connect(admin_url, autocommit=True) as connection:
        exists = connection.execute("SELECT 1 FROM pg_database WHERE datname = 'docuscope_test'").fetchone()
        if not exists:
            connection.execute("CREATE DATABASE docuscope_test")


_ensure_test_database()
os.environ["DATABASE_URL"] = CONFIGURED_DATABASE_URL

from alembic import command
from alembic.config import Config

from app import store
from app.config import settings
from app.database import session_scope
from app.seed import seed_demo_data


command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def restore_state(monkeypatch):
    monkeypatch.setattr(settings, "mock_llm", True)
    documents = copy.deepcopy(store.DOCUMENTS)
    with session_scope() as session:
        session.execute(text("TRUNCATE messages, conversations, audit_events, user_teams, users, teams RESTART IDENTITY CASCADE"))
        seed_demo_data(session)
    yield
    store.DOCUMENTS.clear()
    store.DOCUMENTS.update(documents)
    with session_scope() as session:
        session.execute(text("TRUNCATE messages, conversations, audit_events, user_teams, users, teams RESTART IDENTITY CASCADE"))
        seed_demo_data(session)
