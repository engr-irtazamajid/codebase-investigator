import json

from fastapi import APIRouter, HTTPException, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from sse_starlette.sse import EventSourceResponse

from app.models.schemas import ChatRequest
from app.services import audit as audit_svc
from app.services import conversation as conv_svc
from app.services.answer import stream_answer

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/ask")
@limiter.limit("30/minute")   # one question every 2s sustained; bursty is fine
async def ask(request: Request, body: ChatRequest) -> EventSourceResponse:
    """
    Stream answer tokens, then emit citations and an independent audit.

    SSE event types:
      {"type": "token",     "content": "..."}
      {"type": "citations", "data": [...]}
      {"type": "audit",     "data": {...}}
      {"type": "error",     "message": "..."}
    Stream always terminates with the literal string [DONE].
    """
    try:
        session = conv_svc.get_session(body.session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Session not found. Ingest a repo first.") from e

    async def event_generator():
        collected_answer: list[str] = []

        try:
            async for event in stream_answer(session, body.question):
                if event["type"] == "token":
                    collected_answer.append(event["content"])
                yield {"data": json.dumps(event)}

        except Exception as exc:
            yield {"data": json.dumps({"type": "error", "message": str(exc)})}
            yield {"data": "[DONE]"}
            return

        try:
            audit_result = await audit_svc.audit_answer(
                question=body.question,
                answer="".join(collected_answer),
                # Reuse chunks already retrieved during answer generation — no second embed call
                retrieved_chunks=session.last_retrieved_chunks,
            )

            if session.history and session.history[-1].role == "assistant":
                session.history[-1].audit = audit_result

            yield {"data": json.dumps({"type": "audit", "data": audit_result.model_dump()})}

        except Exception as exc:
            yield {"data": json.dumps({
                "type": "audit",
                "data": {
                    "trust_score": 5,
                    "verdict": "caution",
                    "flags": [{"type": "missing_evidence", "description": str(exc), "severity": "low"}],
                    "summary": "Audit service encountered an error.",
                },
            })}

        yield {"data": "[DONE]"}

    return EventSourceResponse(event_generator())
