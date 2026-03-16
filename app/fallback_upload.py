"""Fallback-загрузка больших файлов через web-форму."""

from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.config import get_settings
from app.redis_store import get_redis


def _upload_token_key(token: str) -> str:
    return f"upload-token:{token}"


def create_upload_token(chat_id: int, user_id: int, file_name: str, file_size: int | None) -> str:
    """Создает одноразовый токен для web-загрузки большого файла."""
    token = uuid4().hex
    payload = {
        "chat_id": chat_id,
        "user_id": user_id,
        "file_name": file_name,
        "file_size": file_size or 0,
    }
    settings = get_settings()
    get_redis().setex(
        _upload_token_key(token),
        settings.upload_token_ttl_seconds,
        json.dumps(payload, ensure_ascii=False),
    )
    return token


def get_upload_token_payload(token: str) -> dict[str, object] | None:
    """Возвращает данные токена без удаления."""
    raw = get_redis().get(_upload_token_key(token))
    if raw is None:
        return None
    return json.loads(raw)


def consume_upload_token(token: str) -> dict[str, object] | None:
    """Забирает данные токена и удаляет его."""
    redis = get_redis()
    key = _upload_token_key(token)
    raw = redis.get(key)
    if raw is None:
        return None
    redis.delete(key)
    return json.loads(raw)


def build_upload_url(token: str) -> str:
    """Строит публичную ссылку на fallback-загрузку."""
    base_url = get_settings().web_base_url.rstrip("/")
    return f"{base_url}/upload/{token}"


def build_uploaded_file_path(token: str, file_name: str) -> Path:
    """Возвращает путь временного файла для web-загрузки."""
    base_dir = get_settings().temp_dir / "uploaded-files" / token
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir / Path(file_name).name
