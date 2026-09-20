from uuid import uuid4

import pytest

from app.database import session_scope
from app.repositories import AuditRepository, RepositoryConflict, TeamRepository, UserRepository
from app.seed import seed_demo_data


def test_users_teams_and_audit_survive_new_repository_instances():
    suffix = uuid4().hex[:8]
    slug = f"quality-{suffix}"
    email = f"quality-{suffix}@docuscope.local"

    with session_scope() as session:
        teams = TeamRepository(session)
        users = UserRepository(session)
        audit = AuditRepository(session)
        teams.create(slug, f"Qualité {suffix}")
        created = users.create(email, "Zoé Qualité", "hash", "EMPLOYEE", {slug})
        audit.record(created, "USER_CREATED", email, "test")

    with session_scope() as session:
        loaded = UserRepository(session).get_by_email(email)
        events = AuditRepository(session).query(actor=email)
        assert loaded is not None
        assert loaded.teams == {slug}
        assert events[0].target == email

        UserRepository(session).delete(loaded.id)
        TeamRepository(session).delete(slug)


def test_seed_is_idempotent_and_does_not_overwrite_changes():
    with session_scope() as session:
        seed_demo_data(session)
        users = UserRepository(session)
        admin = users.get_by_email("admin@docuscope.local")
        assert admin is not None
        users.update(admin.id, role="EMPLOYEE")

    with session_scope() as session:
        seed_demo_data(session)
        assert UserRepository(session).get_by_email("admin@docuscope.local").role == "EMPLOYEE"
        UserRepository(session).update("u-admin", role="ADMIN")


def test_duplicate_email_and_team_slug_raise_repository_conflict():
    suffix = uuid4().hex[:8]
    slug = f"duplicate-{suffix}"
    email = f"duplicate-{suffix}@docuscope.local"
    with session_scope() as session:
        teams = TeamRepository(session)
        users = UserRepository(session)
        teams.create(slug, "Équipe temporaire")
        users.create(email, "Compte temporaire", "hash", "EMPLOYEE", {slug})
        with pytest.raises(RepositoryConflict):
            teams.create(slug, "Autre nom")
        with pytest.raises(RepositoryConflict):
            users.create(email, "Doublon", "hash", "EMPLOYEE", set())
        users.delete(users.get_by_email(email).id)
        teams.delete(slug)
