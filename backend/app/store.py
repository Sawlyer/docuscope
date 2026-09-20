from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from .security import hash_password

AUDIT_ACTIONS = (
    "LOGIN",
    "QUESTION_ASKED",
    "USER_CREATED",
    "USER_UPDATED",
    "USER_DELETED",
    "DOCUMENT_UPLOADED",
    "DOCUMENT_ACCESS_CHANGED",
    "DOCUMENT_DELETED",
    "TEAM_CREATED",
    "TEAM_DELETED",
)

ROLES = ("ADMIN", "EMPLOYEE")


@dataclass
class Team:
    slug: str
    label: str


@dataclass
class Document:
    id: str
    title: str
    department: str
    content: str
    allowed_roles: set[str] = field(default_factory=set)
    allowed_teams: set[str] = field(default_factory=set)
    status: str = "indexed"
    chunks: list[str] = field(default_factory=list)


@dataclass
class User:
    id: str
    email: str
    name: str
    password_hash: str
    role: str
    teams: set[str] = field(default_factory=set)


@dataclass
class AuditEvent:
    id: str
    timestamp: str
    actor_email: str
    actor_name: str
    action: str
    target: str
    detail: str = ""
    # Structured payload for analytics. The human-readable `detail` is for
    # display only; counting citations by splitting that string would break the
    # day a title contains a comma.
    meta: dict = field(default_factory=dict)


TEAMS: dict[str, Team] = {
    "leadership": Team("leadership", "Direction"),
    "rh": Team("rh", "Ressources humaines"),
    "finance": Team("finance", "Finance"),
    "engineering": Team("engineering", "Ingénierie"),
    "sales": Team("sales", "Commercial"),
}


def _user(user_id, email, name, password, role, teams):
    return User(user_id, email, name, hash_password(password), role, set(teams))


USERS: dict[str, User] = {
    user.email: user
    for user in [
        _user("u-admin", "admin@docuscope.local", "Amélie Martin", "Admin123!", "ADMIN", {"leadership"}),
        _user("u-lea", "lea@docuscope.local", "Léa Bernard", "Demo123!", "EMPLOYEE", {"rh"}),
        _user("u-marc", "marc@docuscope.local", "Marc Dubois", "Demo123!", "EMPLOYEE", {"finance"}),
        _user("u-sofia", "sofia@docuscope.local", "Sofia Ricci", "Demo123!", "ADMIN", {"leadership", "engineering"}),
        _user("u-karim", "karim@docuscope.local", "Karim Haddad", "Demo123!", "EMPLOYEE", {"engineering"}),
        _user("u-nina", "nina@docuscope.local", "Nina Okafor", "Demo123!", "EMPLOYEE", {"engineering", "sales"}),
        _user("u-tom", "tom@docuscope.local", "Tom Lefevre", "Demo123!", "EMPLOYEE", {"sales"}),
        _user("u-claire", "claire@docuscope.local", "Claire Dupont", "Demo123!", "EMPLOYEE", {"rh", "sales"}),
    ]
}


def _document(doc_id, title, department, content, roles, teams):
    document = Document(doc_id, title, department, content, set(roles), set(teams))
    document.chunks = [content]
    return document


DOCUMENTS: dict[str, Document] = {
    document.id: document
    for document in [
        _document(
            "doc-handbook",
            "Manuel de l'employé",
            "Général",
            "Chaque salarié doit suivre la formation sécurité dans les trente jours suivant son arrivée. L'accès à distance exige une authentification à deux facteurs.",
            {"ADMIN", "EMPLOYEE"},
            set(),
        ),
        _document(
            "doc-rh",
            "Politique RH 2026",
            "Ressources humaines",
            "Le cycle d'entretiens annuels démarre en septembre. Les ressources humaines pilotent la liste d'intégration et la politique de qualité de vie au travail.",
            {"ADMIN"},
            {"rh"},
        ),
        _document(
            "doc-finance",
            "Rapport financier T2",
            "Finance",
            "Le chiffre d'affaires progresse de 18 pour cent au deuxième trimestre. L'équipe finance table prudemment sur 7 pour cent de croissance au trimestre suivant.",
            {"ADMIN"},
            {"finance"},
        ),
        _document(
            "doc-security",
            "Socle de sécurité",
            "Ingénierie",
            "L'accès à la production est accordé service par service et réexaminé chaque trimestre. Les secrets sont renouvelés automatiquement tous les quatre-vingt-dix jours.",
            {"ADMIN", "EMPLOYEE"},
            set(),
        ),
        _document(
            "doc-architecture",
            "Notes d'architecture",
            "Ingénierie",
            "Le service de recherche filtre les documents par rôle et par équipe avant toute recherche de similarité. Les vecteurs sont stockés dans pgvector.",
            {"ADMIN"},
            {"engineering"},
        ),
        _document(
            "doc-pipeline",
            "Revue du pipeline commercial",
            "Commercial",
            "Les contrats grands comptes se concluent désormais en quarante et un jours en moyenne. L'équipe commerciale suit le risque de non-renouvellement chaque semaine.",
            {"ADMIN"},
            {"sales"},
        ),
    ]
}


