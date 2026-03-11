"""Общие настройки тестов."""

from __future__ import annotations

import os

import pytest


@pytest.fixture(autouse=True)
def set_test_env(tmp_path, monkeypatch):
    """Подготавливает окружение для тестов."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "test-token")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("OPENAI_ANALYSIS_MODEL", "gpt-4.1-mini")
    monkeypatch.setenv("OPENAI_REASONING_EFFORT", "medium")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("TEMP_DIR", str(tmp_path))
    monkeypatch.setenv("MAX_FILE_SIZE_MB", "20")
    monkeypatch.setenv("OPENAI_TRANSCRIPTION_MAX_FILE_SIZE_MB", "24")
    monkeypatch.setenv("VOICE_GROUP_WINDOW_SECONDS", "20")
    monkeypatch.setenv("TRANSCRIPT_CHUNK_SIZE", "100")
    monkeypatch.setenv("BOT_STATUS_POLLING_TIMEOUT", "1")
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
