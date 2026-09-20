from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from .config import settings
from .database import session_scope
from .dependencies import current_user, admin_user
from .chat_service import answer_question, source_document_titles
from .retrieval import accessible_documents
from .extractors import DocumentExtractionError
from .ingestion import ingestion_service
from .rag_repository import RagRepository
from .repositories import AuditRepository, ConversationRepository, RepositoryConflict, TeamRepository, UserRepository
from .seed import seed_demo_data
from .storage import object_storage
from .schemas import (
    AccessEntry,
    AccessMatrix,
    AccessPreview,
    Analytics,
    AnalyticsAlerts,
    AuditEventOut,
    ChatRequest,
    ChatResponse,
    ConversationCreate,
    ConversationMessageOut,
    ConversationOut,
    ConversationSummary,
    DailyCount,
    DocumentAccessUpdate,
    DocumentOut,
    DocumentContentOut,
    DocumentRef,
    LabelCount,
    LoginRequest,
    LoginResponse,
    MatrixRow,
    MemberRef,
    TeamCreate,
    TeamOut,
    UserCreate,
    UserOut,
    UserUpdate,
)
from .request_security import validate_request_origin
from .security import clear_session_cookie, create_token, hash_password, set_session_cookie, verify_password
from .store import (
    DOCUMENTS,
    ROLES,
    Document,
    Team,
    User,
    new_document,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    with session_scope() as session:
        seed_demo_data(session)
    if not settings.mock_llm:
        from .rag_runtime import initialize_rag
        initialize_rag()
    yield


app = FastAPI(title=settings.app_name, version="0.4.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[item.strip() for item in settings.allowed_origins.split(",") if item.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ANALYTICS_DAYS = 14

ROLE_LABELS = {"ADMIN": "Administrateur", "EMPLOYEE": "Employé"}

FIELD_LABELS = {
    "email": "Adresse e-mail",
    "name": "Nom",
    "password": "Mot de passe",
    "role": "Rôle",
    "teams": "Équipes",
    "slug": "Identifiant",
    "label": "Nom",
    "question": "Question",
}


@app.middleware("http")
async def enforce_same_origin(request: Request, call_next):
    try:
        validate_request_origin(request)
    except HTTPException as exc:
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_error(_: Request, exc: RequestValidationError):
    """Pydantic reports in English; the client shows `detail` verbatim."""
    messages = []
    for error in exc.errors():
        field = str(error["loc"][-1])
        label = FIELD_LABELS.get(field, field)
        kind = error["type"]
        if kind == "missing":
            messages.append(f"{label} : champ obligatoire")
        elif kind.endswith("too_short"):
            messages.append(f"{label} : trop court")
        elif kind.endswith("too_long"):
            messages.append(f"{label} : trop long")
        elif kind == "value_error":
            messages.append(f"{label} : {error.get('msg', 'valeur invalide').replace('Value error, ', '')}")
        else:
            messages.append(f"{label} : valeur invalide")
    return JSONResponse(status_code=422, content={"detail": " ; ".join(messages)})


def user_out(user: User) -> UserOut:
    return UserOut(id=user.id, email=user.email, name=user.name, role=user.role, teams=sorted(user.teams))


def document_out(doc: Document) -> DocumentOut:
    return DocumentOut(
        id=doc.id,
        title=doc.title,
        department=doc.department,
        status=doc.status,
        allowed_roles=sorted(doc.allowed_roles),
        allowed_teams=sorted(doc.allowed_teams),
        page_count=getattr(doc, "page_count", 0),
        chunk_count=len(doc.chunks),
        ingestion_error=getattr(doc, "ingestion_error", None),
    )


def require_user(repository: UserRepository, user_id: str) -> User:
    user = repository.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="Membre introuvable")
    return user


def require_document(document_id: str) -> Document:
    doc = DOCUMENTS.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document introuvable")
    return doc


def require_team(repository: TeamRepository, slug: str) -> Team:
    team = repository.get(slug)
    if team is None:
        raise HTTPException(status_code=404, detail="Équipe introuvable")
    return team


def validate_teams(repository: TeamRepository, teams) -> set[str]:
    unknown = sorted(set(teams) - set(repository.labels()))
    if unknown:
        raise HTTPException(status_code=422, detail=f"Équipe(s) inconnue(s) : {', '.join(unknown)}")
    return set(teams)


def validate_role(role: str) -> str:
    if role not in ROLES:
        raise HTTPException(status_code=422, detail=f"Le rôle doit être {' ou '.join(ROLES)}")
    return role


def team_label(labels: dict[str, str], slug: str) -> str:
    return labels.get(slug, slug)


@app.get("/health")
def health():
    return {"status": "ok", "service": "docuscope-api", "llm": settings.lm_studio_url, "model": settings.lm_studio_model}


@app.post("/api/auth/login", response_model=LoginResponse)
def login(payload: LoginRequest, response: Response):
    with session_scope() as session:
        user = UserRepository(session).get_by_email(payload.email)
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Adresse e-mail ou mot de passe incorrect")
        AuditRepository(session).record(user, "LOGIN", user.email, f"Rôle {user.role}")
    set_session_cookie(response, create_token(user.email, user.role))
    return LoginResponse(user=user_out(user))


@app.post("/api/auth/logout", status_code=204)
def logout(response: Response):
    clear_session_cookie(response)
    return None


@app.get("/api/auth/me", response_model=UserOut)
def me(user: User = Depends(current_user)):
    return user_out(user)


@app.get("/api/dashboard")
def dashboard(user: User = Depends(current_user)):
    accessible = accessible_documents(user)
    with session_scope() as session:
        users_count = len(UserRepository(session).list())
        audit = AuditRepository(session)
        questions = len(audit.query(action="QUESTION_ASKED", limit=100000))
        activity = audit.query(limit=5) if user.role == "ADMIN" else audit.query(actor=user.email, limit=5)
    return {
        "documents": len(accessible),
        "users": users_count,
        "indexed": len(DOCUMENTS),
        "questions": questions,
        # Non-admins see only their own trail: the full feed names other members
        # and the permission changes made to them.
        "activity": activity,
    }


@app.get("/api/documents", response_model=list[DocumentOut])
def documents(user: User = Depends(current_user)):
    return [document_out(doc) for doc in accessible_documents(user)]


@app.get("/api/documents/{document_id}/content", response_model=DocumentContentOut)
def document_content(document_id: str, user: User = Depends(current_user)):
    doc = require_document(document_id)
    if doc.id not in {item.id for item in accessible_documents(user)}:
        raise HTTPException(status_code=403, detail="Vous n'avez pas accès à ce document")
    return DocumentContentOut(id=doc.id, title=doc.title, department=doc.department, content=doc.content)


@app.post("/api/documents", response_model=DocumentOut, status_code=201)
async def upload_document(file: UploadFile = File(...), user: User = Depends(admin_user)):
    data = await file.read()
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Le fichier dépasse la taille maximale autorisée")
    filename = file.filename or "Document sans titre"
    extension = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
    mime_types = {"pdf": "application/pdf", "txt": "text/plain", "md": "text/markdown"}
    mime_type = mime_types.get(extension)
    if mime_type is None or (mime_type == "application/pdf" and not data.startswith(b"%PDF-")):
        raise HTTPException(status_code=415, detail="Formats acceptés : PDF texte, TXT et Markdown")
    if settings.mock_llm:
        content = data.decode("utf-8", errors="ignore")
        doc = new_document(filename, "Général", content)
    else:
        doc = new_document(filename, "Général", "")
        doc.status = "PROCESSING"
        try:
            result = ingestion_service.ingest(doc.id, doc.title, doc.department, data, mime_type, sorted(doc.allowed_roles), sorted(doc.allowed_teams))
        except DocumentExtractionError as exc:
            DOCUMENTS.pop(doc.id, None)
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            DOCUMENTS.pop(doc.id, None)
            raise HTTPException(status_code=503, detail="L'indexation du document a échoué") from exc
        doc.content = result.content
        doc.chunks = result.chunks
        doc.status = "READY"
        doc.page_count = result.page_count
    with session_scope() as session:
        AuditRepository(session).record(user, "DOCUMENT_UPLOADED", doc.title, f"{len(doc.chunks)} fragment(s) indexé(s)")
    return document_out(doc)


@app.get("/api/documents/{document_id}/file")
def document_file(document_id: str, user: User = Depends(current_user)):
    doc = require_document(document_id)
    if doc.id not in {item.id for item in accessible_documents(user)}:
        raise HTTPException(status_code=403, detail="Vous n'avez pas accès à ce document")
    record = RagRepository().get_document(document_id)
    if record is None or not record.object_key:
        raise HTTPException(status_code=404, detail="Fichier original indisponible")
    data = object_storage.get(record.object_key)
    return Response(data, media_type=record.mime_type, headers={"Content-Disposition": f'inline; filename="{doc.title}"'})


@app.patch("/api/documents/{document_id}/access", response_model=DocumentOut)
def update_document_access(document_id: str, payload: DocumentAccessUpdate, actor: User = Depends(admin_user)):
    doc = require_document(document_id)
    roles = {validate_role(role) for role in payload.allowed_roles}
    with session_scope() as session:
        team_repository = TeamRepository(session)
        teams_set = validate_teams(team_repository, payload.allowed_teams)
        labels = team_repository.labels()
    doc.allowed_roles = roles
    doc.allowed_teams = teams_set
    if not settings.mock_llm:
        RagRepository().update_permissions(doc.id, sorted(roles), sorted(teams_set))
    detail = (
        f"Rôles : {', '.join(sorted(roles)) or 'aucun'} ; "
        f"équipes : {', '.join(sorted(team_label(labels, slug) for slug in teams_set)) or 'aucune'}"
    )
    with session_scope() as session:
        AuditRepository(session).record(actor, "DOCUMENT_ACCESS_CHANGED", doc.title, detail)
    return document_out(doc)


@app.delete("/api/documents/{document_id}", status_code=204)
def remove_document(document_id: str, actor: User = Depends(admin_user)):
    doc = require_document(document_id)
    DOCUMENTS.pop(document_id, None)
    if not settings.mock_llm:
        object_key = RagRepository().delete_document(document_id)
        if object_key:
            object_storage.delete(object_key)
    with session_scope() as session:
        AuditRepository(session).record(actor, "DOCUMENT_DELETED", doc.title, f"Service {doc.department}")
    return None


@app.get("/api/users", response_model=list[UserOut])
def users(_: User = Depends(admin_user)):
    with session_scope() as session:
        return [user_out(user) for user in UserRepository(session).list()]


@app.post("/api/users", response_model=UserOut, status_code=201)
def create_user(payload: UserCreate, actor: User = Depends(admin_user)):
    with session_scope() as session:
        users = UserRepository(session)
        teams_repository = TeamRepository(session)
        role = validate_role(payload.role)
        memberships = validate_teams(teams_repository, payload.teams)
        try:
            user = users.create(payload.email, payload.name, hash_password(payload.password), role, memberships)
        except RepositoryConflict as exc:
            raise HTTPException(status_code=409, detail="Un membre utilise déjà cette adresse e-mail") from exc
        labels_map = teams_repository.labels()
        labels = ", ".join(sorted(team_label(labels_map, slug) for slug in memberships)) or "aucune"
        AuditRepository(session).record(actor, "USER_CREATED", user.email, f"Rôle {role}, équipes {labels}")
        return user_out(user)


@app.patch("/api/users/{user_id}", response_model=UserOut)
def update_user(user_id: str, payload: UserUpdate, actor: User = Depends(admin_user)):
    with session_scope() as session:
        users = UserRepository(session)
        teams_repository = TeamRepository(session)
        user = require_user(users, user_id)
        changes = []
        role = None
        memberships = None
        if payload.role is not None and payload.role != user.role:
            role = validate_role(payload.role)
            if user.role == "ADMIN" and role != "ADMIN" and users.admin_ids() == {user.id}:
                raise HTTPException(status_code=409, detail="Dernier administrateur : promouvez un autre membre avant de rétrograder celui-ci")
            changes.append(f"Rôle {role}")
        if payload.teams is not None:
            memberships = validate_teams(teams_repository, payload.teams)
            if memberships != user.teams:
                labels_map = teams_repository.labels()
                labels = ", ".join(sorted(team_label(labels_map, slug) for slug in memberships)) or "aucune"
                changes.append(f"Équipes {labels}")
            else:
                memberships = None
        updated = users.update(user.id, role=role, teams=memberships)
        if changes:
            AuditRepository(session).record(actor, "USER_UPDATED", updated.email, " ; ".join(changes))
        return user_out(updated)


@app.delete("/api/users/{user_id}", status_code=204)
def remove_user(user_id: str, actor: User = Depends(admin_user)):
    with session_scope() as session:
        users = UserRepository(session)
        user = require_user(users, user_id)
        if user.id == actor.id:
            raise HTTPException(status_code=409, detail="Vous ne pouvez pas supprimer votre propre compte")
        users.delete(user.id)
        AuditRepository(session).record(actor, "USER_DELETED", user.email, f"Était {user.role}")
    return None


@app.get("/api/users/{user_id}/access", response_model=AccessPreview)
def user_access(user_id: str, _: User = Depends(admin_user)):
    """Computed through accessible_documents(), the same gate the chat endpoint uses."""
    with session_scope() as session:
        target = require_user(UserRepository(session), user_id)
        labels = TeamRepository(session).labels()
    allowed_ids = {doc.id for doc in accessible_documents(target)}
    entries = []
    for doc in DOCUMENTS.values():
        allowed = doc.id in allowed_ids
        reason = None
        if allowed:
            if target.role in doc.allowed_roles:
                reason = f"rôle {ROLE_LABELS.get(target.role, target.role)}"
            else:
                reason = "équipe " + team_label(labels, sorted(target.teams & doc.allowed_teams)[0])
        entries.append(AccessEntry(document_id=doc.id, title=doc.title, department=doc.department, allowed=allowed, reason=reason))
    return AccessPreview(user=user_out(target), entries=entries, allowed_count=len(allowed_ids), total_count=len(DOCUMENTS))


@app.get("/api/teams", response_model=list[TeamOut])
def teams(_: User = Depends(admin_user)):
    with session_scope() as session:
        all_users = UserRepository(session).list()
        result = []
        for team in TeamRepository(session).list():
            members = [MemberRef(id=user.id, name=user.name, email=user.email) for user in all_users if team.slug in user.teams]
            docs = [DocumentRef(id=doc.id, title=doc.title) for doc in DOCUMENTS.values() if team.slug in doc.allowed_teams]
            result.append(TeamOut(slug=team.slug, label=team.label, members=members, documents=docs, member_count=len(members)))
        return result


@app.get("/api/team-labels")
def team_labels(_: User = Depends(current_user)):
    """Slug to display name, for every signed-in account. Team names are not
    secret, and a member already sees the slugs of the teams they belong to."""
    with session_scope() as session:
        return TeamRepository(session).labels()


@app.post("/api/teams", response_model=TeamOut, status_code=201)
def create_team(payload: TeamCreate, actor: User = Depends(admin_user)):
    with session_scope() as session:
        try:
            team = TeamRepository(session).create(payload.slug, payload.label)
        except RepositoryConflict as exc:
            raise HTTPException(status_code=409, detail="Une équipe porte déjà cet identifiant") from exc
        AuditRepository(session).record(actor, "TEAM_CREATED", team.label, f"Identifiant {team.slug}")
        return TeamOut(slug=team.slug, label=team.label, members=[], documents=[], member_count=0)


@app.delete("/api/teams/{slug}", status_code=204)
def remove_team(slug: str, actor: User = Depends(admin_user)):
    """Cascades: the team is stripped from every member and every document."""
    with session_scope() as session:
        repository = TeamRepository(session)
        team = require_team(repository, slug)
        members, documents = repository.delete(slug)
        runtime_documents = [document for document in DOCUMENTS.values() if slug in document.allowed_teams]
        for document in runtime_documents:
            document.allowed_teams.discard(slug)
        documents = max(documents, len(runtime_documents))
        AuditRepository(session).record(actor, "TEAM_DELETED", team.label, f"{members} membre(s) et {documents} document(s) impactés")
    return None


@app.get("/api/access-matrix", response_model=AccessMatrix)
def access_matrix(_: User = Depends(admin_user)):
    docs = list(DOCUMENTS.values())
    with session_scope() as session:
        all_teams = TeamRepository(session).list()
    rows = [
        MatrixRow(kind="role", key=role, label=role, access={doc.id: role in doc.allowed_roles for doc in docs})
        for role in ROLES
    ]
    rows += [
        MatrixRow(kind="team", key=team.slug, label=team.label, access={doc.id: team.slug in doc.allowed_teams for doc in docs})
        for team in all_teams
    ]
    return AccessMatrix(documents=[document_out(doc) for doc in docs], rows=rows)


@app.get("/api/audit", response_model=list[AuditEventOut])
def audit_trail(
    actor: str | None = None,
    action: str | None = None,
    since: str | None = None,
    limit: int = 200,
    _: User = Depends(admin_user),
):
    with session_scope() as session:
        return AuditRepository(session).query(actor=actor, action=action, since=since, limit=limit)


@app.get("/api/analytics", response_model=Analytics)
def analytics(days: int = ANALYTICS_DAYS, _: User = Depends(admin_user)):
    days = max(1, min(days, 90))
    today = datetime.now(timezone.utc).date()
    first_day = today - timedelta(days=days - 1)

    with session_scope() as session:
        user_repository = UserRepository(session)
        all_users = user_repository.list()
        users_by_email = {user.email: user for user in all_users}
        team_repository = TeamRepository(session)
        all_teams = team_repository.list()
        labels = team_repository.labels()
        questions = AuditRepository(session).query(action="QUESTION_ASKED", limit=100000)
    in_period = [event for event in questions if datetime.fromisoformat(event.timestamp).date() >= first_day]

    per_day = Counter(datetime.fromisoformat(event.timestamp).date() for event in in_period)
    questions_per_day = [
        DailyCount(
            date=(first_day + timedelta(days=offset)).isoformat(),
            count=per_day.get(first_day + timedelta(days=offset), 0),
        )
        for offset in range(days)
    ]

    document_hits: Counter = Counter()
    team_hits: Counter = Counter()
    member_hits: Counter = Counter()
    for event in in_period:
        # Counted from the structured payload, not by splitting the display string.
        for document_id in event.meta.get("document_ids", []):
            document_hits[document_id] += 1
        member_hits[event.actor_email] += 1
        actor = users_by_email.get(event.actor_email)
        for slug in actor.teams if actor else []:
            team_hits[slug] += 1

    top_documents = [
        LabelCount(key=document_id, label=DOCUMENTS[document_id].title, count=count)
        for document_id, count in document_hits.most_common(6)
        if document_id in DOCUMENTS
    ]
    activity_by_team = [
        LabelCount(key=team.slug, label=team.label, count=team_hits.get(team.slug, 0))
        for team in sorted(all_teams, key=lambda item: (-team_hits.get(item.slug, 0), item.label))
    ]
    top_members = [
        LabelCount(key=email, label=users_by_email[email].name, count=count)
        for email, count in member_hits.most_common(6)
        if email in users_by_email
    ]

    # A document nobody can reach is dead weight in the index; surface it rather
    # than let it sit there looking indexed.
    reachable: set[str] = set()
    for user in all_users:
        reachable |= {doc.id for doc in accessible_documents(user)}

    alerts = AnalyticsAlerts(
        unreachable_documents=[
            DocumentRef(id=doc.id, title=doc.title) for doc in DOCUMENTS.values() if doc.id not in reachable
        ],
        members_without_team=[
            MemberRef(id=user.id, name=user.name, email=user.email)
            for user in all_users
            if user.role != "ADMIN" and not user.teams
        ],
        empty_teams=[
            LabelCount(key=slug, label=team.label, count=0)
            for team in sorted(all_teams, key=lambda item: item.label)
            for slug in [team.slug]
            if not any(slug in user.teams for user in all_users)
        ],
    )

    return Analytics(
        days=days,
        total_questions=len(questions),
        questions_in_period=len(in_period),
        active_members=len(member_hits),
        questions_per_day=questions_per_day,
        top_documents=top_documents,
        activity_by_team=activity_by_team,
        top_members=top_members,
        alerts=alerts,
    )


def _conversation_summary(record) -> ConversationSummary:
    return ConversationSummary(id=record.id, title=record.title, created_at=record.created_at, updated_at=record.updated_at)


def _conversation_out(record) -> ConversationOut:
    return ConversationOut(
        **_conversation_summary(record).model_dump(),
        messages=[ConversationMessageOut(
            id=message.id, role=message.role, content=message.content, sources=message.sources or [],
            status=message.status, created_at=message.created_at,
        ) for message in record.messages],
    )


@app.get("/api/conversations", response_model=list[ConversationSummary])
def list_conversations(user: User = Depends(current_user)):
    with session_scope() as session:
        return [_conversation_summary(item) for item in ConversationRepository(session).list_for_owner(user.id)]


@app.post("/api/conversations", response_model=ConversationSummary, status_code=201)
def create_conversation(payload: ConversationCreate, user: User = Depends(current_user)):
    with session_scope() as session:
        return _conversation_summary(ConversationRepository(session).create(user.id, payload.title))


@app.get("/api/conversations/{conversation_id}", response_model=ConversationOut)
def get_conversation(conversation_id: str, user: User = Depends(current_user)):
    with session_scope() as session:
        record = ConversationRepository(session).get_for_owner(conversation_id, user.id)
        if record is None:
            raise HTTPException(status_code=404, detail="Conversation introuvable")
        return _conversation_out(record)


@app.delete("/api/conversations/{conversation_id}", status_code=204)
def delete_conversation(conversation_id: str, user: User = Depends(current_user)):
    with session_scope() as session:
        if not ConversationRepository(session).delete(conversation_id, user.id):
            raise HTTPException(status_code=404, detail="Conversation introuvable")
    return Response(status_code=204)


@app.post("/api/conversations/{conversation_id}/messages", response_model=ConversationOut, status_code=201)
async def create_conversation_message(conversation_id: str, payload: ChatRequest, user: User = Depends(current_user)):
    with session_scope() as session:
        record = ConversationRepository(session).get_for_owner(conversation_id, user.id)
        if record is None:
            raise HTTPException(status_code=404, detail="Conversation introuvable")
    try:
        response = await answer_question(payload.question, user)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Le modèle local ne répond pas. Réessayez dans un instant.") from exc
    with session_scope() as session:
        repository = ConversationRepository(session)
        record = repository.get_for_owner(conversation_id, user.id)
        if record is None:
            raise HTTPException(status_code=404, detail="Conversation introuvable")
        record = repository.append_exchange(record, payload.question, response.answer, [item.model_dump() for item in response.sources])
        titles = source_document_titles(response)
        AuditRepository(session).record(user, "QUESTION_ASKED", payload.question,
                                        "Sources : " + (", ".join(titles) or "aucune"),
                                        {"document_ids": [item.document_id for item in response.sources]})
        return _conversation_out(record)


@app.post("/api/chat", response_model=ChatResponse)
async def chat(payload: ChatRequest, user: User = Depends(current_user)):
    response = await answer_question(payload.question, user)
    titles = source_document_titles(response)
    with session_scope() as session:
        AuditRepository(session).record(user, "QUESTION_ASKED", payload.question,
                                        "Sources : " + (", ".join(titles) or "aucune"),
                                        {"document_ids": [item.document_id for item in response.sources]})
    return response
