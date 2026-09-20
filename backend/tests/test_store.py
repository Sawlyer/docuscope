from app import store


def test_demo_accounts_are_unchanged():
    lea = store.USERS["lea@docuscope.local"]
    assert lea.role == "EMPLOYEE"
    assert lea.teams == {"rh"}
    assert store.USERS["admin@docuscope.local"].role == "ADMIN"
    assert store.USERS["marc@docuscope.local"].teams == {"finance"}


def test_seed_is_large_enough_to_exercise_the_ui():
    assert len(store.USERS) >= 8
    assert len(store.DOCUMENTS) >= 6
    assert len(store.TEAMS) >= 5


def test_every_referenced_team_exists():
    referenced = set()
    for user in store.USERS.values():
        referenced |= user.teams
    for document in store.DOCUMENTS.values():
        referenced |= document.allowed_teams
    assert referenced <= set(store.TEAMS)


def test_no_seed_document_readable_by_lea_mentions_the_finance_report():
    lea = store.USERS["lea@docuscope.local"]
    for document in store.DOCUMENTS.values():
        if lea.role in document.allowed_roles or lea.teams & document.allowed_teams:
            assert "Rapport financier T2" not in document.content


def test_new_user_and_delete_user_roundtrip():
    created = store.new_user("zoe@docuscope.local", "Zoe Laurent", "Demo123!", "EMPLOYEE", {"rh"})
    assert store.find_user_by_id(created.id) is created
    assert store.USERS["zoe@docuscope.local"] is created
    removed = store.delete_user(created.id)
    assert removed is created
    assert "zoe@docuscope.local" not in store.USERS
    assert store.delete_user("does-not-exist") is None


def test_audit_log_is_seeded_with_typed_events():
    assert store.AUDIT_LOG
    event = store.AUDIT_LOG[0]
    assert isinstance(event, store.AuditEvent)
    assert event.action in store.AUDIT_ACTIONS
