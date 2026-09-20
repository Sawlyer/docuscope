from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select

from ..models import AuditEventRecord
from ..store import AUDIT_ACTIONS, AuditEvent, User


def _event(record: AuditEventRecord) -> AuditEvent:
    timestamp = record.timestamp if record.timestamp.tzinfo else record.timestamp.replace(tzinfo=timezone.utc)
    return AuditEvent(
        record.id, timestamp.isoformat(), record.actor_email, record.actor_name,
        record.action, record.target, record.detail, dict(record.event_meta or {}),
    )


class AuditRepository:
    def __init__(self, session):
        self.session = session

    def record(self, actor: User, action: str, target: str, detail: str = "", meta: dict | None = None) -> AuditEvent:
        if action not in AUDIT_ACTIONS:
            raise ValueError(f"Unknown audit action: {action}")
        record = AuditEventRecord(
            id=str(uuid4()), timestamp=datetime.now(timezone.utc), actor_email=actor.email,
            actor_name=actor.name, action=action, target=target, detail=detail, event_meta=dict(meta or {}),
        )
        self.session.add(record)
        self.session.flush()
        return _event(record)

    def query(self, actor: str | None = None, action: str | None = None, since: str | None = None, limit: int = 100) -> list[AuditEvent]:
        statement = select(AuditEventRecord).order_by(AuditEventRecord.timestamp.desc()).limit(limit)
        if actor:
            statement = statement.where(AuditEventRecord.actor_email == actor.lower())
        if action:
            statement = statement.where(AuditEventRecord.action == action)
        if since:
            statement = statement.where(AuditEventRecord.timestamp >= datetime.fromisoformat(since))
        return [_event(record) for record in self.session.scalars(statement)]
