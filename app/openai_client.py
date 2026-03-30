"""Клиент OpenAI для транскрипции и анализа."""

from __future__ import annotations

import json
import math
from pathlib import Path

from openai import OpenAI

from app.audio import split_audio_for_transcription
from app.config import get_settings
from app.models import AnalysisResult
from app.prompts import get_system_prompt, render_user_prompt

DEFAULT_OWNER = "ответственный не указан"
DEFAULT_DEADLINE = "срок не указан"


class OpenAIService:
    """Обертка над OpenAI API."""

    def __init__(self) -> None:
        settings = get_settings()
        self._client = OpenAI(api_key=settings.openai_api_key)
        self._analysis_model = settings.openai_analysis_model
        self._reasoning_effort = settings.openai_reasoning_effort
        self._chunk_size = settings.transcript_chunk_size
        self._transcription_max_size_bytes = settings.openai_transcription_max_file_size_bytes

    def transcribe_audio(self, audio_path: Path) -> str:
        """Транскрибирует аудиофайл через Whisper."""
        parts = split_audio_for_transcription(
            source=audio_path,
            output_dir=audio_path.parent / f"{audio_path.stem}-parts",
            max_size_bytes=self._transcription_max_size_bytes,
        )
        transcripts = [self._transcribe_single_file(part) for part in parts]
        joined = "\n".join(part for part in transcripts if part).strip()
        if not joined:
            raise ValueError("Whisper вернул пустую транскрипцию.")
        return joined

    def _transcribe_single_file(self, audio_path: Path) -> str:
        """Транскрибирует один аудиофайл через Whisper."""
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
        try:
            payload = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise ValueError("Responses API вернул невалидный JSON.") from exc

        summary = str(payload.get("summary", "")).strip()
        raw_tasks = payload.get("tasks", [])
        if not isinstance(raw_tasks, list):
            raw_tasks = []

        tasks: list[dict[str, str]] = []
        for item in raw_tasks:
            if not isinstance(item, dict):
                continue
            task_text = str(item.get("task", "")).strip()
            if not task_text:
                continue
            owner = str(item.get("owner", "")).strip() or DEFAULT_OWNER
            deadline = str(item.get("deadline", "")).strip() or DEFAULT_DEADLINE
            tasks.append(
                {
                    "task": task_text,
                    "owner": owner,
                    "deadline": deadline,
                }
            )

        return AnalysisResult(
            summary=summary,
            tasks=tasks,
            raw_text=raw_text,
        )
