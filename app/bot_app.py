"""Сборка и запуск Telegram-бота."""

from __future__ import annotations

import logging
import time

from aiogram import Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.celery_app import celery_app
from app.config import get_settings
from app.logging_setup import setup_logging
from app.models import IncomingFile, SourceType
from app.telegram_client import build_bot
from app.validators import validate_incoming_file
from app.voice_buffer import push_voice_message

logger = logging.getLogger(__name__)
router = Router()


@router.message(Command("start"))
async def start_handler(message: Message) -> None:
    """Приветственное сообщение."""
    await message.answer(
        "Отправьте голосовое сообщение или аудиофайл, и я подготовлю структурированный протокол встречи."
    )


@router.message(Command("help"))
async def help_handler(message: Message) -> None:
    """Справка по использованию."""
    await message.answer(
        "Поддерживаются voice, audio и document в форматах ogg, mp3, m4a, wav."
    )


@router.message(F.voice)
async def voice_handler(message: Message) -> None:
    """Принимает голосовые сообщения и буферизует их."""
    voice = message.voice
    if not voice or not message.from_user:
        return

    file_data = IncomingFile(
        source_type=SourceType.VOICE,
        telegram_file_id=voice.file_id,
        file_name=f"{voice.file_unique_id}.ogg",
        mime_type="audio/ogg",
        size=voice.file_size,
    )
    is_valid, error = validate_incoming_file(file_data)
    if not is_valid:
        await message.answer(error)
        return

    payload = {
        "chat_id": message.chat.id,
        "user_id": message.from_user.id,
        "telegram_file_id": voice.file_id,
        "file_name": file_data.file_name,
        "mime_type": file_data.mime_type,
        "size": file_data.size,
    }
    push_voice_message(payload)
    celery_app.send_task(
        "app.tasks.flush_voice_group_task",
        args=[message.chat.id, message.from_user.id],
        countdown=get_settings().voice_group_window_seconds,
    )
    await message.answer("Голосовое сообщение получено. Жду возможные продолжения перед запуском обработки.")


@router.message(F.audio | F.document)
async def file_handler(message: Message) -> None:
    """Принимает аудиофайлы и документы."""
    if not message.from_user:
        return

    item = message.audio or message.document
    if item is None:
        return

    source_type = SourceType.AUDIO if message.audio else SourceType.DOCUMENT
    file_name = item.file_name or f"{item.file_id}.bin"
    file_data = IncomingFile(
        source_type=source_type,
        telegram_file_id=item.file_id,
        file_name=file_name,
        mime_type=getattr(item, "mime_type", None),
        size=item.file_size,
    )
    is_valid, error = validate_incoming_file(file_data)
    if not is_valid:
        await message.answer(error)
        return

    payload = {
        "chat_id": message.chat.id,
        "user_id": message.from_user.id,
        "source_type": source_type.value,
        "files": [
            {
                "telegram_file_id": file_data.telegram_file_id,
                "file_name": file_data.file_name,
                "mime_type": file_data.mime_type,
                "size": file_data.size,
            }
        ],
        "created_at": time.time(),
    }
    celery_app.send_task("app.tasks.process_meeting_task", args=[payload])
    await message.answer("Файл получен. Начинаю обработку.")


async def run_bot() -> None:
    """Запускает long polling бота."""
    settings = get_settings()
    setup_logging(settings.log_level)
    dispatcher = Dispatcher()
    dispatcher.include_router(router)
    bot = build_bot()
    logger.info("Запуск Telegram-бота")
    await dispatcher.start_polling(bot, polling_timeout=settings.bot_status_polling_timeout)
