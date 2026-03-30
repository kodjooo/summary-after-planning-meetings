"""Тесты разбиения и парсинга анализа."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from app.openai_client import DEFAULT_DEADLINE, DEFAULT_OWNER, OpenAIService


class DummyOpenAI:
    """Заглушка клиента OpenAI."""

    def __init__(self, *args, **kwargs) -> None:
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=lambda **_: None))
        self.responses = SimpleNamespace(create=lambda **_: None)


def test_parse_analysis_extracts_tasks(monkeypatch):
    monkeypatch.setattr("app.openai_client.OpenAI", DummyOpenAI)
    service = OpenAIService()

    parsed = service._parse_analysis(
        """
        {
          "summary": "Короткое резюме",
          "tasks": [
            {
              "task": "Подготовить смету",
              "owner": "Иван",
              "deadline": "пятница"
            }
          ]
        }
        """
    )

    assert parsed.summary == "Короткое резюме"
    assert parsed.tasks[0]["owner"] == "Иван"
    assert parsed.tasks[0]["deadline"] == "пятница"


def test_parse_analysis_uses_default_values(monkeypatch):
    monkeypatch.setattr("app.openai_client.OpenAI", DummyOpenAI)
    service = OpenAIService()

    parsed = service._parse_analysis(
        """
        {
          "summary": "Короткое резюме",
          "tasks": [
            {
              "task": "Подготовить смету",
              "owner": "",
              "deadline": ""
            }
          ]
        }
        """
    )

    assert parsed.tasks[0]["owner"] == DEFAULT_OWNER
    assert parsed.tasks[0]["deadline"] == DEFAULT_DEADLINE


def test_parse_analysis_raises_for_invalid_json(monkeypatch):
    monkeypatch.setattr("app.openai_client.OpenAI", DummyOpenAI)
    service = OpenAIService()

    with pytest.raises(ValueError, match="невалидный JSON"):
        service._parse_analysis("РЕЗЮМЕ: текст")


def test_analyze_transcript_uses_chunking_for_long_text(monkeypatch):
    monkeypatch.setattr("app.openai_client.OpenAI", DummyOpenAI)
    service = OpenAIService()
    calls = []

    def fake_run_response(prompt: str) -> str:
        calls.append(prompt)
        if "часть" in prompt:
            return '{"summary":"summary chunk","tasks":[]}'
        return '{"summary":"Итог","tasks":[{"task":"Задача","owner":"Иван","deadline":"завтра"}]}'

    monkeypatch.setattr(service, "_run_response", fake_run_response)

    result = service.analyze_transcript("a" * 250)

    assert result.summary == "Итог"
    assert len(calls) == 4


def test_transcribe_audio_splits_big_file(monkeypatch, tmp_path):
    monkeypatch.setattr("app.openai_client.OpenAI", DummyOpenAI)
    service = OpenAIService()
    audio_path = tmp_path / "meeting.wav"
    audio_path.write_bytes(b"audio")

    monkeypatch.setattr(
        "app.openai_client.split_audio_for_transcription",
        lambda source, output_dir, max_size_bytes: [
            output_dir / "part-001.wav",
            output_dir / "part-002.wav",
        ],
    )
    monkeypatch.setattr(
        service,
        "_transcribe_single_file",
        lambda path: f"text:{Path(path).name}",
    )

    transcript = service.transcribe_audio(audio_path)

    assert transcript == "text:part-001.wav\ntext:part-002.wav"
