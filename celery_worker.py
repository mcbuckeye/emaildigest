"""Celery worker & beat entrypoint.

Run with::

    celery -A celery_worker worker --loglevel=info
    celery -A celery_worker beat --loglevel=info
"""

from src.tasks.celery_app import celery_app  # noqa: F401  (re-exported)
from src.tasks import pipeline, scheduler  # noqa: F401  (register tasks)
