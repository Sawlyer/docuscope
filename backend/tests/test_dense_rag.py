from dataclasses import dataclass
from types import SimpleNamespace


class FakeModel:
    def __init__(self):
        self.inputs = []

    def embed(self, texts):
        self.inputs.extend(texts)
        for text in texts:
            yield [1.0, 0.0, 0.0]


def test_embedding_service_uses_e5_prefixes():
    from app.embeddings import EmbeddingService

    model = FakeModel()
    service = EmbeddingService(model=model)

    assert service.embed_documents(["politique RH"]) == [[1.0, 0.0, 0.0]]
    assert service.embed_query("congés") == [1.0, 0.0, 0.0]
    assert model.inputs == ["passage: politique RH", "query: congés"]


@dataclass
class FakeDocument:
    id: str


class FakeRepository:
    def __init__(self):
        self.allowed_ids = None

    def search(self, vector, allowed_document_ids, limit, threshold):
        self.allowed_ids = allowed_document_ids
        return []


def test_dense_retriever_passes_only_authorized_ids(monkeypatch):
    from app.embeddings import EmbeddingService
    from app.retrieval import DenseRetriever

    repository = FakeRepository()
    retriever = DenseRetriever(repository, EmbeddingService(model=FakeModel()))
    monkeypatch.setattr("app.retrieval.accessible_documents", lambda user: [FakeDocument("allowed")])

    retriever.search("secret", object())

    assert repository.allowed_ids == ["allowed"]


def test_low_similarity_results_are_not_returned():
    from app.rag_repository import filter_by_threshold

    rows = [
        {"id": "low", "similarity": 0.69},
        {"id": "edge", "similarity": 0.70},
        {"id": "high", "similarity": 0.91},
    ]

    assert [row["id"] for row in filter_by_threshold(rows, 0.70)] == ["edge", "high"]


def test_e5_small_is_registered_when_fastembed_does_not_bundle_it(monkeypatch):
    from app import embeddings

    calls = []

    class FakeTextEmbedding:
        @staticmethod
        def list_supported_models():
            return []

        @staticmethod
        def add_custom_model(**kwargs):
            calls.append(kwargs)

        def __init__(self, **kwargs):
            self.kwargs = kwargs

    monkeypatch.setattr(embeddings, "TextEmbedding", FakeTextEmbedding)
    service = embeddings.EmbeddingService()

    assert service.model.kwargs["model_name"] == "intfloat/multilingual-e5-small"
    assert calls[0]["dim"] == 384


def test_persisted_documents_are_hydrated_into_runtime_store():
    from app.rag_runtime import hydrate_documents

    target = {}
    record = SimpleNamespace(
        id="uploaded-contract",
        title="Contrat partenaire",
        department="Juridique",
        allowed_roles=["ADMIN"],
        allowed_teams=["leadership"],
        status="READY",
        page_count=2,
        chunks=[
            SimpleNamespace(chunk_index=1, text="Clause de confidentialité."),
            SimpleNamespace(chunk_index=0, text="Durée du contrat : trois ans."),
        ],
    )

    hydrate_documents([record], target)

    document = target["uploaded-contract"]
    assert document.title == "Contrat partenaire"
    assert document.allowed_roles == {"ADMIN"}
    assert document.allowed_teams == {"leadership"}
    assert document.chunks == ["Durée du contrat : trois ans.", "Clause de confidentialité."]
    assert document.content == "Durée du contrat : trois ans.\n\nClause de confidentialité."


def test_production_runtime_replaces_legacy_seed_documents_with_uploaded_files():
    from app.rag_runtime import replace_with_persisted_documents

    uploaded = SimpleNamespace(
        id="uploaded-policy",
        title="Politique réelle.pdf",
        department="Général",
        allowed_roles=["ADMIN"],
        allowed_teams=[],
        status="READY",
        page_count=1,
        object_key="uploaded-policy/original.pdf",
        mime_type="application/pdf",
        chunks=[SimpleNamespace(chunk_index=0, text="Politique réellement importée.")],
    )

    class FakeRepository:
        def __init__(self):
            self.deleted = None

        def delete_documents(self, document_ids):
            self.deleted = set(document_ids)

        def list_documents(self):
            return [uploaded]

    repository = FakeRepository()
    target = {"doc-finance": object(), "doc-handbook": object()}

    replace_with_persisted_documents(repository, target, {"doc-finance", "doc-handbook"})

    assert repository.deleted == {"doc-finance", "doc-handbook"}
    assert list(target) == ["uploaded-policy"]
    assert target["uploaded-policy"].object_key == "uploaded-policy/original.pdf"
