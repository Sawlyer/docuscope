from .config import settings
from .llm import generate
from .retrieval import dense_retriever, retrieve
from .schemas import ChatResponse, Source
from .store import DOCUMENTS, User


async def answer_question(question: str, user: User) -> ChatResponse:
    if settings.mock_llm:
        documents = retrieve(question, user)
        sources = [Source(document_id=item.id, title=item.title, excerpt=item.content[:220]) for item in documents]
        context = "\n\n".join(f"[{index}] {item.title}: {item.content}" for index, item in enumerate(documents, 1))
    else:
        hits = dense_retriever.search(question, user)
        context_parts: list[str] = []
        sources: list[Source] = []
        size = 0
        for index, hit in enumerate(hits, 1):
            block = f"[{index}] {hit.title}, page {hit.page}: {hit.text}"
            if size + len(block) > settings.rag_context_max_chars:
                break
            context_parts.append(block)
            size += len(block)
            sources.append(Source(document_id=hit.document_id, title=hit.title, page=hit.page,
                                  excerpt=hit.text[:280], similarity=round(hit.similarity, 4),
                                  file_url=f"/api/documents/{hit.document_id}/file"))
        context = "\n\n".join(context_parts)

    return ChatResponse(answer=await generate(question, context), sources=sources)


def source_document_titles(response: ChatResponse) -> list[str]:
    return [DOCUMENTS[item.document_id].title for item in response.sources if item.document_id in DOCUMENTS]
