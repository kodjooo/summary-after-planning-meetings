"""Работа с аудиофайлами."""

from __future__ import annotations

import subprocess
from pathlib import Path


class AudioProcessingError(RuntimeError):
    """Ошибка аудиообработки."""


def convert_to_wav(source: Path, target: Path) -> Path:
    """Конвертирует входной файл в wav."""
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AudioProcessingError(result.stderr.strip() or "Не удалось конвертировать аудио.")
    return target


def merge_audio_files(sources: list[Path], target: Path) -> Path:
    """Объединяет несколько wav-файлов в один."""
    if not sources:
        raise AudioProcessingError("Не переданы файлы для объединения.")

    concat_file = target.with_suffix(".txt")
    concat_payload = "".join(f"file '{source}'\n" for source in sources)
    concat_file.write_text(concat_payload, encoding="utf-8")
    command = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(concat_file),
        "-c",
        "copy",
        str(target),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    concat_file.unlink(missing_ok=True)
    if result.returncode != 0:
        raise AudioProcessingError(result.stderr.strip() or "Не удалось объединить аудио.")
    return target


def ensure_non_empty_file(file_path: Path) -> None:
    """Проверяет, что файл существует и не пустой."""
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise AudioProcessingError("Получен пустой или повреждённый файл.")
