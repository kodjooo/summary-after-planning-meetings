"""Конфигурация приложения."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки из переменных окружения."""

    telegram_bot_token: str = Field(alias="TELEGRAM_BOT_TOKEN")
    openai_api_key: str = Field(alias="OPENAI_API_KEY")
    openai_analysis_model: str = Field(
        default="gpt-4.1-mini",
        alias="OPENAI_ANALYSIS_MODEL",
    )
    openai_reasoning_effort: str = Field(
        default="medium",
        alias="OPENAI_REASONING_EFFORT",
    )
    redis_url: str = Field(alias="REDIS_URL")
    temp_dir: Path = Field(default=Path("/tmp/meeting-assistant"), alias="TEMP_DIR")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    max_file_size_mb: int = Field(default=100, alias="MAX_FILE_SIZE_MB")
    openai_transcription_max_file_size_mb: int = Field(
        default=24,
        alias="OPENAI_TRANSCRIPTION_MAX_FILE_SIZE_MB",
    )
    voice_group_window_seconds: int = Field(
        default=20,
        alias="VOICE_GROUP_WINDOW_SECONDS",
    )
    transcript_chunk_size: int = Field(default=40000, alias="TRANSCRIPT_CHUNK_SIZE")
    bot_status_polling_timeout: int = Field(
        default=30,
        alias="BOT_STATUS_POLLING_TIMEOUT",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def max_file_size_bytes(self) -> int:
        """Ограничение на размер файла в байтах."""
        return self.max_file_size_mb * 1024 * 1024

    @property
    def openai_transcription_max_file_size_bytes(self) -> int:
        """Безопасный лимит размера файла для Whisper в байтах."""
        return self.openai_transcription_max_file_size_mb * 1024 * 1024


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Возвращает кэшированные настройки."""
    settings = Settings()
    settings.temp_dir.mkdir(parents=True, exist_ok=True)
    return settings
