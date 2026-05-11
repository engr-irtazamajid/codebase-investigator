"""Answer generation: retrieve → prompt → stream → parse citations & claims."""

from __future__ import annotations

import re
from collections.abc import AsyncGenerator

from app.core.config import get_settings
from app.core.llm_client import get_llm_client
from app.models.schemas import Citation
from app.services.conversation import Claim, Session
from app.services.embedding import embed_query
from app.services.vector_store import VectorStore

_CITATION_RE = re.compile(r"\[\[([^:\]]+):(\d+)-(\d+)\]\]")

_SYSTEM_PROMPT = """\
You are an expert code investigator. You analyse public GitHub repositories and answer \
questions with precise, evidence-based responses grounded in specific files and lines.

RULES:
1. Every non-trivial claim MUST be cited using [[file_path:start_line-end_line]].
   Example: "The handler is async [[src/api/handler.py:23-45]]"
2. If you are uncertain, say so explicitly — never fabricate behaviour.
3. If a prior claim (listed below) turns out to be wrong, explicitly acknowledge and correct it.
4. Do NOT repeat information already covered in earlier turns unless correcting it.
5. Be direct. Skip boilerplate. Go straight to what matters.\
"""


def _build_prompt(
    question: str,
    repo_name: str,
    retrieved_chunks: list,
    history_digest: str,
    claims_digest: str,
) -> str:
    code_context = "\n\n".join(c.format_for_prompt() for c in retrieved_chunks)
    sections = [
        _SYSTEM_PROMPT,
        f"REPOSITORY: {repo_name}",
        "─" * 60,
        "RETRIEVED CODE:",
        code_context,
        "─" * 60,
    ]
    if claims_digest:
        sections += [claims_digest, "─" * 60]
    if history_digest:
        sections += [history_digest, "─" * 60]
    sections.append(f"QUESTION: {question}")
    return "\n\n".join(sections)


def _parse_citations(
    answer: str, retrieved_chunks: list, scores: dict[str, float]
) -> list[Citation]:
    chunk_map = {(c.file_path, c.start_line): c for c in retrieved_chunks}
    seen: set[str] = set()
    citations: list[Citation] = []

    for m in _CITATION_RE.finditer(answer):
        file_path, start_line, end_line = m.group(1), int(m.group(2)), int(m.group(3))
        key = f"{file_path}:{start_line}-{end_line}"
        if key in seen:
            continue
        seen.add(key)
        matched = chunk_map.get((file_path, start_line))
        citations.append(
            Citation(
                file_path=file_path,
                start_line=start_line,
                end_line=end_line,
                content=matched.content if matched else "(cited but not in retrieved context)",
                relevance_score=scores.get(file_path, 0.0),
            )
        )

    return citations


def _extract_claims(answer: str, turn: int) -> list[Claim]:
    claims: list[Claim] = []
    for sentence in re.split(r"(?<=[.!?])\s+", answer):
        refs = _CITATION_RE.findall(sentence)
        if refs:
            clean = _CITATION_RE.sub("", sentence).strip()
            if len(clean) > 20:
                claims.append(
                    Claim(
                        turn=turn,
                        text=clean[:200],
                        evidence=f"{refs[0][0]}:{refs[0][1]}-{refs[0][2]}",
                    )
                )
    return claims[:10]


async def stream_answer(session: Session, question: str) -> AsyncGenerator[dict, None]:
    """
    Yields SSE-ready dicts:
      {"type": "token",     "content": "..."}
      {"type": "citations", "data": [...]}
    Also updates session.last_retrieved_chunks for use by the audit step.
    """
    settings = get_settings()

    if isinstance(session.store, VectorStore):
        q_emb = await embed_query(question)
        results = session.store.search(q_emb, top_k=settings.max_retrieval_chunks)
    else:
        results = session.store.search(question, top_k=settings.max_retrieval_chunks)

    retrieved_chunks = [r.chunk for r in results]
    score_map = {r.chunk.file_path: r.score for r in results}
    session.last_retrieved_chunks = retrieved_chunks

    turn = session.add_user_message(question)
    prompt = _build_prompt(
        question=question,
        repo_name=session.repo_name,
        retrieved_chunks=retrieved_chunks,
        history_digest=session.history_digest(),
        claims_digest=session.claims_digest(),
    )

    llm = get_llm_client()
    collected: list[str] = []

    async for token in llm.stream(prompt, temperature=0.3):
        collected.append(token)
        yield {"type": "token", "content": token}

    full_answer = "".join(collected)
    citations = _parse_citations(full_answer, retrieved_chunks, score_map)
    yield {"type": "citations", "data": [c.model_dump() for c in citations]}

    session.register_claims(_extract_claims(full_answer, turn))
    session.add_assistant_message(content=full_answer, turn=turn, citations=citations, audit=None)
