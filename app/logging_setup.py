"""Настройка логирования."""

from __future__ import annotations

import logging


def setup_logging(level: str) -> None:
    """Настраивает единый формат логов."""
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
