from datetime import datetime

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    email: str
    password: str


class UserOut(BaseModel):
    id: str
    email: str
    name: str
    role: str
    teams: list[str] = []


class LoginResponse(BaseModel):
    user: UserOut


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=200)
    name: str = Field(min_length=2, max_length=120)
    password: str = Field(min_length=8, max_length=200)
    role: str = "EMPLOYEE"
    teams: list[str] = []

    @field_validator("email")
    @classmethod
    def looks_like_an_address(cls, value: str) -> str:
        """Deliberately loose: the demo workspace uses the .local domain, which
        strict validators reject as special-use."""
        local, _, domain = value.strip().partition("@")
        if not local or "." not in domain or domain.startswith(".") or domain.endswith("."):
            raise ValueError("Adresse e-mail invalide")
        return value.strip()


class UserUpdate(BaseModel):
    role: str | None = None
    teams: list[str] | None = None


class MemberRef(BaseModel):
    id: str
    name: str
    email: str


class DocumentRef(BaseModel):
    id: str
    title: str


class TeamCreate(BaseModel):
    slug: str = Field(min_length=2, max_length=40)
    label: str = Field(min_length=2, max_length=80)


class TeamOut(BaseModel):
    slug: str
    label: str
    members: list[MemberRef] = []
    documents: list[DocumentRef] = []
    member_count: int = 0


class DocumentOut(BaseModel):
    id: str
    title: str
    department: str
    status: str
    allowed_roles: list[str] = []
    allowed_teams: list[str] = []
    page_count: int = 0
    chunk_count: int = 0
    ingestion_error: str | None = None


class DocumentContentOut(BaseModel):
    id: str
    title: str
    department: str
    content: str


class DocumentAccessUpdate(BaseModel):
    allowed_roles: list[str] = []
    allowed_teams: list[str] = []


class MatrixRow(BaseModel):
    kind: str
    key: str
    label: str
    access: dict[str, bool]


class AccessMatrix(BaseModel):
    documents: list[DocumentOut]
    rows: list[MatrixRow]


class AccessEntry(BaseModel):
    document_id: str
    title: str
    department: str
    allowed: bool
    reason: str | None = None


class AccessPreview(BaseModel):
    user: UserOut
    entries: list[AccessEntry]
    allowed_count: int
    total_count: int


class AuditEventOut(BaseModel):
    id: str
    timestamp: str
    actor_email: str
    actor_name: str
    action: str
    target: str
    detail: str = ""


class DailyCount(BaseModel):
    date: str
    count: int


class LabelCount(BaseModel):
    key: str
    label: str
    count: int


class AnalyticsAlerts(BaseModel):
    unreachable_documents: list[DocumentRef] = []
    members_without_team: list[MemberRef] = []
    empty_teams: list[LabelCount] = []


class Analytics(BaseModel):
    days: int
    total_questions: int
    questions_in_period: int
    active_members: int
    questions_per_day: list[DailyCount]
    top_documents: list[LabelCount]
    activity_by_team: list[LabelCount]
    top_members: list[LabelCount]
    alerts: AnalyticsAlerts


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)


class Source(BaseModel):
    document_id: str
    title: str
    page: int | None = None
    excerpt: str
    similarity: float | None = None
    file_url: str | None = None


class ChatResponse(BaseModel):
    answer: str
    sources: list[Source]


class ConversationCreate(BaseModel):
    title: str = Field(default="Nouvelle conversation", max_length=160)


class ConversationMessageOut(BaseModel):
    id: str
    role: str
    content: str
    sources: list[Source]
    status: str
    created_at: datetime


class ConversationSummary(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ConversationOut(ConversationSummary):
    messages: list[ConversationMessageOut]
