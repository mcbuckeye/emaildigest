"""Celery application + beat schedule."""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from src.config import config


def build_celery() -> Celery:
    settings = config()
    app = Celery(
        "emaildigest",
        broker=settings.celery_broker,
        backend=settings.celery_backend,
        include=["src.tasks.pipeline", "src.tasks.scheduler"],
    )
    app.conf.update(
        task_serializer="json",
        accept_content=["json"],
        timezone="UTC",
        enable_utc=True,
        task_always_eager=False,
        broker_connection_retry_on_startup=True,
    )
    app.conf.beat_schedule = {
        "scan-due-digests-every-minute": {
            "task": "src.tasks.scheduler.scan_due_digests",
            "schedule": crontab(minute="*"),
        },
    }
    return app


celery_app = build_celery()
