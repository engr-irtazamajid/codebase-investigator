"""In-memory session store: conversation history + claim registry."""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from app.models.schemas import AuditResult, Citation
from app.services.repo_ingestion import CodeChunk
from app.services.tfidf_store import TFIDFStore
from app.services.vector_store import VectorStore

_SESSION_TTL = 4 * 60 * 60  # 4 hours

AnyStore = VectorStore | TFIDFStore


@dataclass
class Claim:
    turn: int
    text: str  # one-sentence factual assertion
    evidence: str  # "file_path:start-end" or empty


@dataclass
class HistoryEntry:
    role: str  # "user" | "assistant"
    content: str
    turn: int
    citations: list[Citation] = field(default_factory=list)
    audit: AuditResult | None = None


@dataclass
class Session:
    id: str
    repo_name: str
    temp_dir: str
    store: AnyStore  # VectorStore (Gemini) or TFIDFStore (fallback)
    history: list[HistoryEntry] = field(default_factory=list)
    claim_registry: list[Claim] = field(default_factory=list)
    last_retrieved_chunks: list[CodeChunk] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)

    @property
    def search_mode(self) -> str:
        return "vector" if isinstance(self.store, VectorStore) else "tfidf"

    @property
    def turn(self) -> int:
        return len([e for e in self.history if e.role == "user"])

    def add_user_message(self, content: str) -> int:
        t = self.turn + 1
        self.history.append(HistoryEntry(role="user", content=content, turn=t))
        return t

    def add_assistant_message(
        self,
        content: str,
        turn: int,
        citations: list[Citation],
        audit: AuditResult | None,
    ) -> None:
        self.history.append(
            HistoryEntry(
                role="assistant", content=content, turn=turn, citations=citations, audit=audit
            )
        )

    def register_claims(self, claims: list[Claim]) -> None:
        self.claim_registry.extend(claims)
        self.claim_registry = self.claim_registry[-30:]

    def claims_digest(self, max_claims: int = 10) -> str:
        recent = self.claim_registry[-max_claims:]
        if not recent:
            return ""
        lines = ["PRIOR CLAIMS FROM THIS CONVERSATION:"]
        for c in recent:
            evidence = f" [{c.evidence}]" if c.evidence else ""
            lines.append(f"  • Turn {c.turn}: {c.text}{evidence}")
        return "\n".join(lines)

    def history_digest(self, max_turns: int = 6) -> str:
        recent = self.history[-(max_turns * 2) :]
        if not recent:
            return ""
        lines = ["CONVERSATION HISTORY (recent turns):"]
        for entry in recent:
            label = "User" if entry.role == "user" else "Assistant"
            body = entry.content if len(entry.content) <= 400 else entry.content[:400] + "…"
            lines.append(f"  Turn {entry.turn} ({label}): {body}")
        return "\n".join(lines)


# ── Singleton store ────────────────────────────────────────────────────────────

_sessions: dict[str, Session] = {}


def create_session(
    session_id: str,
    repo_name: str,
    temp_dir: str,
    store: AnyStore,
) -> Session:
    _prune()
    session = Session(id=session_id, repo_name=repo_name, temp_dir=temp_dir, store=store)
    _sessions[session_id] = session
    return session


def get_session(session_id: str) -> Session:
    session = _sessions.get(session_id)
    if session is None:
        raise KeyError(f"Session not found: {session_id}")
    return session


def _prune() -> None:
    cutoff = time.time() - _SESSION_TTL
    stale = [sid for sid, s in _sessions.items() if s.created_at < cutoff]
    for sid in stale:
        del _sessions[sid]
