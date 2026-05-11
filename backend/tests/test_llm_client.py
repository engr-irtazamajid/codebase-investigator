"""Tests for LLMClient provider selection and quota-error detection."""

from app.core.llm_client import _is_quota_error


class TestIsQuotaError:
    """The quota detector must catch all Gemini and OpenRouter rate-limit signals."""

    def test_detects_429_string(self):
        assert _is_quota_error(Exception("429 Too Many Requests"))

    def test_detects_quota_keyword(self):
        assert _is_quota_error(Exception("You exceeded your current quota"))

    def test_detects_rate_limit(self):
        assert _is_quota_error(Exception("rate limit exceeded"))

    def test_detects_resource_exhausted(self):
        assert _is_quota_error(Exception("RESOURCE_EXHAUSTED"))

    def test_detects_limit_exceeded(self):
        assert _is_quota_error(Exception("limit exceeded for model"))

    def test_ignores_auth_error(self):
        assert not _is_quota_error(Exception("401 Unauthorized"))

    def test_ignores_not_found(self):
        assert not _is_quota_error(Exception("404 Model not found"))

    def test_ignores_generic_error(self):
        assert not _is_quota_error(Exception("Connection refused"))

    def test_case_insensitive(self):
        assert _is_quota_error(Exception("QUOTA EXCEEDED for this model"))


class TestLLMClientProviderSelection:
    def test_gemini_active_when_key_set(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "test-key")
        monkeypatch.setenv("OPENROUTER_API_KEY", "")
        # Force settings cache to reload
        from app.core import config

        config.get_settings.cache_clear()
        from app.core.llm_client import LLMClient

        client = LLMClient()
        assert "gemini" in client.active_provider

    def test_openrouter_active_when_only_or_key_set(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-v1-test")
        from app.core import config

        config.get_settings.cache_clear()
        from app.core.llm_client import LLMClient

        client = LLMClient()
        assert "openrouter" in client.active_provider

    def test_no_provider_shows_none(self, monkeypatch):
        monkeypatch.setenv("GEMINI_API_KEY", "")
        monkeypatch.setenv("OPENROUTER_API_KEY", "")
        from app.core import config

        config.get_settings.cache_clear()
        from app.core.llm_client import LLMClient

        client = LLMClient()
        assert client.active_provider == "none"
