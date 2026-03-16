"""Базовые smoke-проверки проекта."""

from __future__ import annotations

from pathlib import Path


def test_docker_compose_contains_required_services():
    content = Path("docker-compose.yml").read_text(encoding="utf-8")

    assert "bot:" in content
    assert "worker:" in content
    assert "redis:" in content
    assert "web:" in content
