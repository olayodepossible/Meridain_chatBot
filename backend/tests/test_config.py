"""Tests for application settings."""

import os

import pytest

from app.config import Settings, get_settings


def test_settings_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    """Defaults when env does not override (isolate from repo .env)."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    monkeypatch.delenv("MAX_TOOL_STEPS", raising=False)
    monkeypatch.delenv("RATE_LIMIT_REQUESTS", raising=False)
    monkeypatch.delenv("APP_NAME", raising=False)
    get_settings.cache_clear()
    s = Settings(_env_file=None)
    assert s.app_name == "tool-augmented-ai-backend"
    assert s.openai_model == "gpt-4o-mini"
    assert s.max_tool_steps == 6
    assert s.rate_limit_requests == 60


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
    monkeypatch.setenv("OPENAI_MODEL", "gpt-test")
    monkeypatch.setenv("MAX_TOOL_STEPS", "3")
    monkeypatch.setenv("RATE_LIMIT_REQUESTS", "5")
    get_settings.cache_clear()
    s = Settings(_env_file=None)
    assert s.openai_api_key == "sk-test-key"
    assert s.openai_model == "gpt-test"
    assert s.max_tool_steps == 3
    assert s.rate_limit_requests == 5


def test_get_settings_cached(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("APP_NAME", "cached-app")
    get_settings.cache_clear()
    a = get_settings()
    b = get_settings()
    assert a is b
    assert a.app_name == "cached-app"
