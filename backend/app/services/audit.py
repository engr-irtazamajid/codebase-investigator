"""
Independent answer auditor.

DESIGN CONTRACT: receives ONLY (question, answer, raw_chunks) — zero
access to conversation history or prior claims. Fresh-eyes verification.
"""

from __future__ import annotations

import json
import re

from app.core.llm_client import get_llm_client
from app.models.schemas import AuditFlag, AuditResult
from app.services.repo_ingestion import CodeChunk

_AUDIT_PROMPT_TEMPLATE = """\
You are an independent code answer auditor. Your sole job is to verify the \
factual accuracy of an AI-generated answer about a codebase.

WHAT TO ASSESS (nothing else):
  1. Citation validity     — does each [[file:line-line]] ref exist in the retrieved code?
  2. Confidence calibration — is the answer appropriately hedged given the evidence?
  3. Scope creep           — does the answer assert things not supported by retrieved code?
  4. Internal contradiction — does the answer contradict itself?
  5. Missing evidence      — are significant claims made without any citation?

DO NOT assess: writing quality, helpfulness, style, or completeness.

─────────────────────────────────────────────────────
QUESTION:
{question}

─────────────────────────────────────────────────────
AI-GENERATED ANSWER:
{answer}

─────────────────────────────────────────────────────
ACTUAL CODE CHUNKS RETRIEVED (ground truth):
{chunks}

─────────────────────────────────────────────────────
Respond with VALID JSON ONLY — no markdown fences, no commentary:
{{
  "trust_score": <integer 0-10>,
  "verdict": "<reliable|caution|unreliable>",
  "flags": [
    {{
      "type": "<citation_invalid|overconfident|scope_creep|contradiction|missing_evidence>",
      "description": "<specific description of the issue>",
      "severity": "<low|medium|high>"
    }}
  ],
  "summary": "<one concise paragraph summarising your verdict and reasoning>"
}}
"""

_JSON_RE = re.compile(r"\{[\s\S]+\}", re.DOTALL)


def _parse_audit_json(raw: str) -> AuditResult:
    m = _JSON_RE.search(raw)
    if not m:
        raise ValueError("No JSON object found in audit response")

    data = json.loads(m.group())
    flags = [
        AuditFlag(
            type=f.get("type", "unknown"),
            description=f.get("description", ""),
            severity=f.get("severity", "medium"),
        )
        for f in data.get("flags", [])
    ]

    trust_score = max(0, min(10, int(data.get("trust_score", 5))))
    verdict = data.get("verdict", "caution")
    if verdict not in ("reliable", "caution", "unreliable"):
        verdict = "caution"

    return AuditResult(
        trust_score=trust_score,
        verdict=verdict,
        flags=flags,
        summary=data.get("summary", ""),
    )


async def audit_answer(
    question: str,
    answer: str,
    retrieved_chunks: list[CodeChunk],
) -> AuditResult:
    """
    Independent audit via the unified LLM client (Gemini or OpenRouter fallback).
    This call deliberately receives NO conversation history.
    """
    chunks_text = "\n\n".join(c.format_for_prompt() for c in retrieved_chunks)
    prompt = _AUDIT_PROMPT_TEMPLATE.format(
        question=question,
        answer=answer,
        chunks=chunks_text,
    )

    llm = get_llm_client()
    raw = await llm.generate(prompt, temperature=0.1)

    try:
        return _parse_audit_json(raw)
    except (ValueError, KeyError, json.JSONDecodeError):
        return AuditResult(
            trust_score=5,
            verdict="caution",
            flags=[
                AuditFlag(
                    type="missing_evidence",
                    description="Audit parsing failed — review manually.",
                    severity="low",
                )
            ],
            summary="Automated audit could not be fully parsed. Manual review recommended.",
        )
