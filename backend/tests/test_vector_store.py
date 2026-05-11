"""Tests for the numpy cosine-similarity vector store."""
import numpy as np

from app.services.vector_store import VectorStore


def _random_embedding(dim: int = 8) -> list[float]:
    v = np.random.randn(dim).astype(float)
    return (v / np.linalg.norm(v)).tolist()


class TestVectorStore:
    def test_empty_store_returns_empty(self):
        store = VectorStore()
        results = store.search(_random_embedding(), top_k=5)
        assert results == []

    def test_size_property(self, sample_chunks):
        store = VectorStore()
        embeddings = [_random_embedding() for _ in sample_chunks]
        store.add(sample_chunks, embeddings)
        assert store.size == len(sample_chunks)

    def test_search_returns_limited_results(self, sample_chunks):
        store = VectorStore()
        embeddings = [_random_embedding() for _ in sample_chunks]
        store.add(sample_chunks, embeddings)
        results = store.search(_random_embedding(), top_k=2)
        assert len(results) <= 2

    def test_exact_match_scores_near_one(self, sample_chunks):
        store = VectorStore()
        # All embeddings are the same unit vector
        emb = _random_embedding()
        store.add(sample_chunks, [emb] * len(sample_chunks))
        # Query with the exact same vector → cosine similarity = 1.0
        results = store.search(emb, top_k=1)
        assert abs(results[0].score - 1.0) < 1e-5

    def test_opposite_vector_scores_near_minus_one(self, sample_chunks):
        store = VectorStore()
        emb = _random_embedding()
        store.add(sample_chunks, [emb])
        opposite = [-x for x in emb]
        results = store.search(opposite, top_k=1)
        assert results[0].score < 0

    def test_results_sorted_descending(self, sample_chunks):
        store = VectorStore()
        embeddings = [_random_embedding() for _ in sample_chunks]
        store.add(sample_chunks, embeddings)
        results = store.search(_random_embedding(), top_k=len(sample_chunks))
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_add_chunks_match_returned_chunks(self, sample_chunks):
        store = VectorStore()
        embeddings = [_random_embedding() for _ in sample_chunks]
        store.add(sample_chunks, embeddings)
        results = store.search(_random_embedding(), top_k=len(sample_chunks))
        returned_ids = {r.chunk.id for r in results}
        original_ids = {c.id for c in sample_chunks}
        assert returned_ids == original_ids
