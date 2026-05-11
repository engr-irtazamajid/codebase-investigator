"""Tests for the TF-IDF keyword search store."""

from app.services.tfidf_store import TFIDFStore, _tokenize


class TestTokenizer:
    def test_basic_words(self):
        assert "authenticate" in _tokenize("authenticate user")

    def test_camel_case_split(self):
        tokens = _tokenize("authenticateUser")
        assert "authenticate" in tokens
        assert "user" in tokens

    def test_snake_case_preserved(self):
        tokens = _tokenize("authenticate_user")
        # underscore is a word char, so the whole token stays
        assert any("authenticate" in t for t in tokens)

    def test_short_tokens_filtered(self):
        tokens = _tokenize("a b authenticate")
        assert "a" not in tokens
        assert "b" not in tokens
        assert "authenticate" in tokens

    def test_lowercasing(self):
        tokens = _tokenize("FastAPI Router")
        assert "fast" in tokens or "fastapi" in tokens
        assert "router" in tokens


class TestTFIDFStore:
    def test_empty_store_returns_empty(self):
        store = TFIDFStore()
        results = store.search("authentication", top_k=5)
        assert results == []

    def test_size_property(self, sample_chunks):
        store = TFIDFStore()
        store.add(sample_chunks)
        assert store.size == len(sample_chunks)

    def test_search_returns_limited_results(self, sample_chunks):
        store = TFIDFStore()
        store.add(sample_chunks)
        results = store.search("user", top_k=2)
        assert len(results) <= 2

    def test_auth_query_ranks_auth_chunk_highest(self, sample_chunks):
        store = TFIDFStore()
        store.add(sample_chunks)
        results = store.search("jwt token authentication", top_k=3)
        assert len(results) > 0
        # The auth chunk should score highest
        top = results[0].chunk
        assert "auth" in top.file_path

    def test_user_query_ranks_user_model_chunk(self, sample_chunks):
        store = TFIDFStore()
        store.add(sample_chunks)
        results = store.search("user email class model", top_k=3)
        assert len(results) > 0
        top_paths = [r.chunk.file_path for r in results]
        assert any("model" in p for p in top_paths)

    def test_scores_between_zero_and_one(self, sample_chunks):
        store = TFIDFStore()
        store.add(sample_chunks)
        results = store.search("authentication jwt", top_k=5)
        for r in results:
            assert 0.0 <= r.score <= 1.0 + 1e-6   # allow float tolerance

    def test_results_sorted_descending(self, sample_chunks):
        store = TFIDFStore()
        store.add(sample_chunks)
        results = store.search("authentication", top_k=5)
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    def test_add_incremental(self, sample_chunks):
        store = TFIDFStore()
        store.add(sample_chunks[:1])
        store.add(sample_chunks[1:])
        assert store.size == len(sample_chunks)
        results = store.search("jwt", top_k=3)
        assert len(results) > 0
