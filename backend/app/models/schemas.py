from __future__ import annotations

from pydantic import BaseModel


class IngestRequest(BaseModel):
    github_url: str


class IngestResponse(BaseModel):
    session_id: str
    repo_name: str
    files_indexed: int
    chunks_indexed: int


class Citation(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    content: str
    relevance_score: float


class AuditFlag(BaseModel):
    type: str  # citation_invalid | overconfident | scope_creep | contradiction | missing_evidence
    description: str
    severity: str  # low | medium | high


class AuditResult(BaseModel):
    trust_score: int  # 0–10
    verdict: str  # reliable | caution | unreliable
    flags: list[AuditFlag]
    summary: str


class ChatRequest(BaseModel):
    session_id: str
    question: str


class ConversationMessage(BaseModel):
    role: str  # user | assistant
    content: str
    turn: int
    citations: list[Citation] | None = None
    audit: AuditResult | None = None


class FileContentResponse(BaseModel):
    content: str
    language: str
    total_lines: int
