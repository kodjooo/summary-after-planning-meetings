"""Тесты web fallback-загрузки."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.web_app import app


def test_upload_form_returns_404_for_invalid_token(monkeypatch):
    monkeypatch.setattr("app.web_app.get_upload_token_payload", lambda token: None)
    client = TestClient(app)

    response = client.get("/upload/unknown")

    assert response.status_code == 404
    assert "Ссылка недействительна" in response.text


def test_upload_form_returns_html_for_valid_token(monkeypatch):
    monkeypatch.setattr(
        "app.web_app.get_upload_token_payload",
        lambda token: {"file_name": "meeting.wav", "file_size": 1024},
    )
    client = TestClient(app)

    response = client.get("/upload/token123")

    assert response.status_code == 200
    assert "Загрузка большой записи" in response.text
    assert "meeting.wav" in response.text
