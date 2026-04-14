"""Celery worker configuration."""

import asyncio
from celery import Celery

from src.config import config


# Celery app configuration
celery_app = Celery(
    "emaildigest",
    broker=config().redis_url,
    backend=config().redis_url,
    include=["src.tasks.digest"],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_routes={
        "src.tasks.digest.*": {"queue": "digests"},
    },
)

if __name__ == "__main__":
    celery_app.start()
