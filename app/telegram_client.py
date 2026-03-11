"""Вспомогательные функции работы с Telegram."""

from __future__ import annotations

from pathlib import Path

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.types import BufferedInputFile

from app.config import get_settings


def build_bot() -> Bot:
    """Создаёт экземпляр бота."""
    settings = get_settings()
    return Bot(
        token=settings.telegram_bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN),
    )


async def download_file(bot: Bot, telegram_file_id: str, destination: Path) -> Path:
    """Скачивает файл Telegram в локальное хранилище."""
    telegram_file = await bot.get_file(telegram_file_id)
    await bot.download(telegram_file, destination=destination)
    return destination


async def send_text_file(bot: Bot, chat_id: int, filename: str, content: str) -> None:
    """Отправляет текстовый файл пользователю."""
    payload = BufferedInputFile(content.encode("utf-8"), filename=filename)
    await bot.send_document(chat_id=chat_id, document=payload)
