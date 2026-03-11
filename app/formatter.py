"""Форматирование ответа пользователю."""

from __future__ import annotations

from app.models import AnalysisResult


def render_markdown_result(result: AnalysisResult) -> str:
    """Собирает итоговый Markdown-ответ для Telegram."""
    lines = ["*РЕЗЮМЕ ВСТРЕЧИ*", result.summary or "Нет данных", "", "*ОСНОВНЫЕ ТЕМЫ*"]
    if result.topics:
        lines.extend([f"- {topic}" for topic in result.topics])
    else:
        lines.append("- Нет данных")

    lines.extend(["", "*ЗАДАЧИ*"])
    if result.tasks:
        for task in result.tasks:
            lines.append(f"- {task['task']}")
            lines.append(f"  исполнитель: {task['owner']}")
            lines.append(f"  срок: {task['deadline']}")
    else:
        lines.append("- Нет задач")

    lines.extend(["", "*ЗАДАЧИ ПО ИСПОЛНИТЕЛЯМ*"])
    if result.grouped_by_owner:
        for owner, tasks in result.grouped_by_owner.items():
            lines.append(owner)
            lines.extend([f"- {task}" for task in tasks] or ["- Нет задач"])
            lines.append("")
    else:
        lines.append("исполнитель не назначен")
        lines.append("- Нет задач")

    return "\n".join(lines).strip()
