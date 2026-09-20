from functools import lru_cache

from sqlalchemy import func, select

from .models import AuditEventRecord
from .repositories import AuditRepository, TeamRepository, UserRepository
from .security import hash_password


DEMO_TEAMS = {
    "leadership": "Direction",
    "rh": "Ressources humaines",
    "finance": "Finance",
    "engineering": "Ingénierie",
    "sales": "Commercial",
}

DEMO_USERS = (
    ("u-admin", "admin@docuscope.local", "Amélie Martin", "Admin123!", "ADMIN", {"leadership"}),
    ("u-lea", "lea@docuscope.local", "Léa Bernard", "Demo123!", "EMPLOYEE", {"rh"}),
    ("u-marc", "marc@docuscope.local", "Marc Dubois", "Demo123!", "EMPLOYEE", {"finance"}),
    ("u-sofia", "sofia@docuscope.local", "Sofia Ricci", "Demo123!", "ADMIN", {"leadership", "engineering"}),
    ("u-karim", "karim@docuscope.local", "Karim Haddad", "Demo123!", "EMPLOYEE", {"engineering"}),
    ("u-nina", "nina@docuscope.local", "Nina Okafor", "Demo123!", "EMPLOYEE", {"engineering", "sales"}),
    ("u-tom", "tom@docuscope.local", "Tom Lefevre", "Demo123!", "EMPLOYEE", {"sales"}),
    ("u-claire", "claire@docuscope.local", "Claire Dupont", "Demo123!", "EMPLOYEE", {"rh", "sales"}),
)


@lru_cache(maxsize=2)
def _demo_password_hash(password: str) -> str:
    return hash_password(password)


def seed_demo_data(session) -> None:
    teams = TeamRepository(session)
    users = UserRepository(session)
    for slug, label in DEMO_TEAMS.items():
        if teams.get(slug) is None:
            teams.create(slug, label)
    for user_id, email, name, password, role, memberships in DEMO_USERS:
        if users.get_by_email(email) is None:
            users.create(email, name, _demo_password_hash(password), role, memberships, user_id=user_id)
    if not session.scalar(select(func.count()).select_from(AuditEventRecord)):
        admin = users.get_by_email("admin@docuscope.local")
        AuditRepository(session).record(admin, "LOGIN", admin.email, "Initialisation de la démonstration")
