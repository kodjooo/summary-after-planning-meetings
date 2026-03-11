"""Внутренние модели приложения."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class SourceType(StrEnum):
    """Поддерживаемые типы входных сообщений."""

    VOICE = "voice"
    AUDIO = "audio"
    DOCUMENT = "document"


class JobStatus(StrEnum):
    """Этапы обработки задания."""

    QUEUED = "queued"
    DOWNLOADING = "downloading"
    PREPROCESSING = "preprocessing"
    TRANSCRIBING = "transcribing"
    ANALYZING = "analyzing"
    SENDING = "sending"
    DONE = "done"
    FAILED = "failed"


@dataclass(slots=True)
class IncomingFile:
    """Описание входящего файла из Telegram."""

    source_type: SourceType
    telegram_file_id: str
    file_name: str
    mime_type: str | None
    size: int | None


@dataclass(slots=True)
class AnalysisResult:
    """Структурированный результат анализа."""

    summary: str
    topics: list[str]
    tasks: list[dict[str, str]]
    grouped_by_owner: dict[str, list[str]]
    raw_text: str
