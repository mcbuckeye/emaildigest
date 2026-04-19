"""Tests for item dedup via fingerprint."""

from __future__ import annotations

from datetime import datetime

import pytest_asyncio

from src.models import DeliveryStatus, DigestDelivery, DigestItem


@pytest_asyncio.fixture
async def prev_delivery_with_item(db, digest_with_source):
    from src.tasks.pipeline import compute_fingerprint

    delivery = DigestDelivery(
        digest_id=digest_with_source.id,
        scheduled_at=datetime.utcnow(),
        sent_at=datetime.utcnow(),
        status=DeliveryStatus.SENT.value,
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)

    db.add(
        DigestItem(
            delivery_id=delivery.id,
            digest_id=digest_with_source.id,
            source_id=digest_with_source.sources[0].id,
            source_url="https://example.com/feed",
            title="Seen",
            summary="Already sent",
            url="https://example.com/seen",
            fingerprint=compute_fingerprint({"url": "https://example.com/seen", "title": "Seen"}),
        )
    )
    await db.commit()
    return delivery


class TestFingerprint:
    def test_fingerprint_is_stable_for_same_url(self):
        from src.tasks.pipeline import compute_fingerprint

        a = compute_fingerprint({"url": "https://example.com/a", "title": "A"})
        b = compute_fingerprint({"url": "https://example.com/a", "title": "different"})
        assert a == b

    def test_fingerprint_falls_back_to_title_if_no_url(self):
        from src.tasks.pipeline import compute_fingerprint

        fp = compute_fingerprint({"url": "", "title": "Some Title"})
        assert fp


class TestDedup:
    async def test_previously_sent_items_are_filtered(
        self, db, digest_with_source, prev_delivery_with_item, mocker
    ):
        from src.tasks.pipeline import run_delivery

        fresh_items = [
            {
                "title": "Seen",
                "url": "https://example.com/seen",
                "summary": "x",
                "source_url": "https://example.com/feed",
                "source_id": digest_with_source.sources[0].id,
                "published_at": None,
            },
            {
                "title": "New",
                "url": "https://example.com/new",
                "summary": "y",
                "source_url": "https://example.com/feed",
                "source_id": digest_with_source.sources[0].id,
                "published_at": None,
            },
        ]
        mocker.patch("src.tasks.pipeline.fetch_all_sources", autospec=True, return_value=fresh_items)
        mocker.patch("src.tasks.pipeline.summarize_items", autospec=True, side_effect=lambda items: items)
        send = mocker.patch("src.tasks.pipeline.send_email_message", autospec=True)

        delivery_id = await run_delivery(digest_with_source.id)
        send.assert_awaited()

        from sqlalchemy import select

        items = (
            await db.execute(select(DigestItem).where(DigestItem.delivery_id == delivery_id))
        ).scalars().all()
        titles = {i.title for i in items}
        assert "New" in titles
        assert "Seen" not in titles
