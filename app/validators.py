"""Проверки входящих файлов."""

from __future__ import annotations

from pathlib import Path

from app.config import get_settings
from app.models import IncomingFile

SUPPORTED_EXTENSIONS = {".ogg", ".mp3", ".m4a", ".wav"}


def validate_incoming_file(file_data: IncomingFile) -> tuple[bool, str | None]:
    """Проверяет, можно ли ставить файл в обработку."""
    settings = get_settings()
    extension = Path(file_data.file_name).suffix.lower()
    if extension not in SUPPORTED_EXTENSIONS:
        return False, "Неподдерживаемый формат файла. Поддерживаются: ogg, mp3, m4a, wav."

    if file_data.size and file_data.size > settings.max_file_size_bytes:
        return False, (
            f"Файл слишком большой. Максимальный размер: {settings.max_file_size_mb} MB."
        )

    return True, None
