"""Тесты форматирования ответа."""

from __future__ import annotations

from io import BytesIO

from openpyxl import load_workbook

from app.formatter import build_excel_report, render_markdown_result, render_short_markdown_result
from app.models import AnalysisResult


def test_render_markdown_result_contains_summary_and_tasks():
    result = AnalysisResult(
        summary="Обсудили запуск проекта.",
        tasks=[
            {
                "task": "Подготовить docker-compose",
                "owner": "Иван",
                "deadline": "пятница",
            }
        ],
        raw_text="raw",
    )

    rendered = render_markdown_result(result)

    assert "*РЕЗЮМЕ ВСТРЕЧИ*" in rendered
    assert "*ЗАДАЧИ*" in rendered
    assert "Подготовить docker-compose | ответственный: Иван | срок: пятница" in rendered


def test_render_short_markdown_result_mentions_excel_attachment():
    result = AnalysisResult(
        summary="Обсудили запуск проекта.",
        tasks=[],
        raw_text="raw",
    )

    rendered = render_short_markdown_result(result)

    assert "*РЕЗЮМЕ ВСТРЕЧИ*" in rendered
    assert "Excel-файлом" in rendered


def test_build_excel_report_contains_expected_columns():
    result = AnalysisResult(
        summary="Обсудили запуск проекта.",
        tasks=[
            {
                "task": "Подготовить docker-compose",
                "owner": "Иван",
                "deadline": "пятница",
            }
        ],
        raw_text="raw",
    )

    payload = build_excel_report(result)
    workbook = load_workbook(filename=BytesIO(payload))
    sheet = workbook.active

    assert sheet.title == "Задачи"
    assert sheet["A1"].value == "Задача"
    assert sheet["B1"].value == "Ответственный"
    assert sheet["C1"].value == "Срок"
    assert sheet["A2"].value == "Подготовить docker-compose"
    assert sheet["B2"].value == "Иван"
    assert sheet["C2"].value == "пятница"
