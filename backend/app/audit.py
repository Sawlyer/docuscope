from datetime import datetime, timezone
from uuid import uuid4

from .store import AUDIT_ACTIONS, AUDIT_LOG, AuditEvent, User


def record(actor: User, action: str, target: str, detail: str = "", meta: dict | None = None) -> AuditEvent:
    if action not in AUDIT_ACTIONS:
        raise ValueError(f"Unknown audit action: {action}")
    event = AuditEvent(
        id=str(uuid4()),
        timestamp=datetime.now(timezone.utc).isoformat(),
        actor_email=actor.email,
        actor_name=actor.name,
        action=action,
        target=target,
        detail=detail,
        meta=dict(meta or {}),
    )
    AUDIT_LOG.append(event)
    return event


def query(
    actor: str | None = None,
    action: str | None = None,
    since: str | None = None,
    limit: int = 100,
) -> list[AuditEvent]:
    events = list(reversed(AUDIT_LOG))
    if actor:
        events = [event for event in events if event.actor_email == actor.lower()]
    if action:
        events = [event for event in events if event.action == action]
    if since:
        events = [event for event in events if event.timestamp >= since]
    return events[:limit]
