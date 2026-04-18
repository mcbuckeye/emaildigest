"""Tests for open-pixel + click-through tracking."""

from __future__ import annotations

from datetime import datetime

import pytest_asyncio

from src.models import DeliveryStatus, DigestDelivery, DigestItem


@pytest_asyncio.fixture
async def tracked_delivery(db, digest_with_source):
    delivery = DigestDelivery(
        digest_id=digest_with_source.id,
        scheduled_at=datetime.utcnow(),
        sent_at=datetime.utcnow(),
        status=DeliveryStatus.SENT.value,
        tracking_token="trk-abc",
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)
    item = DigestItem(
        delivery_id=delivery.id,
        digest_id=digest_with_source.id,
        source_id=digest_with_source.sources[0].id,
        source_url="https://example.com/feed",
        title="T",
        summary="s",
        url="https://example.com/item",
        fingerprint="fp",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return delivery, item


class TestOpenPixel:
    async def test_pixel_increments_open_count(self, client, db, tracked_delivery):
        delivery, _item = tracked_delivery
        r = await client.get(f"/api/track/open/{delivery.tracking_token}.gif")
        assert r.status_code == 200
        assert r.headers["content-type"] == "image/gif"

        await db.refresh(delivery)
        assert delivery.open_count == 1


class TestClickRedirect:
    async def test_click_redirects_and_increments(self, client, db, tracked_delivery):
        delivery, item = tracked_delivery
        r = await client.get(
            f"/api/track/click/{delivery.tracking_token}/{item.id}",
            follow_redirects=False,
        )
        assert r.status_code == 307
        assert r.headers["location"] == item.url

        await db.refresh(delivery)
        await db.refresh(item)
        assert delivery.click_count == 1
        assert item.click_count == 1


class TestDeliveryAnalyticsEndpoint:
    async def test_exposes_open_and_click_totals(
        self, db, client, auth_headers, digest_with_source, tracked_delivery
    ):
        delivery, _ = tracked_delivery
        delivery.open_count = 4
        delivery.click_count = 2
        await db.commit()

        r = await client.get(
            f"/api/digests/{digest_with_source.id}/deliveries", headers=auth_headers
        )
        assert r.status_code == 200
        payload = r.json()
        assert any(d["open_count"] == 4 and d["click_count"] == 2 for d in payload)
