from .store import DOCUMENTS, User
from .config import settings
from .embeddings import embedding_service
from .rag_repository import RagRepository


def accessible_documents(user: User):
    """Authorization boundary: called before any similarity/retrieval operation."""
    return [
        doc for doc in DOCUMENTS.values()
        if user.role in doc.allowed_roles or bool(user.teams & doc.allowed_teams)
    ]


import re

STOP_WORDS = {"qui", "que", "quoi", "dans", "pour", "avec", "sans", "une", "des", "les", "est", "es", "le", "la", "de", "du", "un", "et", "sur", "aux", "the", "what", "who", "is", "are"}
QUERY_ALIASES = {
    "onboarding": {"intégration", "integration"},
    "checklist": {"intégration", "integration", "onboarding"},
    "hr": {"rh"},
}


def retrieve(question: str, user: User, limit: int = 4):
    question_words = {
        word for word in re.findall(r"[\wÀ-ÿ]+", question.lower())
        if len(word) > 2 and word not in STOP_WORDS
    }
    expanded_words = question_words | {alias for word in question_words for alias in QUERY_ALIASES.get(word, set())}
    candidates = []
    for doc in accessible_documents(user):
        searchable = f"{doc.title} {doc.content}".lower()
        score = sum(word in searchable for word in expanded_words)
        candidates.append((score, doc))
    ranked = [doc for score, doc in sorted(candidates, key=lambda item: item[0], reverse=True) if score > 0]
    return ranked[:limit]


class DenseRetriever:
    def __init__(self, repository=None, embeddings=None):
        self.repository = repository or RagRepository()
        self.embeddings = embeddings or embedding_service

    def search(self, question: str, user: User, limit: int | None = None):
        allowed_ids = [document.id for document in accessible_documents(user)]
        vector = self.embeddings.embed_query(question)
        return self.repository.search(
            vector,
            allowed_ids,
            limit or settings.retrieval_limit,
            settings.retrieval_threshold,
        )


dense_retriever = DenseRetriever()
