"""Тесты разбиения и парсинга анализа."""

from __future__ import annotations

from types import SimpleNamespace

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
