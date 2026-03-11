"""Работа с аудиофайлами."""

from __future__ import annotations

import subprocess
from pathlib import Path
from math import ceil


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


def get_audio_duration_seconds(file_path: Path) -> float:
    """Возвращает длительность аудиофайла в секундах."""
    command = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(file_path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AudioProcessingError(result.stderr.strip() or "Не удалось определить длительность аудио.")

    try:
        duration = float(result.stdout.strip())
    except ValueError as error:
        raise AudioProcessingError("Не удалось распарсить длительность аудио.") from error

    if duration <= 0:
        raise AudioProcessingError("Длительность аудио должна быть больше нуля.")
    return duration


def split_audio_for_transcription(
    source: Path,
    output_dir: Path,
    max_size_bytes: int,
) -> list[Path]:
    """Нарезает большой аудиофайл на части меньше лимита Whisper."""
    ensure_non_empty_file(source)
    source_size = source.stat().st_size
    if source_size <= max_size_bytes:
        return [source]

    duration = get_audio_duration_seconds(source)
    segments_count = ceil(source_size / max_size_bytes)
    segment_duration = max(1, ceil(duration / segments_count))
    output_dir.mkdir(parents=True, exist_ok=True)
    pattern = output_dir / "transcription-part-%03d.wav"
    command = [
        "ffmpeg",
        "-y",
        "-i",
        str(source),
        "-f",
        "segment",
        "-segment_time",
        str(segment_duration),
        "-c",
        "pcm_s16le",
        str(pattern),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise AudioProcessingError(result.stderr.strip() or "Не удалось нарезать аудио на части.")

    parts = sorted(output_dir.glob("transcription-part-*.wav"))
    if not parts:
        raise AudioProcessingError("После нарезки не найдено ни одной части аудио.")

    for part in parts:
        ensure_non_empty_file(part)
        if part.stat().st_size > max_size_bytes:
            raise AudioProcessingError("После нарезки часть аудио всё ещё превышает лимит Whisper.")
    return parts
