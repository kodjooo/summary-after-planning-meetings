"""Тесты разбиения и парсинга анализа."""

from __future__ import annotations

from types import SimpleNamespace
from pathlib import Path

from app.openai_client import OpenAIService


class DummyOpenAI:
    """Заглушка клиента OpenAI."""

    def __init__(self, *args, **kwargs) -> None:
        self.audio = SimpleNamespace(transcriptions=SimpleNamespace(create=lambda **_: None))
        self.responses = SimpleNamespace(create=lambda **_: None)


def test_parse_analysis_extracts_tasks(monkeypatch):
    monkeypatch.setattr("app.openai_client.OpenAI", DummyOpenAI)
    service = OpenAIService()

    parsed = service._parse_analysis(
        """РЕЗЮМЕ:
Короткое резюме

ОСНОВНЫЕ ТЕМЫ:
- Бюджет

ЗАДАЧИ:
- Подготовить смету | исполнитель: Иван | срок: пятница

ЗАДАЧИ ПО ИСПОЛНИТЕЛЯМ:
Иван:
- Подготовить смету
"""
    )

    assert parsed.summary == "Короткое резюме"
    assert parsed.topics == ["Бюджет"]
    assert parsed.tasks[0]["owner"] == "Иван"
    assert parsed.tasks[0]["deadline"] == "пятница"
    assert parsed.grouped_by_owner["Иван"] == ["Подготовить смету"]


def test_analyze_transcript_uses_chunking_for_long_text(monkeypatch):
    monkeypatch.setattr("app.openai_client.OpenAI", DummyOpenAI)
    service = OpenAIService()
    calls = []

    def fake_run_response(prompt: str) -> str:
        calls.append(prompt)
        if "часть" in prompt:
            return "summary chunk"
        return "РЕЗЮМЕ:\nИтог\n\nОСНОВНЫЕ ТЕМЫ:\n- Тема\n\nЗАДАЧИ:\n- Задача | исполнитель: Иван | срок: завтра\n\nЗАДАЧИ ПО ИСПОЛНИТЕЛЯМ:\nИван:\n- Задача"

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
