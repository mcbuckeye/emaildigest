"""Scheduler: find digests whose cron is due and enqueue them."""

from __future__ import annotations

import asyncio
import logging
from datetime import UTC, datetime

from croniter import croniter
from sqlalchemy import select

from src.database import db_session
from src.models import Digest, DigestStatus
from src.tasks.celery_app import celery_app
from src.tasks.pipeline import generate_digest_task

logger = logging.getLogger(__name__)


def compute_next_run_at(cron_expr: str, *, now: datetime | None = None) -> datetime:
    """Return the next datetime the cron expression will fire (UTC)."""
    reference = now or datetime.now(UTC)
    if reference.tzinfo is None:
        reference = reference.replace(tzinfo=UTC)
    if not croniter.is_valid(cron_expr):
        raise ValueError(f"invalid cron expression: {cron_expr}")
    it = croniter(cron_expr, reference)
    return it.get_next(datetime)


async def scan_due_digests_async() -> int:
    """Find digests whose next_run_at is <= now, enqueue them, and advance next_run_at.

    Returns the number of digests enqueued.
    """
    now = datetime.utcnow()
    enqueued = 0
    async with db_session() as session:
        stmt = select(Digest).where(Digest.status == DigestStatus.ACTIVE.value)
        rows = (await session.execute(stmt)).scalars().all()
        for digest in rows:
            if digest.next_run_at is None:
                try:
                    digest.next_run_at = compute_next_run_at(digest.frequency_cron).replace(tzinfo=None)
                except ValueError:
                    logger.warning("Digest %s has invalid cron '%s'", digest.id, digest.frequency_cron)
                continue
            if digest.next_run_at <= now:
                generate_digest_task.delay(digest.id)
                enqueued += 1
                try:
                    digest.next_run_at = compute_next_run_at(
                        digest.frequency_cron, now=now.replace(tzinfo=UTC)
                    ).replace(tzinfo=None)
                except ValueError:
                    logger.warning("Digest %s has invalid cron '%s'", digest.id, digest.frequency_cron)
                    digest.next_run_at = None
        await session.commit()
    return enqueued


@celery_app.task(name="src.tasks.scheduler.scan_due_digests")
def scan_due_digests() -> int:
    return asyncio.run(scan_due_digests_async())
