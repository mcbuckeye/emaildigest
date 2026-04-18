"""Digest generation pipeline."""

from __future__ import annotations

import asyncio
import hashlib
import logging
import secrets
from datetime import datetime
from email.message import EmailMessage
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.ai.summarizer import summarize_items
from src.config import config
from src.database import db_session
from src.mailer.client import send_email_message
from src.metrics import DELIVERIES
from src.models import (
    DeliveryStatus,
    Digest,
    DigestDelivery,
    DigestItem,
    DigestRecipient,
    DigestSource,
    SourceHealth,
    SourceType,
)
from src.tasks.celery_app import celery_app
from src.tasks.fetchers import fetch_rss, fetch_webpage
from src.tasks.render import build_email_message

logger = logging.getLogger(__name__)

BROKEN_AFTER = 5  # consecutive failures → broken
DEGRADED_AFTER = 2


def compute_fingerprint(item: dict[str, Any]) -> str:
    key = (item.get("url") or "").strip() or (item.get("title") or "").strip()
    return hashlib.sha256(key.encode("utf-8")).hexdigest()[:40] if key else ""


def _health_from(failures: int) -> str:
    if failures >= BROKEN_AFTER:
        return SourceHealth.BROKEN.value
    if failures >= DEGRADED_AFTER:
        return SourceHealth.DEGRADED.value
    return SourceHealth.HEALTHY.value


async def _mark_source_success(source: DigestSource, session: AsyncSession) -> None:
    source.consecutive_failures = 0
    source.health = SourceHealth.HEALTHY.value
    source.last_error = None
    source.last_scraped_at = datetime.utcnow()
    source.last_checked_at = datetime.utcnow()
    await session.commit()


async def _mark_source_failure(source: DigestSource, exc: Exception, session: AsyncSession) -> None:
    source.consecutive_failures = (source.consecutive_failures or 0) + 1
    source.health = _health_from(source.consecutive_failures)
    source.last_error = str(exc)[:500]
    source.last_checked_at = datetime.utcnow()
    await session.commit()


async def fetch_all_sources(
    digest: Digest, *, session: AsyncSession | None = None
) -> list[dict[str, Any]]:
    all_items: list[dict[str, Any]] = []
    for source in digest.sources:
        try:
            if source.source_type == SourceType.RSS.value:
                items = await fetch_rss(source.url)
            else:
                items = await fetch_webpage(source.url)
        except Exception as exc:
            logger.warning("failed to fetch %s: %s", source.url, exc)
            if session is not None:
                await _mark_source_failure(source, exc, session)
            continue

        if session is not None:
            await _mark_source_success(source, session)
        for item in items:
            item["source_id"] = source.id
        all_items.extend(items)
    return all_items


async def _load_seen_fingerprints(digest_id: int, session: AsyncSession) -> set[str]:
    stmt = select(DigestItem.fingerprint).where(
        DigestItem.digest_id == digest_id, DigestItem.fingerprint.is_not(None)
    )
    rows = (await session.execute(stmt)).all()
    return {r[0] for r in rows}


async def _active_recipients(digest: Digest, session: AsyncSession) -> list[DigestRecipient]:
    stmt = (
        select(DigestRecipient)
        .where(DigestRecipient.digest_id == digest.id, DigestRecipient.unsubscribed_at.is_(None))
    )
    rows = (await session.execute(stmt)).scalars().all()
    if rows:
        return list(rows)
    # legacy fallback: single recipient_email
    if digest.recipient_email:
        rec = DigestRecipient(
            digest_id=digest.id,
            email=digest.recipient_email,
            unsubscribe_token=secrets.token_urlsafe(24),
        )
        session.add(rec)
        await session.commit()
        return [rec]
    return []


def _personalize(message: EmailMessage, recipient: DigestRecipient) -> EmailMessage:
    """Return a new EmailMessage addressed to `recipient` with an unsubscribe footer."""
    settings = config()
    unsub_url = f"{settings.app_base_url.rstrip('/')}/unsubscribe?token={recipient.unsubscribe_token}"

    msg = EmailMessage()
    for header in ("From", "Subject"):
        if message[header]:
            msg[header] = message[header]
    msg["To"] = recipient.email
    msg["List-Unsubscribe"] = f"<{unsub_url}>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"

    plain = next(
        (p.get_content() for p in message.iter_parts() if p.get_content_type() == "text/plain"), ""
    )
    html = next(
        (p.get_content() for p in message.iter_parts() if p.get_content_type() == "text/html"), ""
    )

    footer_plain = f"\n\n---\nUnsubscribe: {unsub_url}\n"
    footer_html = (
        f'<hr><p style="font-size:11px;color:#999">'
        f'<a href="{unsub_url}">Unsubscribe from this digest</a></p>'
    )
    msg.set_content(plain + footer_plain)
    msg.add_alternative(html + footer_html, subtype="html")
    return msg


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
            tracking_token=secrets.token_urlsafe(24),
        )
        session.add(delivery)
        await session.commit()
        await session.refresh(delivery)
        delivery_id = delivery.id

        try:
            raw_items = await fetch_all_sources(digest, session=session)

            seen = await _load_seen_fingerprints(digest.id, session)
            deduped: list[dict[str, Any]] = []
            for item in raw_items:
                fp = compute_fingerprint(item)
                if fp and fp in seen:
                    continue
                if fp:
                    seen.add(fp)
                item["fingerprint"] = fp
                deduped.append(item)

            items = await summarize_items(deduped)

            recipients = await _active_recipients(digest, session)

            message = build_email_message(digest, items, to_email=digest.recipient_email)
            for rec in recipients:
                personalized = _personalize(message, rec)
                await send_email_message(personalized)

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
            delivery.delivery_count = len(recipients)

            for item in items:
                session.add(
                    DigestItem(
                        delivery_id=delivery.id,
                        digest_id=digest.id,
                        source_id=item.get("source_id"),
                        source_url=item.get("source_url", ""),
                        title=(item.get("title") or "")[:500],
                        summary=item.get("summary"),
                        url=(item.get("url") or "")[:1000],
                        fingerprint=item.get("fingerprint"),
                        published_at=item.get("published_at"),
                    )
                )

            digest.last_run_at = datetime.utcnow()
            await session.commit()
            DELIVERIES.labels(status="sent").inc()
            return delivery_id

        except Exception as exc:
            logger.exception("delivery failed for digest %s", digest_id)
            delivery.status = DeliveryStatus.FAILED.value
            delivery.error_message = str(exc)
            await session.commit()
            DELIVERIES.labels(status="failed").inc()
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
