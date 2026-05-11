"""Tests for session management, claim registry, and digest generation."""
import pytest

from app.services.conversation import Claim, Session, create_session, get_session
from app.services.tfidf_store import TFIDFStore


@pytest.fixture
def session(sample_chunks) -> Session:
    store = TFIDFStore()
    store.add(sample_chunks)
    return create_session(
        session_id="test-session-001",
        repo_name="test-repo",
        temp_dir="/tmp/test",
        store=store,
    )


class TestSessionTurns:
    def test_initial_turn_is_zero(self, session):
        assert session.turn == 0

    def test_turn_increments_on_user_message(self, session):
        session.add_user_message("How does auth work?")
        assert session.turn == 1

    def test_add_user_message_returns_turn_number(self, session):
        t = session.add_user_message("Question?")
        assert t == 1

    def test_multiple_turns(self, session):
        session.add_user_message("Q1")
        session.add_user_message("Q2")
        assert session.turn == 2


class TestClaimRegistry:
    def test_claims_registered(self, session):
        session.add_user_message("Q")
        claims = [Claim(turn=1, text="Auth uses JWT tokens.", evidence="src/auth.py:1-30")]
        session.register_claims(claims)
        assert len(session.claim_registry) == 1

    def test_registry_capped_at_thirty(self, session):
        claims = [Claim(turn=1, text=f"Claim {i}", evidence="f.py:1-5") for i in range(40)]
        session.register_claims(claims)
        assert len(session.claim_registry) == 30

    def test_claims_digest_empty_when_no_claims(self, session):
        assert session.claims_digest() == ""

    def test_claims_digest_contains_claim_text(self, session):
        session.register_claims([Claim(turn=1, text="Auth uses JWT.", evidence="auth.py:1-10")])
        digest = session.claims_digest()
        assert "Auth uses JWT." in digest
        assert "Turn 1" in digest

    def test_claims_digest_respects_max_claims(self, session):
        claims = [Claim(turn=i, text=f"Claim {i}", evidence="f.py:1-5") for i in range(20)]
        session.register_claims(claims)
        digest = session.claims_digest(max_claims=3)
        # Only last 3 claims should appear
        assert "Claim 17" in digest or "Claim 18" in digest or "Claim 19" in digest
        assert "Claim 0" not in digest


class TestHistoryDigest:
    def test_empty_history_returns_empty(self, session):
        assert session.history_digest() == ""

    def test_digest_contains_user_message(self, session):
        session.add_user_message("How does auth work?")
        digest = session.history_digest()
        assert "How does auth work?" in digest

    def test_long_messages_truncated(self, session):
        long_msg = "x" * 1000
        session.add_user_message(long_msg)
        digest = session.history_digest()
        assert len(digest) < 2000   # truncated


class TestSessionStore:
    def test_get_session_after_create(self):
        store = TFIDFStore()
        create_session("unique-id-xyz", "repo", "/tmp", store)
        s = get_session("unique-id-xyz")
        assert s.repo_name == "repo"

    def test_get_nonexistent_session_raises(self):
        with pytest.raises(KeyError):
            get_session("does-not-exist-99999")

    def test_search_mode_tfidf(self, session):
        assert session.search_mode == "tfidf"

    def test_search_mode_vector(self, sample_chunks):
        from app.services.vector_store import VectorStore
        store = VectorStore()
        import numpy as np
        embs = [np.random.randn(8).tolist() for _ in sample_chunks]
        store.add(sample_chunks, embs)
        s = create_session("vec-session", "repo", "/tmp", store)
        assert s.search_mode == "vector"
