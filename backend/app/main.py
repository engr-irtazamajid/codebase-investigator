import logging

import google.generativeai as genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes import chat, repo
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

limiter = Limiter(key_func=get_remote_address, default_limits=["200/hour"])

app = FastAPI(
    title="Codebase Investigator API",
    description="Clone a GitHub repo, ask questions, get audited answers grounded in source code.",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repo.router)
app.include_router(chat.router)


@app.on_event("startup")
async def _startup() -> None:
    if not settings.gemini_enabled and not settings.openrouter_enabled:
        logger.warning(
            "⚠️  No LLM provider configured. Set GEMINI_API_KEY or OPENROUTER_API_KEY in .env"
        )
    if settings.gemini_enabled:
        genai.configure(api_key=settings.gemini_api_key)
        logger.info("✓ Gemini configured (model: %s)", settings.model_name)
    if settings.openrouter_enabled:
        logger.info("✓ OpenRouter configured (model: %s)", settings.openrouter_model)
    if not settings.gemini_enabled:
        logger.warning("⚠️  GEMINI_API_KEY not set — embeddings unavailable, using TF-IDF search")


@app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
