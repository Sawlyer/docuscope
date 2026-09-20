from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..models import TeamRecord, UserRecord
from ..store import User
from . import RepositoryConflict


def _identity(record: UserRecord) -> User:
    return User(record.id, record.email, record.name, record.password_hash, record.role, {team.slug for team in record.teams})


class UserRepository:
    def __init__(self, session):
        self.session = session

    def _query(self):
        return select(UserRecord).options(selectinload(UserRecord.teams))

    def list(self) -> list[User]:
        records = self.session.scalars(self._query().order_by(UserRecord.name)).all()
        return [_identity(record) for record in records]

    def get_by_email(self, email: str) -> User | None:
        record = self.session.scalar(self._query().where(UserRecord.email == email.strip().lower()))
        return _identity(record) if record else None

    def get_by_id(self, user_id: str) -> User | None:
        record = self.session.scalar(self._query().where(UserRecord.id == user_id))
        return _identity(record) if record else None

    def create(self, email: str, name: str, password_hash: str, role: str, teams: set[str], user_id: str | None = None) -> User:
        email = email.strip().lower()
        if self.get_by_email(email):
            raise RepositoryConflict("email")
        records = self.session.scalars(select(TeamRecord).where(TeamRecord.slug.in_(teams))).all() if teams else []
        if {record.slug for record in records} != set(teams):
            raise RepositoryConflict("team")
        record = UserRecord(
            id=user_id or f"u-{uuid4().hex[:12]}", email=email, name=name.strip(),
            password_hash=password_hash, role=role, teams=list(records),
        )
        self.session.add(record)
        self.session.flush()
        return _identity(record)

    def update(self, user_id: str, *, role: str | None = None, teams: set[str] | None = None) -> User | None:
        record = self.session.scalar(self._query().where(UserRecord.id == user_id))
        if record is None:
            return None
        if role is not None:
            record.role = role
        if teams is not None:
            records = self.session.scalars(select(TeamRecord).where(TeamRecord.slug.in_(teams))).all() if teams else []
            if {item.slug for item in records} != set(teams):
                raise RepositoryConflict("team")
            record.teams = list(records)
        self.session.flush()
        return _identity(record)

    def delete(self, user_id: str) -> User | None:
        record = self.session.scalar(self._query().where(UserRecord.id == user_id))
        if record is None:
            return None
        user = _identity(record)
        self.session.delete(record)
        self.session.flush()
        return user

    def admin_ids(self) -> set[str]:
        return set(self.session.scalars(select(UserRecord.id).where(UserRecord.role == "ADMIN")))
