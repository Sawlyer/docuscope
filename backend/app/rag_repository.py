from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from .config import settings
from .database import SessionLocal
from .rag_models import RagChunk, RagDocument


@dataclass(frozen=True)
class RagHit:
    chunk_id: int
    document_id: str
    title: str
    page: int
    text: str
    similarity: float


def filter_by_threshold(rows, threshold: float):
    return [row for row in rows if row["similarity"] >= threshold]


class RagRepository:
    def list_documents(self):
        query = select(RagDocument).options(selectinload(RagDocument.chunks))
        with SessionLocal() as session:
            documents = list(session.scalars(query).all())
            session.expunge_all()
        return documents

    def search(self, vector, allowed_document_ids, limit=None, threshold=None) -> list[RagHit]:
        if not allowed_document_ids:
            return []
        limit = limit or settings.retrieval_limit
        threshold = settings.retrieval_threshold if threshold is None else threshold
        similarity = (1 - RagChunk.embedding.cosine_distance(vector)).label("similarity")
        query = (
            select(RagChunk, RagDocument.title, similarity)
            .join(RagDocument, RagDocument.id == RagChunk.document_id)
            .where(RagChunk.document_id.in_(allowed_document_ids), RagDocument.status == "READY", similarity >= threshold)
            .order_by(similarity.desc())
            .limit(limit)
        )
        with SessionLocal() as session:
            rows = session.execute(query).all()
        return [RagHit(chunk.id, chunk.document_id, title, chunk.page, chunk.text, float(score)) for chunk, title, score in rows]

    def upsert_document(self, document_id: str, title: str, department: str, mime_type: str, object_key: str | None,
                        allowed_roles: list[str], allowed_teams: list[str], pages, vectors) -> None:
        with SessionLocal.begin() as session:
            existing = session.get(RagDocument, document_id)
            if existing:
                session.execute(delete(RagChunk).where(RagChunk.document_id == document_id))
                document = existing
            else:
                document = RagDocument(id=document_id)
                session.add(document)
            document.title = title
            document.department = department
            document.mime_type = mime_type
            document.object_key = object_key
            document.allowed_roles = allowed_roles
            document.allowed_teams = allowed_teams
            document.status = "READY"
            document.page_count = max((chunk.page for chunk in pages), default=0)
            document.chunk_count = len(pages)
            document.error = None
            for chunk, vector in zip(pages, vectors, strict=True):
                session.add(RagChunk(document_id=document_id, page=chunk.page, chunk_index=chunk.index, text=chunk.text, embedding=vector))

    def update_permissions(self, document_id: str, roles: list[str], teams: list[str]) -> None:
        with SessionLocal.begin() as session:
            document = session.get(RagDocument, document_id)
            if document:
                document.allowed_roles = roles
                document.allowed_teams = teams

    def delete_document(self, document_id: str) -> str | None:
        with SessionLocal.begin() as session:
            document = session.get(RagDocument, document_id)
            if not document:
                return None
            object_key = document.object_key
            session.delete(document)
            return object_key

    def delete_documents(self, document_ids) -> None:
        ids = list(document_ids)
        if not ids:
            return
        with SessionLocal.begin() as session:
            session.execute(delete(RagDocument).where(RagDocument.id.in_(ids)))

    def get_document(self, document_id: str):
        with SessionLocal() as session:
            document = session.get(RagDocument, document_id)
            if not document:
                return None
            session.expunge(document)
            return document
