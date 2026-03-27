"""Тесты аудиообработки."""

from __future__ import annotations

from types import SimpleNamespace

from app.audio import split_audio_for_transcription


def test_split_audio_for_transcription_recursively_splits_oversized_parts(monkeypatch, tmp_path):
    source = tmp_path / "meeting.wav"
    source.write_bytes(b"x" * 25)

    monkeypatch.setattr("app.audio.get_audio_duration_seconds", lambda _: 12.0)

    def fake_run(command, capture_output, text, check):
        pattern = command[-1]
        if str(source) in command:
            first = tmp_path / "parts" / "transcription-part-001.wav"
            second = tmp_path / "parts" / "transcription-part-002.wav"
            first.parent.mkdir(parents=True, exist_ok=True)
            first.write_bytes(b"x" * 11)
            second.write_bytes(b"x" * 9)
        else:
            nested_dir = tmp_path / "parts" / "transcription-part-001-nested-001"
            nested_dir.mkdir(parents=True, exist_ok=True)
            (nested_dir / "transcription-part-001.wav").write_bytes(b"x" * 6)
            (nested_dir / "transcription-part-002.wav").write_bytes(b"x" * 5)
        return SimpleNamespace(returncode=0, stderr="", stdout="")

    monkeypatch.setattr("app.audio.subprocess.run", fake_run)

    parts = split_audio_for_transcription(source, tmp_path / "parts", max_size_bytes=10)

    assert len(parts) == 3
    assert [part.stat().st_size for part in parts] == [6, 5, 9]
