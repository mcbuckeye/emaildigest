"""Digest generation pipeline."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.ai.summarizer import summarize_items
from src.database import db_session
from src.mailer.client import send_email_message
from src.models import (
    DeliveryStatus,
    Digest,
    DigestDelivery,
    DigestItem,
    SourceType,
)
from src.tasks.celery_app import celery_app
from src.tasks.fetchers import fetch_rss, fetch_webpage
from src.tasks.render import build_email_message

logger = logging.getLogger(__name__)


async def fetch_all_sources(digest: Digest) -> list[dict[str, Any]]:
    all_items: list[dict[str, Any]] = []
    for source in digest.sources:
        try:
            if source.source_type == SourceType.RSS.value:
                items = await fetch_rss(source.url)
            else:
                items = await fetch_webpage(source.url)
        except Exception as exc:
            logger.warning("failed to fetch %s: %s", source.url, exc)
            continue
        for item in items:
            item["source_id"] = source.id
        all_items.extend(items)
    return all_items


async def run_delivery(digest_id: int) -> int:
    """Execute the end-to-end delivery for a digest. Returns the delivery id."""
    async with db_session() as session:
        stmt = (
            select(Digest)
            .where(Digest.id == digest_id)
            .options(selectinload(Digest.sources))
        )
        digest = (await session.execute(stmt)).scalar_one_or_none()
        if digest is None:
            raise ValueError(f"Digest {digest_id} not found")

        delivery = DigestDelivery(
            digest_id=digest.id,
            scheduled_at=datetime.utcnow(),
            status=DeliveryStatus.RUNNING.value,
            attempts=1,
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)
        delivery_id = delivery.id

        try:
            raw_items = await fetch_all_sources(digest)
            items = await summarize_items(raw_items)

            message = build_email_message(digest, items, to_email=digest.recipient_email)
            await send_email_message(message)

            delivery.html_body = next(
                (
                    part.get_content()
                    for part in message.iter_parts()
                    if part.get_content_type() == "text/html"
                ),
                None,
            )
            delivery.subject = message["Subject"]
            delivery.sent_at = datetime.utcnow()
            delivery.status = DeliveryStatus.SENT.value
            delivery.delivery_count = 1

            for item in items:
                session.add(
                    DigestItem(
                        delivery_id=delivery.id,
                        source_id=item.get("source_id"),
                        source_url=item.get("source_url", ""),
                        title=(item.get("title") or "")[:500],
                        summary=item.get("summary"),
                        url=(item.get("url") or "")[:1000],
                        published_at=item.get("published_at"),
                    )
                )

            digest.last_run_at = datetime.utcnow()
            await session.commit()
            return delivery_id

        except Exception as exc:
            logger.exception("delivery failed for digest %s", digest_id)
            delivery.status = DeliveryStatus.FAILED.value
            delivery.error_message = str(exc)
            await session.commit()
            raise


@celery_app.task(
    name="src.tasks.pipeline.generate_digest_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=3,
)
def generate_digest_task(self, digest_id: int) -> None:
    """Celery entrypoint: run a single digest delivery."""
    asyncio.run(run_delivery(digest_id))
