"""Проверки входящих файлов."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.models import IncomingFile

SUPPORTED_EXTENSIONS = {".ogg", ".mp3", ".m4a", ".wav", ".aac"}


def format_file_size_mb(size_bytes: int | None) -> str | None:
    """Возвращает размер файла в MB для сообщений пользователю."""
    if not size_bytes:
        return None
    return f"{round(size_bytes / (1024 * 1024), 2)} MB"


def validate_incoming_file(file_data: IncomingFile) -> tuple[bool, str | None]:
    """Проверяет, можно ли ставить файл в обработку."""
    settings = get_settings()
    extension = Path(file_data.file_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        return False, "Неподдерживаемый формат файла. Поддерживаются: ogg, mp3, m4a, wav, aac."

    if file_data.size and file_data.size > settings.max_file_size_bytes:
        actual_size = format_file_size_mb(file_data.size)
        return False, (
            "Файл слишком большой. "
            f"Размер файла: {actual_size}. "
            f"Максимальный размер: {settings.max_file_size_mb} MB."
        )

    return True, None
