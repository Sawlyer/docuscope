import httpx

from .config import settings


async def generate(question: str, context: str) -> str:
    system_prompt = (
        "Tu es DocuScope, un assistant de connaissances d'entreprise. Réponds toujours en français. "
        "Pour les questions générales et calculs simples, réponds directement. "
        "Pour les informations internes, utilise uniquement le contexte fourni et n'invente jamais. "
        "Si le contexte ne permet pas de répondre à une question interne, dis-le clairement. "
        "Cite les sources avec [1], [2] quand elles existent."
    )
    if settings.mock_llm:
        if not context.strip():
            return "Je ne trouve pas cette information dans les documents auxquels vous avez accès."
        return f"Selon les documents autorisés, voici la synthèse : {context[:500]}\n\nSources : [1]"
    payload = {"model": settings.lm_studio_model, "system_prompt": system_prompt, "input": f"Context:\n{context}\n\nQuestion: {question}"}
    async with httpx.AsyncClient(timeout=settings.lm_studio_timeout) as client:
        response = await client.post(settings.lm_studio_url, json=payload)
        response.raise_for_status()
        data = response.json()
    output = data.get("output")
    if isinstance(output, list):
        messages = [item.get("content", "") for item in output if item.get("type") == "message"]
        return "\n".join(message for message in messages if message).strip() or "No answer returned"
    if isinstance(output, str):
        return output
    response = data.get("response")
    if isinstance(response, str):
        return response
    choices = data.get("choices") or []
    return choices[0].get("message", {}).get("content", "No answer returned") if choices else "No answer returned"
