"""Форматирование ответа пользователю и файлов выгрузки."""

from __future__ import annotations

from io import BytesIO

from openpyxl import Workbook
from openpyxl.styles import Font

from app.models import AnalysisResult


def render_markdown_result(result: AnalysisResult) -> str:
    """Собирает итоговый Markdown-ответ для Telegram."""
    lines = ["*РЕЗЮМЕ ВСТРЕЧИ*", result.summary or "Нет данных", "", "*ЗАДАЧИ*"]

    if result.tasks:
        for task in result.tasks:
            lines.append(
                f"- {task['task']} | ответственный: {task['owner']} | срок: {task['deadline']}"
            )
    else:
        lines.append("- Нет задач")

    return "\n".join(lines).strip()


def render_short_markdown_result(result: AnalysisResult) -> str:
    """Собирает краткую версию ответа для сообщения в Telegram."""
    lines = [
        "*РЕЗЮМЕ ВСТРЕЧИ*",
        result.summary or "Нет данных",
        "",
        "_Таблица с задачами приложена отдельным Excel-файлом._",
    ]
    return "\n".join(lines).strip()


def build_excel_report(result: AnalysisResult) -> bytes:
    """Собирает Excel-файл с задачами встречи."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Задачи"

    headers = ("Задача", "Ответственный", "Срок")
    sheet.append(headers)
    for cell in sheet[1]:
        cell.font = Font(bold=True)

    if result.tasks:
        for task in result.tasks:
            sheet.append((task["task"], task["owner"], task["deadline"]))
    else:
        sheet.append(("Нет задач", "", ""))

    for column in sheet.columns:
        max_length = 0
        column_letter = column[0].column_letter
        for cell in column:
            cell_value = "" if cell.value is None else str(cell.value)
            max_length = max(max_length, len(cell_value))
        sheet.column_dimensions[column_letter].width = min(max(max_length + 2, 14), 60)

    buffer = BytesIO()
    workbook.save(buffer)
    return buffer.getvalue()
