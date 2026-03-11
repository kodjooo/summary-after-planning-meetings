"""Фабрика Redis-клиента."""

from __future__ import annotations

from functools import lru_cache

from redis import Redis

from app.config import get_settings


@lru_cache(maxsize=1)
def get_redis() -> Redis:
    """Возвращает кэшированный Redis-клиент."""
    settings = get_settings()
    return Redis.from_url(settings.redis_url, decode_responses=True)
