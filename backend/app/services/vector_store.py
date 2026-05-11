"""Per-session in-memory vector store backed by numpy cosine similarity."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.services.repo_ingestion import CodeChunk


@dataclass
class SearchResult:
    chunk: CodeChunk
    score: float


class VectorStore:
    def __init__(self) -> None:
        self._chunks: list[CodeChunk] = []
        self._matrix: np.ndarray | None = None

    def add(self, chunks: list[CodeChunk], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self._chunks.extend(chunks)
        new_rows = np.array(embeddings, dtype=np.float32)
        # L2-normalise each row in-place
        norms = np.linalg.norm(new_rows, axis=1, keepdims=True) + 1e-10
        new_rows /= norms

        self._matrix = new_rows if self._matrix is None else np.vstack([self._matrix, new_rows])

    def search(self, query_embedding: list[float], top_k: int = 8) -> list[SearchResult]:
        if self._matrix is None or not self._chunks:
            return []

        q = np.array(query_embedding, dtype=np.float32)
        q /= np.linalg.norm(q) + 1e-10

        scores: np.ndarray = self._matrix @ q  # cosine similarity
        k = min(top_k, len(self._chunks))
        top_idx = np.argpartition(scores, -k)[-k:]  # fast partial sort
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]

        return [SearchResult(chunk=self._chunks[i], score=float(scores[i])) for i in top_idx]

    @property
    def size(self) -> int:
        return len(self._chunks)
