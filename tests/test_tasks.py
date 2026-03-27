"""Тесты обработки файлов worker."""

from __future__ import annotations

import asyncio
from pathlib import Path

from app.tasks import _process_payload


class _DummyBot:
    async def send_message(self, chat_id: int, text: str) -> None:
        return None


def test_process_payload_converts_aac_before_transcription(monkeypatch, tmp_path):
    source = tmp_path / "meeting.aac"
    source.write_bytes(b"aac")

    converted_files: list[tuple[Path, Path]] = []
    transcribed_paths: list[Path] = []

    def fake_convert_to_wav(source_path: Path, target_path: Path) -> Path:
        converted_files.append((source_path, target_path))
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_bytes(b"wav")
        return target_path

    def fake_ensure_non_empty_file(file_path: Path) -> None:
        assert file_path.exists()
        assert file_path.stat().st_size > 0

    class _FakeService:
        def transcribe_audio(self, audio_path: Path) -> str:
            transcribed_paths.append(audio_path)
            return "transcript"

        def analyze_transcript(self, transcript: str):
            assert transcript == "transcript"
            return {"summary": "ok"}

    async def fake_send_result(bot, chat_id: int, result) -> None:
        assert chat_id == 123
        assert result == {"summary": "ok"}

    monkeypatch.setattr("app.tasks.convert_to_wav", fake_convert_to_wav)
    monkeypatch.setattr("app.tasks.ensure_non_empty_file", fake_ensure_non_empty_file)
    monkeypatch.setattr("app.tasks.OpenAIService", _FakeService)
    monkeypatch.setattr("app.tasks._send_result", fake_send_result)

    payload = {
        "chat_id": 123,
        "user_id": 456,
        "files": [
            {
                "local_file_path": str(source),
                "file_name": source.name,
                "mime_type": "audio/aac",
                "size": source.stat().st_size,
            }
        ],
    }

    asyncio.run(_process_payload(_DummyBot(), payload, tmp_path / "work"))

    assert len(converted_files) == 1
    assert converted_files[0][0].suffix == ".aac"
    assert transcribed_paths == [converted_files[0][1]]