def _seeded_event(minutes_ago, actor_email, action, target, detail, meta=None):
    actor = USERS[actor_email]
    stamp = datetime.now(timezone.utc) - timedelta(minutes=minutes_ago)
    return AuditEvent(
        str(uuid4()),
        stamp.isoformat(),
        actor.email,
        actor.name,
        action,
        target,
        detail,
        dict(meta or {}),
    )


def _question(minutes_ago, actor_email, question, document_ids):
    titles = ", ".join(DOCUMENTS[doc_id].title for doc_id in document_ids)
    return _seeded_event(
        minutes_ago,
        actor_email,
        "QUESTION_ASKED",
        question,
        f"Sources : {titles}",
        {"document_ids": list(document_ids)},
    )


DAY = 1440

# Two weeks of history so the analytics screen has a curve to draw rather than a
# single bar on today.
AUDIT_LOG: list[AuditEvent] = [
    _seeded_event(13 * DAY, "admin@docuscope.local", "DOCUMENT_UPLOADED", "Socle de sécurité", "1 fragment indexé"),
    _question(13 * DAY, "karim@docuscope.local", "Comment sont gérés les secrets en production ?", ["doc-security"]),
    _question(12 * DAY, "lea@docuscope.local", "Quelle est la liste d'intégration ?", ["doc-rh", "doc-handbook"]),
    _question(12 * DAY, "claire@docuscope.local", "Quand commencent les entretiens annuels ?", ["doc-rh"]),
    _question(11 * DAY, "marc@docuscope.local", "Quelle croissance est prévue au prochain trimestre ?", ["doc-finance"]),
    _seeded_event(10 * DAY, "sofia@docuscope.local", "USER_CREATED", "tom@docuscope.local", "Rôle EMPLOYEE, équipes commercial"),
    _question(10 * DAY, "tom@docuscope.local", "Quel est le délai moyen de signature ?", ["doc-pipeline"]),
    _question(9 * DAY, "nina@docuscope.local", "Comment fonctionne le filtrage par équipe ?", ["doc-handbook"]),
    _question(8 * DAY, "lea@docuscope.local", "Quelles sont les règles d'accès à distance ?", ["doc-handbook", "doc-rh"]),
    _question(6 * DAY, "karim@docuscope.local", "Où sont stockés les vecteurs ?", ["doc-architecture", "doc-security"]),
    _question(5 * DAY, "claire@docuscope.local", "Que couvre la politique de qualité de vie au travail ?", ["doc-rh"]),
    _seeded_event(4 * DAY, "admin@docuscope.local", "DOCUMENT_ACCESS_CHANGED", "Rapport financier T2", "Équipes : finance"),
    _question(4 * DAY, "marc@docuscope.local", "Comment a évolué le chiffre d'affaires ?", ["doc-finance", "doc-handbook"]),
    _question(3 * DAY, "nina@docuscope.local", "Quel est le risque de non-renouvellement ?", ["doc-pipeline"]),
    _question(2 * DAY, "lea@docuscope.local", "Qu'est-ce qui a changé dans la politique RH ?", ["doc-rh"]),
    _question(DAY, "tom@docuscope.local", "Quels comptes sont à relancer ?", ["doc-pipeline", "doc-handbook"]),
    _question(240, "karim@docuscope.local", "Quand la revue d'accès a-t-elle lieu ?", ["doc-security"]),
    _seeded_event(20, "admin@docuscope.local", "LOGIN", "admin@docuscope.local", "Rôle ADMIN"),
]


def find_user_by_id(user_id: str) -> User | None:
    return next((user for user in USERS.values() if user.id == user_id), None)


def new_user(email: str, name: str, password: str, role: str, teams: set[str]) -> User:
    user = User(f"u-{uuid4().hex[:8]}", email.lower(), name, hash_password(password), role, set(teams))
    USERS[user.email] = user
    return user


def delete_user(user_id: str) -> User | None:
    user = find_user_by_id(user_id)
    if user is None:
        return None
    return USERS.pop(user.email, None)


def new_document(title: str, department: str, content: str) -> Document:
    document = _document(str(uuid4()), title, department, content, {"ADMIN"}, set())
    DOCUMENTS[document.id] = document
    return document


def delete_team(slug: str) -> tuple[int, int]:
    """Remove a team and every grant that referenced it. Returns what it touched."""
    members = [user for user in USERS.values() if slug in user.teams]
    documents = [doc for doc in DOCUMENTS.values() if slug in doc.allowed_teams]
    for user in members:
        user.teams.discard(slug)
    for doc in documents:
        doc.allowed_teams.discard(slug)
    TEAMS.pop(slug, None)
    return len(members), len(documents)
