from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Gemini (primary) ──────────────────────────────────────────────────────
    gemini_api_key: str = ""
    model_name: str = "gemini-2.0-flash-lite"
    embedding_model: str = "models/gemini-embedding-001"

    # ── OpenRouter (fallback for generation when Gemini is absent or quota-hit)
    openrouter_api_key: str = ""
    openrouter_model: str = "google/gemini-2.0-flash-lite"   # any OpenRouter model slug

    # ── Retrieval & chunking ──────────────────────────────────────────────────
    max_retrieval_chunks: int = 8
    chunk_size: int = 60
    chunk_overlap: int = 15
    max_file_size_kb: int = 500
    max_chunks_per_repo: int = 1500
    embedding_batch_size: int = 5
    cors_origins: list[str] = ["http://localhost:3000"]

    model_config = {
        "env_file": ".env",
        "protected_namespaces": ("settings_",),
    }

    @property
    def gemini_enabled(self) -> bool:
        return bool(self.gemini_api_key)

    @property
    def openrouter_enabled(self) -> bool:
        return bool(self.openrouter_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
