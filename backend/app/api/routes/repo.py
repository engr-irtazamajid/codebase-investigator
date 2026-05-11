import asyncio
import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.config import get_settings
from app.models.schemas import FileContentResponse, IngestRequest, IngestResponse
from app.services import conversation as conv_svc
from app.services import embedding as emb_svc
from app.services.repo_ingestion import SUPPORTED_EXTENSIONS, ingest_repo
from app.services.tfidf_store import TFIDFStore
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)
limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/repo", tags=["repo"])


@router.post("/ingest", response_model=IngestResponse)
@limiter.limit("5/minute;20/hour")  # git clone + embed is expensive
async def ingest(request: Request, body: IngestRequest) -> IngestResponse:
    """Clone repo, chunk files, build search index, create session."""
    settings = get_settings()

    try:
        repo = await asyncio.get_event_loop().run_in_executor(None, ingest_repo, body.github_url)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e

    if not repo.chunks:
        raise HTTPException(
            status_code=422,
            detail="No indexable source files found in this repository.",
        )

    # ── Choose search backend based on available credentials ──────────────────
    if settings.gemini_enabled:
        # Gemini available → high-quality vector (embedding) search
        logger.info("Using vector search (Gemini embeddings) for session %s", repo.session_id)
        try:
            texts = [c.content for c in repo.chunks]
            embeddings = await emb_svc.embed_documents(texts)
            store: VectorStore | TFIDFStore = VectorStore()
            store.add(repo.chunks, embeddings)
        except Exception as e:
            logger.warning("Embedding failed (%s) — falling back to TF-IDF", e)
            store = TFIDFStore()
            store.add(repo.chunks)
    else:
        # No Gemini key → keyword (TF-IDF) search; generation via OpenRouter
        logger.info(
            "No GEMINI_API_KEY — using TF-IDF keyword search for session %s", repo.session_id
        )
        if not settings.openrouter_enabled:
            raise HTTPException(
                status_code=503,
                detail=(
                    "No LLM provider configured. "
                    "Set GEMINI_API_KEY and/or OPENROUTER_API_KEY in backend/.env"
                ),
            )
        store = TFIDFStore()
        store.add(repo.chunks)

    conv_svc.create_session(
        session_id=repo.session_id,
        repo_name=repo.repo_name,
        temp_dir=repo.temp_dir,
        store=store,
    )

    search_mode = "vector" if isinstance(store, VectorStore) else "tfidf"
    logger.info(
        "Session %s ready — %d files, %d chunks, search=%s",
        repo.session_id,
        repo.files_indexed,
        len(repo.chunks),
        search_mode,
    )

    return IngestResponse(
        session_id=repo.session_id,
        repo_name=repo.repo_name,
        files_indexed=repo.files_indexed,
        chunks_indexed=len(repo.chunks),
    )


@router.get("/file", response_model=FileContentResponse)
@limiter.limit("60/minute")
async def get_file(
    request: Request,
    session_id: str = Query(...),
    file_path: str = Query(...),
) -> FileContentResponse:
    """Return raw file content for the citation viewer."""
    try:
        session = conv_svc.get_session(session_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail="Session not found.") from e

    abs_path = Path(session.temp_dir) / file_path
    if not abs_path.exists() or not abs_path.is_file():
        raise HTTPException(status_code=404, detail="File not found in repository.")

    try:
        abs_path.relative_to(session.temp_dir)
    except ValueError as e:
        raise HTTPException(status_code=403, detail="Access denied.") from e

    content = abs_path.read_text(encoding="utf-8", errors="replace")
    language = SUPPORTED_EXTENSIONS.get(abs_path.suffix, "text")

    return FileContentResponse(
        content=content,
        language=language,
        total_lines=len(content.splitlines()),
    )
