"""Тесты fallback-загрузки больших файлов."""

from __future__ import annotations

from app.fallback_upload import build_upload_url, consume_upload_token, create_upload_token, get_upload_token_payload


class FakeRedis:
    """Простая заглушка Redis для тестов."""

    def __init__(self) -> None:
        self.storage: dict[str, str] = {}

    def setex(self, key: str, ttl: int, value: str) -> None:
        self.storage[key] = value

    def get(self, key: str) -> str | None:
        return self.storage.get(key)

    def delete(self, key: str) -> None:
        self.storage.pop(key, None)


def test_upload_token_roundtrip(monkeypatch):
    fake_redis = FakeRedis()
    monkeypatch.setattr("app.fallback_upload.get_redis", lambda: fake_redis)

    token = create_upload_token(10, 20, "meeting.wav", 123)

    assert build_upload_url(token).endswith(f"/upload/{token}")
    assert get_upload_token_payload(token)["chat_id"] == 10
    assert consume_upload_token(token)["user_id"] == 20
    assert consume_upload_token(token) is None
