"""Загрузка промптов из файлов."""

from __future__ import annotations

from pathlib import Path

PROMPTS_DIR = Path(__file__).with_name("prompts")


def _read_prompt(filename: str) -> str:
    """Читает текст промпта из файла."""
    return (PROMPTS_DIR / filename).read_text(encoding="utf-8").strip()


def get_system_prompt() -> str:
    """Возвращает системный промпт."""
    return _read_prompt("system_prompt.txt")


def render_user_prompt(transcript: str) -> str:
    """Подставляет транскрипцию в пользовательский промпт."""
    template = _read_prompt("user_prompt.txt")
    return template.format(transcript=transcript)
