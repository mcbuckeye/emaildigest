"""Celery tasks."""

from src.tasks.digest import generate_digest_task

__all__ = ["generate_digest_task"]
