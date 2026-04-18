"""Tests for delivery listing and preview endpoints."""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest_asyncio

from src.models import DeliveryStatus, DigestDelivery, DigestItem


@pytest_asyncio.fixture
async def delivery_with_items(db, digest_with_source):
    delivery = DigestDelivery(
        digest_id=digest_with_source.id,
        scheduled_at=datetime.utcnow() - timedelta(hours=1),
        sent_at=datetime.utcnow(),
        status=DeliveryStatus.SENT.value,
        subject="Your digest",
        html_body="<h1>Hi</h1><p>Items</p>",
    )
    db.add(delivery)
    await db.commit()
    await db.refresh(delivery)

    for i in range(3):
        db.add(
            DigestItem(
                delivery_id=delivery.id,
                source_id=digest_with_source.sources[0].id,
                source_url="https://example.com/feed.xml",
                title=f"Item {i}",
                summary=f"Summary {i}",
                url=f"https://example.com/item/{i}",
                published_at=datetime.utcnow(),
            )
        )
    await db.commit()
    await db.refresh(delivery)
    return delivery


class TestListDeliveries:
    async def test_lists_deliveries_for_digest(self, client, auth_headers, digest_with_source, delivery_with_items):
        r = await client.get(
            f"/api/digests/{digest_with_source.id}/deliveries", headers=auth_headers
        )
        assert r.status_code == 200
        data = r.json()
        assert len(data) == 1
        assert data[0]["status"] == "sent"
        assert data[0]["item_count"] == 3

    async def test_enforces_ownership(self, client, other_auth_headers, digest_with_source):
        r = await client.get(
            f"/api/digests/{digest_with_source.id}/deliveries", headers=other_auth_headers
        )
        assert r.status_code == 404


class TestDeliveryPreview:
    async def test_returns_html(self, client, auth_headers, delivery_with_items):
        r = await client.get(
            f"/api/deliveries/{delivery_with_items.id}/preview", headers=auth_headers
        )
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("text/html")
        assert "Hi" in r.text

    async def test_enforces_ownership(self, client, other_auth_headers, delivery_with_items):
        r = await client.get(
            f"/api/deliveries/{delivery_with_items.id}/preview", headers=other_auth_headers
        )
        assert r.status_code == 404
