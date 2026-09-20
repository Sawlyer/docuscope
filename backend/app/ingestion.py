from dataclasses import dataclass
from uuid import uuid4

from .chunking import chunk_pages
from .embeddings import embedding_service
from .extractors import extract_document
from .rag_repository import RagRepository
from .storage import object_storage, safe_filename


@dataclass(frozen=True)
class IngestionResult:
    object_key: str
    page_count: int
    chunk_count: int
    content: str
    chunks: list[str]


class IngestionService:
    def __init__(self, repository=None, embeddings=None, storage=None):
        self.repository = repository or RagRepository()
        self.embeddings = embeddings or embedding_service
        self.storage = storage or object_storage

    def ingest(self, document_id: str, title: str, department: str, data: bytes, mime_type: str,
               allowed_roles: list[str], allowed_teams: list[str]) -> IngestionResult:
        pages = extract_document(data, mime_type)
        chunks = chunk_pages(pages)
        vectors = self.embeddings.embed_documents([chunk.text for chunk in chunks])
        key = f"documents/{document_id}/{safe_filename(title)}"
        self.storage.put(key, data, mime_type)
        try:
            self.repository.upsert_document(
                document_id, title, department, mime_type, key,
                allowed_roles, allowed_teams, chunks, vectors,
            )
        except Exception:
            self.storage.delete(key)
            raise
        return IngestionResult(key, len(pages), len(chunks), "\n\n".join(page.text for page in pages), [chunk.text for chunk in chunks])


ingestion_service = IngestionService()
