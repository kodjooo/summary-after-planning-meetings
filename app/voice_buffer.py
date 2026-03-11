"""Агрегация нескольких голосовых сообщений."""

from __future__ import annotations

import json
import time

from app.config import get_settings
from app.redis_store import get_redis


def _buffer_key(chat_id: int, user_id: int) -> str:
    return f"voice-buffer:{chat_id}:{user_id}"


def _meta_key(chat_id: int, user_id: int) -> str:
    return f"voice-meta:{chat_id}:{user_id}"


def push_voice_message(payload: dict[str, object]) -> None:
    """Добавляет voice-сообщение в буфер пользователя."""
    chat_id = int(payload["chat_id"])
    user_id = int(payload["user_id"])
    redis = get_redis()
    redis.rpush(_buffer_key(chat_id, user_id), json.dumps(payload, ensure_ascii=False))
    redis.hset(
        _meta_key(chat_id, user_id),
        mapping={
            "updated_at": str(time.time()),
            "chat_id": str(chat_id),
            "user_id": str(user_id),
        },
    )
    redis.expire(_buffer_key(chat_id, user_id), get_settings().voice_group_window_seconds * 6)
    redis.expire(_meta_key(chat_id, user_id), get_settings().voice_group_window_seconds * 6)


def flush_voice_messages(chat_id: int, user_id: int) -> tuple[list[dict[str, object]], float]:
    """Возвращает накопленные voice-сообщения и время последнего обновления."""
    redis = get_redis()
    raw_items = redis.lrange(_buffer_key(chat_id, user_id), 0, -1)
    meta = redis.hgetall(_meta_key(chat_id, user_id))
    redis.delete(_buffer_key(chat_id, user_id))
    redis.delete(_meta_key(chat_id, user_id))
    items = [json.loads(item) for item in raw_items]
    updated_at = float(meta.get("updated_at", "0"))
    return items, updated_at
