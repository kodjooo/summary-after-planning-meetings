"""Фоновые задачи Celery."""

from __future__ import annotations

import logging
import shutil
import time
from pathlib import Path
from uuid import uuid4

from celery import Task
from aiogram.exceptions import TelegramBadRequest

from app.audio import convert_to_wav, ensure_non_empty_file, merge_audio_files
from app.celery_app import celery_app
from app.config import get_settings
from app.fallback_upload import build_upload_url, create_upload_token
from app.formatter import render_markdown_result
from app.logging_setup import setup_logging
from app.models import JobStatus
from app.openai_client import OpenAIService
from app.telegram_client import build_bot, download_file, is_too_big_telegram_error, send_text_file
from app.validators import format_file_size_mb
from app.voice_buffer import flush_voice_messages

logger = logging.getLogger(__name__)


class BaseTask(Task):
    """Базовая задача с retry-политикой."""

    autoretry_for = (ConnectionError, TimeoutError)
    retry_backoff = True
    retry_jitter = True
    retry_kwargs = {"max_retries": 3}


def _status_text(status: JobStatus) -> str | None:
    mapping = {
        JobStatus.QUEUED: "Файл получен. Начинаю обработку.",
        JobStatus.TRANSCRIBING: "Начинаю транскрипцию.",
        JobStatus.ANALYZING: "Анализирую встречу.",
        JobStatus.DONE: "Готово.",
    }
    return mapping.get(status)


async def _send_status(chat_id: int, text: str) -> None:
    bot = build_bot()
    try:
        await bot.send_message(chat_id=chat_id, text=text)
    finally:
        await bot.session.close()


def _cleanup_directory(path: Path) -> None:
    shutil.rmtree(path, ignore_errors=True)


async def _send_large_file_fallback(chat_id: int, payload: dict[str, object]) -> None:
    source_files: list[dict[str, object]] = payload["files"]  # type: ignore[assignment]
    first_file = source_files[0]
    token = create_upload_token(
        chat_id=chat_id,
        user_id=int(payload["user_id"]),
        file_name=str(first_file.get("file_name", "audio")),
        file_size=int(first_file.get("size", 0) or 0),
    )
    upload_url = build_upload_url(token)
    size_bytes = int(first_file.get("size", 0) or 0)
    size_mb = format_file_size_mb(size_bytes)
    lines = [
        "Telegram не позволяет боту скачать такой большой файл.",
        f"Загрузите запись по резервной ссылке: {upload_url}",
    ]
    if size_mb is not None:
        lines.insert(1, f"Размер файла: {size_mb}.")
    await _send_status(chat_id, "\n".join(lines))


def _move_uploaded_file_to_workdir(file_payload: dict[str, object], destination: Path) -> Path:
    source = Path(str(file_payload["local_file_path"]))
    if not source.exists():
        raise FileNotFoundError(f"Не найден загруженный файл: {source}")
    shutil.move(str(source), str(destination))
    _cleanup_directory(source.parent)
    return destination


@celery_app.task(bind=True, base=BaseTask, name="app.tasks.process_meeting_task")
def process_meeting_task(self: BaseTask, payload: dict[str, object]) -> None:
    """Обрабатывает встречу end-to-end."""
    from asyncio import run

    setup_logging(get_settings().log_level)
    chat_id = int(payload["chat_id"])
    work_dir = get_settings().temp_dir / str(uuid4())
    work_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Старт обработки", extra={"chat_id": chat_id, "status": JobStatus.QUEUED})
    run(_send_status(chat_id, _status_text(JobStatus.QUEUED) or ""))

    try:
        bot = build_bot()
        try:
            run(_process_payload(bot, payload, work_dir))
        finally:
            run(bot.session.close())
        run(_send_status(chat_id, _status_text(JobStatus.DONE) or ""))
        logger.info("Обработка завершена", extra={"chat_id": chat_id, "status": JobStatus.DONE})
    except TelegramBadRequest as exc:
        if is_too_big_telegram_error(exc):
            logger.warning("Telegram не дал скачать большой файл", extra={"chat_id": chat_id})
            run(_send_large_file_fallback(chat_id, payload))
            return
        logger.exception("Ошибка Telegram при обработке встречи: %s", exc)
        run(_send_status(chat_id, "Не удалось обработать файл. Попробуйте снова."))
        raise
    except Exception as exc:
        logger.exception("Ошибка обработки встречи: %s", exc)
        run(_send_status(chat_id, "Не удалось обработать файл. Попробуйте снова."))
        raise
    finally:
        _cleanup_directory(work_dir)


