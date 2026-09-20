from sqlalchemy import cast, func, select
from sqlalchemy.dialects.postgresql import JSONB

from ..models import TeamRecord, UserTeamRecord
from ..rag_models import RagDocument
from ..store import Team
from . import RepositoryConflict


class TeamRepository:
    def __init__(self, session):
        self.session = session

    def list(self) -> list[Team]:
        return [Team(item.slug, item.label) for item in self.session.scalars(select(TeamRecord).order_by(TeamRecord.label))]

    def get(self, slug: str) -> Team | None:
        item = self.session.get(TeamRecord, slug)
        return Team(item.slug, item.label) if item else None

    def labels(self) -> dict[str, str]:
        return {team.slug: team.label for team in self.list()}

    def create(self, slug: str, label: str) -> Team:
        slug = slug.strip().lower()
        if self.session.get(TeamRecord, slug):
            raise RepositoryConflict("slug")
        item = TeamRecord(slug=slug, label=label.strip())
        self.session.add(item)
        self.session.flush()
        return Team(item.slug, item.label)

    def delete(self, slug: str) -> tuple[int, int]:
        item = self.session.get(TeamRecord, slug)
        if item is None:
            return 0, 0
        members = self.session.scalar(select(func.count()).select_from(UserTeamRecord).where(UserTeamRecord.team_slug == slug)) or 0
        documents = self.session.scalars(
            select(RagDocument).where(cast(RagDocument.allowed_teams, JSONB).contains([slug]))
        ).all()
        for document in documents:
            document.allowed_teams = [team for team in document.allowed_teams if team != slug]
        self.session.delete(item)
        self.session.flush()
        return int(members), len(documents)
