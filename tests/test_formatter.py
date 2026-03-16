"""Тесты форматирования ответа."""

from __future__ import annotations

from app.formatter import render_markdown_result, render_short_markdown_result
from app.models import AnalysisResult


def test_render_markdown_result_contains_all_sections():
    result = AnalysisResult(
        summary="Обсудили запуск проекта.",
        topics=["Инфраструктура", "Сроки"],
        tasks=[
            {
                "task": "Подготовить docker-compose",
                "owner": "Иван",
                "deadline": "пятница",
            }
        ],
        grouped_by_owner={"Иван": ["Подготовить docker-compose"]},
        raw_text="raw",
    )

    rendered = render_markdown_result(result)

    assert "*РЕЗЮМЕ ВСТРЕЧИ*" in rendered
    assert "*ОСНОВНЫЕ ТЕМЫ*" in rendered
    assert "*ЗАДАЧИ*" in rendered
    assert "*ЗАДАЧИ ПО ИСПОЛНИТЕЛЯМ*" in rendered
    assert "Подготовить docker-compose" in rendered
    assert "Иван" in rendered


def test_render_short_markdown_result_mentions_txt_attachment():
    result = AnalysisResult(
        summary="Обсудили запуск проекта.",
        topics=["Инфраструктура", "Сроки"],
        tasks=[
            {
                "task": "Подготовить docker-compose",
                "owner": "Иван",
                "deadline": "пятница",
            }
        ],
        grouped_by_owner={"Иван": ["Подготовить docker-compose"]},
        raw_text="raw",
    )

    rendered = render_short_markdown_result(result)

    assert "*РЕЗЮМЕ ВСТРЕЧИ*" in rendered
    assert "*КЛЮЧЕВЫЕ ЗАДАЧИ*" in rendered
    assert "Полный результат приложен отдельным txt-файлом." in rendered
