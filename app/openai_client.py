"""Клиент OpenAI для транскрипции и анализа."""

from __future__ import annotations

import math
from pathlib import Path

from openai import OpenAI

from app.config import get_settings
from app.models import AnalysisResult
from app.prompts import get_system_prompt, render_user_prompt


class OpenAIService:
    """Обертка над OpenAI API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._analysis_model = settings.openai_analysis_model
        self._reasoning_effort = settings.openai_reasoning_effort
        self._chunk_size = settings.transcript_chunk_size

    def transcribe_audio(self, audio_path: Path) -> str:
        """Транскрибирует аудиофайл через Whisper."""
        with audio_path.open("rb") as file_handle:
            response = self._client.audio.transcriptions.create(
                model="whisper-1",
                file=file_handle,
                language="ru",
            )
        text = getattr(response, "text", "").strip()
        if not text:
            raise ValueError("Whisper вернул пустую транскрипцию.")
        return text

    def analyze_transcript(self, transcript: str) -> AnalysisResult:
        """Анализирует транскрипцию встречи."""
        normalized = transcript.strip()
        if not normalized:
            raise ValueError("Нельзя анализировать пустую транскрипцию.")

        if len(normalized) <= self._chunk_size:
            raw_text = self._analyze_text(normalized)
        else:
            partial_summaries = [
                self._summarize_chunk(chunk, index, total)
                for index, (chunk, total) in enumerate(self._chunk_transcript(normalized), start=1)
            ]
            joined = "\n\n".join(partial_summaries)
            raw_text = self._analyze_text(
                "Ниже приведены промежуточные сводки по длинной встрече.\n\n" + joined
            )
        return self._parse_analysis(raw_text)

    def _chunk_transcript(self, transcript: str) -> list[tuple[str, int]]:
        chunks = [
            transcript[index : index + self._chunk_size]
            for index in range(0, len(transcript), self._chunk_size)
        ]
        total = math.ceil(len(transcript) / self._chunk_size)
        return [(chunk, total) for chunk in chunks]

    def _summarize_chunk(self, chunk: str, index: int, total: int) -> str:
        prompt = (
            f"Это часть {index} из {total} длинной транскрипции встречи.\n"
            "Сделай краткую factual-сводку без выдумывания деталей.\n\n"
            f"{chunk}"
        )
        return self._run_response(prompt)

    def _analyze_text(self, transcript: str) -> str:
        prompt = render_user_prompt(transcript)
        return self._run_response(prompt)

    def _run_response(self, user_prompt: str) -> str:
        response = self._client.responses.create(
            model=self._analysis_model,
            instructions=get_system_prompt(),
            input=user_prompt,
            reasoning={"effort": self._reasoning_effort},
        )
        text = getattr(response, "output_text", "").strip()
        if not text:
            raise ValueError("Responses API вернул пустой результат.")
        return text

    def _parse_analysis(self, raw_text: str) -> AnalysisResult:
        sections: dict[str, list[str]] = {}
        current = "OTHER"
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            upper = stripped.upper().rstrip(":")
            if upper in {"РЕЗЮМЕ", "ОСНОВНЫЕ ТЕМЫ", "ЗАДАЧИ", "ЗАДАЧИ ПО ИСПОЛНИТЕЛЯМ"}:
                current = upper
                sections[current] = []
                continue
            sections.setdefault(current, []).append(stripped)

        tasks = []
        for line in sections.get("ЗАДАЧИ", []):
            cleaned = line.removeprefix("- ").strip()
            parts = [part.strip() for part in cleaned.split("|")]
            task = {
                "task": parts[0] if parts else cleaned,
                "owner": "исполнитель не назначен",
                "deadline": "срок не определен",
            }
            for part in parts[1:]:
                lowered = part.lower()
                if lowered.startswith("исполнитель:"):
                    task["owner"] = part.split(":", 1)[1].strip() or task["owner"]
                if lowered.startswith("срок:"):
                    task["deadline"] = part.split(":", 1)[1].strip() or task["deadline"]
            tasks.append(task)

        grouped_by_owner: dict[str, list[str]] = {}
        current_owner = ""
        for line in sections.get("ЗАДАЧИ ПО ИСПОЛНИТЕЛЯМ", []):
            if line.endswith(":"):
                current_owner = line[:-1].strip()
                grouped_by_owner.setdefault(current_owner, [])
                continue
            if line.startswith("- ") and current_owner:
                grouped_by_owner[current_owner].append(line.removeprefix("- ").strip())

        return AnalysisResult(
            summary="\n".join(sections.get("РЕЗЮМЕ", [])).strip(),
            topics=[line.removeprefix("- ").strip() for line in sections.get("ОСНОВНЫЕ ТЕМЫ", [])],
            tasks=tasks,
            grouped_by_owner=grouped_by_owner,
            raw_text=raw_text,
        )
