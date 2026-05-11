"""Thin wrapper around Gemini's embedding API with batching and retry."""
from __future__ import annotations

import asyncio

import google.generativeai as genai

from app.core.config import get_settings


def _embed_batch_sync(texts: list[str], task_type: str) -> list[list[float]]:
    # Always read fresh settings so the API key is never stale (no lru_cache here)
    settings = get_settings()
    if not settings.gemini_api_key:
        raise RuntimeError(
            "GEMINI_API_KEY is not set. Embeddings require Gemini — "
            "add it to backend/.env and restart the server."
        )
    genai.configure(api_key=settings.gemini_api_key)

    embeddings: list[list[float]] = []
    for text in texts:
        result = genai.embed_content(
            model=settings.embedding_model,
            content=text,
            task_type=task_type,
        )
        embeddings.append(result["embedding"])
    return embeddings


async def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed a list of document strings; runs in a thread pool to avoid blocking."""
    settings = get_settings()
    batch_size = settings.embedding_batch_size
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), batch_size):
        batch = texts[i : i + batch_size]
        embeddings = await asyncio.get_event_loop().run_in_executor(
            None, _embed_batch_sync, batch, "retrieval_document"
        )
        all_embeddings.extend(embeddings)
        if i + batch_size < len(texts):
            await asyncio.sleep(1.0)

    return all_embeddings


async def embed_query(text: str) -> list[float]:
    """Embed a single search query."""
    results = await asyncio.get_event_loop().run_in_executor(
        None, _embed_batch_sync, [text], "retrieval_query"
    )
    return results[0]
