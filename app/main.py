"""Точка входа для запуска ролей приложения."""

from __future__ import annotations

import asyncio
import sys

from app.bot_app import run_bot


def main() -> None:
    """Запускает выбранную роль приложения."""
    role = sys.argv[1] if len(sys.argv) > 1 else "bot"
    if role == "bot":
        asyncio.run(run_bot())
        return

    raise SystemExit(f"Неизвестная роль приложения: {role}")


if __name__ == "__main__":
    main()
