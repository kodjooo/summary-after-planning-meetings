"""Инициализация Celery."""

from __future__ import annotations

from celery import Celery

from app.config import get_settings

settings = get_settings()

celery_app = Celery(
    "meeting_assistant",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.process_meeting_task": {"queue": "meetings"},
        "app.tasks.flush_voice_group_task": {"queue": "meetings"},
    },
)

celery_app.autodiscover_tasks(["app"])
app = celery_app