async def _process_payload(bot, payload: dict[str, object], work_dir: Path) -> None:
    logger.info("Скачивание файлов", extra={"status": JobStatus.DOWNLOADING})
    source_files: list[dict[str, object]] = payload["files"]  # type: ignore[assignment]
    audio_paths: list[Path] = []

    for index, file_payload in enumerate(source_files, start=1):
        raw_name = str(file_payload["file_name"])
        destination = work_dir / f"{index}-{raw_name}"
        if file_payload.get("local_file_path"):
            _move_uploaded_file_to_workdir(file_payload, destination)
        else:
            await download_file(bot, str(file_payload["telegram_file_id"]), destination)
        ensure_non_empty_file(destination)
        extension = destination.suffix.lower()
        if extension in {".ogg", ".m4a"}:
            converted = work_dir / f"{destination.stem}.wav"
            audio_paths.append(convert_to_wav(destination, converted))
        else:
            audio_paths.append(destination)

    logger.info("Подготовка аудио", extra={"status": JobStatus.PREPROCESSING})
    for audio_path in audio_paths:
        ensure_non_empty_file(audio_path)

    final_audio = audio_paths[0]
    if len(audio_paths) > 1:
        merged_target = work_dir / "merged.wav"
        wav_sources = []
        for index, item in enumerate(audio_paths, start=1):
            if item.suffix.lower() != ".wav":
                converted = work_dir / f"normalized-{index}.wav"
                wav_sources.append(convert_to_wav(item, converted))
            else:
                wav_sources.append(item)
        final_audio = merge_audio_files(wav_sources, merged_target)

    service = OpenAIService()
    await bot.send_message(chat_id=int(payload["chat_id"]), text=_status_text(JobStatus.TRANSCRIBING))
    started_at = time.perf_counter()
    transcript = service.transcribe_audio(final_audio)
    logger.info(
        "Транскрипция готова",
        extra={
            "status": JobStatus.TRANSCRIBING,
            "duration_seconds": round(time.perf_counter() - started_at, 2),
            "file_size": final_audio.stat().st_size,
        },
    )

    await bot.send_message(chat_id=int(payload["chat_id"]), text=_status_text(JobStatus.ANALYZING))
    started_at = time.perf_counter()
    result = service.analyze_transcript(transcript)
    logger.info(
        "Анализ готов",
        extra={
            "status": JobStatus.ANALYZING,
            "duration_seconds": round(time.perf_counter() - started_at, 2),
        },
    )

    await _send_result(bot, int(payload["chat_id"]), result)


async def _send_result(bot, chat_id: int, result) -> None:
    logger.info("Отправка результата", extra={"status": JobStatus.SENDING, "chat_id": chat_id})
    rendered = render_markdown_result(result)
    if len(rendered) <= 3500:
        await bot.send_message(chat_id=chat_id, text=rendered)
        return

    await bot.send_message(
        chat_id=chat_id,
        text="Результат получился длинным, отправляю краткую сводку и полный текст отдельным файлом.",
    )
    await bot.send_message(chat_id=chat_id, text=f"*РЕЗЮМЕ ВСТРЕЧИ*\n{result.summary}")
    await send_text_file(bot, chat_id, "meeting-summary.txt", result.raw_text)


@celery_app.task(bind=True, base=BaseTask, name="app.tasks.flush_voice_group_task")
def flush_voice_group_task(self: BaseTask, chat_id: int, user_id: int) -> None:
    """Забирает накопленные voice-сообщения и создает общее задание."""
    setup_logging(get_settings().log_level)
    items, updated_at = flush_voice_messages(chat_id, user_id)
    if not items:
        logger.info("Буфер voice пуст", extra={"chat_id": chat_id, "user_id": user_id})
        return

    elapsed = time.time() - updated_at
    window = get_settings().voice_group_window_seconds
    if elapsed < window:
        countdown = max(1, int(window - elapsed))
        self.apply_async(args=[chat_id, user_id], countdown=countdown)
        for item in items:
            from app.voice_buffer import push_voice_message

            push_voice_message(item)
        return

    payload = {
        "chat_id": chat_id,
        "user_id": user_id,
        "source_type": "voice",
        "files": [
            {
                "telegram_file_id": item["telegram_file_id"],
                "file_name": item["file_name"],
                "mime_type": item.get("mime_type"),
                "size": item.get("size"),
            }
            for item in items
        ],
        "created_at": time.time(),
    }
    process_meeting_task.delay(payload)
