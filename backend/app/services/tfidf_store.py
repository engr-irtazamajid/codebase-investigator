"""
TF-IDF keyword search store — zero external dependencies, pure numpy.

Used automatically when GEMINI_API_KEY is not set.
Quality is lower than embedding-based search but works well for code
(identifiers, function names, and keywords are highly discriminative).
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass

import numpy as np

from app.services.repo_ingestion import CodeChunk

_IDENT_RE = re.compile(r"[a-zA-Z_]\w*|\d+")


def _tokenize(text: str) -> list[str]:
    """
    Code-aware tokenizer: splits camelCase/snake_case identifiers and
    keeps numeric literals alongside regular words.
    """
    tokens: list[str] = []
    for raw in _IDENT_RE.findall(text):
        # Split camelCase → ["camel", "case"]
        parts = re.sub(r"([a-z])([A-Z])", r"\1 \2", raw).split()
        # Split snake_case → already split by re above, just lower-case
        tokens.extend(p.lower() for p in parts if len(p) > 1)
    return tokens


@dataclass
class SearchResult:
    chunk: CodeChunk
    score: float


class TFIDFStore:
    """In-memory TF-IDF index with cosine similarity search."""

    def __init__(self) -> None:
        self._chunks: list[CodeChunk] = []
        self._vocab: dict[str, int] = {}
        self._matrix: np.ndarray | None = None
        self._idf: np.ndarray | None = None  # set to ndarray after first _rebuild()

    def add(self, chunks: list[CodeChunk]) -> None:
        if not chunks:
            return
        self._chunks.extend(chunks)
        self._rebuild()

    def _rebuild(self) -> None:
        corpus = [_tokenize(c.content) for c in self._chunks]
        n_docs = len(corpus)

        all_terms: set[str] = {t for doc in corpus for t in doc}
        self._vocab = {t: i for i, t in enumerate(sorted(all_terms))}
        vocab_size = len(self._vocab)

        tf = np.zeros((n_docs, vocab_size), dtype=np.float32)
        for i, doc in enumerate(corpus):
            if not doc:
                continue
            counts = Counter(doc)
            length = len(doc)
            for term, cnt in counts.items():
                j = self._vocab[term]
                tf[i, j] = cnt / length

        df = (tf > 0).astype(np.float32).sum(axis=0)
        idf: np.ndarray = np.log((n_docs + 1.0) / (df + 1.0)) + 1.0
        self._idf = idf

        tfidf = tf * idf
        norms = np.linalg.norm(tfidf, axis=1, keepdims=True) + 1e-10
        self._matrix = tfidf / norms

    def search(self, query: str, top_k: int = 8) -> list[SearchResult]:
        if self._matrix is None or not self._chunks:
            return []

        tokens = _tokenize(query)
        if not tokens:
            return []

        vocab_size = len(self._vocab)
        q_vec = np.zeros(vocab_size, dtype=np.float32)
        counts = Counter(tokens)
        length = len(tokens)
        for term, cnt in counts.items():
            j = self._vocab.get(term)
            if j is not None and self._idf is not None:
                q_vec[j] = (cnt / length) * self._idf[j]

        norm = np.linalg.norm(q_vec) + 1e-10
        q_vec /= norm

        scores: np.ndarray = self._matrix @ q_vec
        k = min(top_k, len(self._chunks))
        top_idx = np.argpartition(scores, -k)[-k:]
        top_idx = top_idx[np.argsort(scores[top_idx])[::-1]]

        return [SearchResult(chunk=self._chunks[i], score=float(scores[i])) for i in top_idx]

    @property
    def size(self) -> int:
        return len(self._chunks)
