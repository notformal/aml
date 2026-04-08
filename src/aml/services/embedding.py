import logging

from openai import AsyncOpenAI

from aml.config import settings

logger = logging.getLogger(__name__)

_client: AsyncOpenAI | None = None


def _get_client() -> AsyncOpenAI:
    global _client
    if _client is None:
        _client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


async def embed_text(text: str) -> list[float] | None:
    """Generate embedding for text. Returns None if API key is not configured."""
    if not settings.openai_api_key:
        logger.warning("OPENAI_API_KEY not set — skipping embedding")
        return None

    client = _get_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=text,
        dimensions=settings.embedding_dimensions,
    )
    return response.data[0].embedding


async def embed_texts(texts: list[str]) -> list[list[float] | None]:
    """Batch embed multiple texts."""
    if not settings.openai_api_key:
        return [None] * len(texts)

    client = _get_client()
    response = await client.embeddings.create(
        model=settings.embedding_model,
        input=texts,
        dimensions=settings.embedding_dimensions,
    )
    return [item.embedding for item in response.data]
