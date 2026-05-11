"""
Unified LLM client: Gemini primary → OpenRouter fallback.

Fallback triggers automatically when:
  • Gemini API key is not configured, OR
  • Gemini returns a quota / rate-limit error (429)

OpenRouter uses the OpenAI-compatible chat completions API, so no extra
SDK is needed — httpx (already a dependency) handles it directly.
"""
from __future__ import annotations

import json
import logging
from collections.abc import AsyncGenerator

import google.generativeai as genai
import httpx

from app.core.config import get_settings

logger = logging.getLogger(__name__)

_QUOTA_SIGNALS = ("429", "quota", "rate limit", "resource_exhausted", "resource exhausted", "limit exceeded")
OPENROUTER_BASE = "https://openrouter.ai/api/v1"


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return any(k in msg for k in _QUOTA_SIGNALS)


class LLMClient:
    """
    Single interface for text generation across providers.

    Usage:
        client = LLMClient()
        # Streaming
        async for token in client.stream(prompt):
            ...
        # Single-shot
        text = await client.generate(prompt)
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        if self._settings.gemini_enabled:
            genai.configure(api_key=self._settings.gemini_api_key)

    # ── Public interface ───────────────────────────────────────────────────────

    async def stream(
        self,
        prompt: str,
        temperature: float = 0.3,
    ) -> AsyncGenerator[str, None]:
        """Yield text tokens, falling back to OpenRouter on Gemini quota errors."""
        if self._settings.gemini_enabled:
            try:
                async for token in self._gemini_stream(prompt, temperature):
                    yield token
                return
            except Exception as exc:
                if not _is_quota_error(exc):
                    raise
                if not self._settings.openrouter_enabled:
                    raise RuntimeError(
                        "Gemini quota exceeded and no OPENROUTER_API_KEY configured."
                    ) from exc
                logger.warning("Gemini quota hit — falling back to OpenRouter (%s)", self._settings.openrouter_model)

        if not self._settings.openrouter_enabled:
            raise RuntimeError("No LLM provider configured. Set GEMINI_API_KEY or OPENROUTER_API_KEY.")

        async for token in self._openrouter_stream(prompt, temperature):
            yield token

    async def generate(self, prompt: str, temperature: float = 0.1) -> str:
        """Single-shot generation, falling back to OpenRouter on Gemini quota errors."""
        if self._settings.gemini_enabled:
            try:
                return await self._gemini_generate(prompt, temperature)
            except Exception as exc:
                if not _is_quota_error(exc):
                    raise
                if not self._settings.openrouter_enabled:
                    raise RuntimeError(
                        "Gemini quota exceeded and no OPENROUTER_API_KEY configured."
                    ) from exc
                logger.warning("Gemini quota hit — falling back to OpenRouter (%s)", self._settings.openrouter_model)

        if not self._settings.openrouter_enabled:
            raise RuntimeError("No LLM provider configured. Set GEMINI_API_KEY or OPENROUTER_API_KEY.")

        return await self._openrouter_generate(prompt, temperature)

    @property
    def active_provider(self) -> str:
        """For logging / debug — not authoritative until a call is made."""
        if self._settings.gemini_enabled:
            return f"gemini:{self._settings.model_name}"
        if self._settings.openrouter_enabled:
            return f"openrouter:{self._settings.openrouter_model}"
        return "none"

    # ── Gemini ─────────────────────────────────────────────────────────────────

    async def _gemini_stream(self, prompt: str, temperature: float) -> AsyncGenerator[str, None]:
        model = genai.GenerativeModel(self._settings.model_name)
        gen_cfg = genai.types.GenerationConfig(temperature=temperature, max_output_tokens=2048)
        response = await model.generate_content_async(prompt, generation_config=gen_cfg, stream=True)
        async for chunk in response:
            text = getattr(chunk, "text", None)
            if text:
                yield text

    async def _gemini_generate(self, prompt: str, temperature: float) -> str:
        model = genai.GenerativeModel(self._settings.model_name)
        gen_cfg = genai.types.GenerationConfig(temperature=temperature, max_output_tokens=1024)
        response = await model.generate_content_async(prompt, generation_config=gen_cfg)
        return response.text

    # ── OpenRouter ─────────────────────────────────────────────────────────────

    def _openrouter_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._settings.openrouter_api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:3000",
            "X-Title": "CodeInvestigator",
        }

    async def _openrouter_stream(self, prompt: str, temperature: float) -> AsyncGenerator[str, None]:
        payload = {
            "model": self._settings.openrouter_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": True,
            "temperature": temperature,
            "max_tokens": 2048,
        }
        async with httpx.AsyncClient(timeout=120) as client:
            async with client.stream(
                "POST",
                f"{OPENROUTER_BASE}/chat/completions",
                headers=self._openrouter_headers(),
                json=payload,
            ) as response:
                if response.status_code == 401:
                    raise RuntimeError(
                        "OpenRouter API key is invalid or account not verified. "
                        "Check your email for a verification link at openrouter.ai, "
                        "or use GEMINI_API_KEY instead."
                    )
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    data = line[6:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        chunk = json.loads(data)
                        content = chunk["choices"][0]["delta"].get("content") or ""
                        if content:
                            yield content
                    except (json.JSONDecodeError, KeyError, IndexError):
                        pass

    async def _openrouter_generate(self, prompt: str, temperature: float) -> str:
        payload = {
            "model": self._settings.openrouter_model,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "temperature": temperature,
            "max_tokens": 1024,
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{OPENROUTER_BASE}/chat/completions",
                headers=self._openrouter_headers(),
                json=payload,
            )
            if response.status_code == 401:
                raise RuntimeError(
                    "OpenRouter API key is invalid or account not verified. "
                    "Check your email for a verification link at openrouter.ai, "
                    "or use GEMINI_API_KEY instead."
                )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]


# Singleton — one client per process, reused across requests
_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
