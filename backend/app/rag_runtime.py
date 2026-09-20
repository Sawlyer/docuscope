from .database import init_database
from .rag_repository import RagRepository
from .storage import object_storage
from .store import DOCUMENTS, Document


LEGACY_DOCUMENT_IDS = frozenset(DOCUMENTS)


def hydrate_documents(records, target) -> None:
    for record in records:
        chunks = [chunk.text for chunk in sorted(record.chunks, key=lambda item: item.chunk_index)]
        document = Document(
            id=record.id,
            title=record.title,
            department=record.department,
            content="\n\n".join(chunks),
            allowed_roles=set(record.allowed_roles),
            allowed_teams=set(record.allowed_teams),
            status=record.status,
            chunks=chunks,
        )
        document.page_count = record.page_count
        document.object_key = getattr(record, "object_key", None)
        document.mime_type = getattr(record, "mime_type", "text/plain")
        target[document.id] = document


def replace_with_persisted_documents(repository, target, legacy_document_ids) -> None:
    repository.delete_documents(legacy_document_ids)
    target.clear()
    hydrate_documents(repository.list_documents(), target)


def initialize_rag() -> None:
    init_database()
    object_storage.ensure_bucket()
    repository = RagRepository()
    replace_with_persisted_documents(repository, DOCUMENTS, LEGACY_DOCUMENT_IDS)
