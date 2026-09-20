import fitz
import pytest

from app.ingestion import IngestionService


def pdf_bytes(text="Politique de télétravail"):
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), text)
    result = document.tobytes()
    document.close()
    return result


class FakeEmbeddings:
    def embed_documents(self, texts):
        return [[1.0, 0.0, 0.0] for _ in texts]


class FakeStorage:
    def __init__(self):
        self.objects = {}

    def put(self, key, data, content_type):
        self.objects[key] = data

    def delete(self, key):
        self.objects.pop(key, None)


class FakeRepository:
    def __init__(self, fail=False):
        self.fail = fail
        self.call = None

    def upsert_document(self, *args):
        if self.fail:
            raise RuntimeError("database unavailable")
        self.call = args


def test_ingestion_extracts_chunks_embeds_and_stores():
    storage = FakeStorage()
    repository = FakeRepository()
    result = IngestionService(repository, FakeEmbeddings(), storage).ingest(
        "doc-1", "politique.pdf", "RH", pdf_bytes(), "application/pdf", ["ADMIN"], ["rh"]
    )

    assert result.page_count == 1
    assert result.chunk_count == 1
    assert result.object_key in storage.objects
    assert repository.call[0:3] == ("doc-1", "politique.pdf", "RH")


def test_ingestion_compensates_object_when_database_fails():
    storage = FakeStorage()
    service = IngestionService(FakeRepository(fail=True), FakeEmbeddings(), storage)

    with pytest.raises(RuntimeError, match="database unavailable"):
        service.ingest("doc-1", "politique.pdf", "RH", pdf_bytes(), "application/pdf", ["ADMIN"], [])

    assert storage.objects == {}
