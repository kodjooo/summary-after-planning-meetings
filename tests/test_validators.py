"""Тесты валидации входных файлов."""

from __future__ import annotations

from app.models import IncomingFile, SourceType
from app.validators import validate_incoming_file


def test_validate_accepts_supported_audio_file():
    file_data = IncomingFile(
        source_type=SourceType.AUDIO,
        telegram_file_id="1",
        file_name="meeting.mp3",
        mime_type="audio/mpeg",
        size=1024,
    )

    is_valid, error = validate_incoming_file(file_data)

    assert is_valid is True
    assert error is None


def test_validate_accepts_aac_file():
    file_data = IncomingFile(
        source_type=SourceType.AUDIO,
        telegram_file_id="1",
        file_name="meeting.aac",
        mime_type="audio/aac",
        size=1024,
    )

    is_valid, error = validate_incoming_file(file_data)

    assert is_valid is True
    assert error is None


def test_validate_rejects_unsupported_extension():
    file_data = IncomingFile(
        source_type=SourceType.DOCUMENT,
        telegram_file_id="1",
        file_name="meeting.txt",
        mime_type="text/plain",
        size=1024,
    )

    is_valid, error = validate_incoming_file(file_data)

    assert is_valid is False
    assert "Неподдерживаемый формат" in error


def test_validate_rejects_big_file():
    file_data = IncomingFile(
        source_type=SourceType.AUDIO,
        telegram_file_id="1",
        file_name="meeting.wav",
        mime_type="audio/wav",
        size=101 * 1024 * 1024,
    )

    is_valid, error = validate_incoming_file(file_data)

    assert is_valid is False
    assert "Файл слишком большой" in error
    assert "Размер файла: 101.0 MB." in error
