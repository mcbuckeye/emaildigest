"""Tests for digest endpoints."""

from __future__ import annotations

from httpx import AsyncClient
from sqlalchemy import select

from src.models import Digest, DigestSource, DigestStatus


class TestListDigests:
    async def test_empty(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/digests", headers=auth_headers)
        assert r.status_code == 200
        assert r.json() == []

    async def test_lists_only_user_digests(
        self, client: AsyncClient, db, user, other_user, auth_headers
    ):
        mine = Digest(
            owner_id=user.id,
            name="Mine",
            recipient_email=user.email,
            status=DigestStatus.ACTIVE.value,
        )
        theirs = Digest(
            owner_id=other_user.id,
            name="Theirs",
            recipient_email=other_user.email,
            status=DigestStatus.ACTIVE.value,
        )
        db.add_all([mine, theirs])
        await db.commit()

        r = await client.get("/api/digests", headers=auth_headers)
        assert r.status_code == 200
        names = [d["name"] for d in r.json()]
        assert names == ["Mine"]

    async def test_requires_auth(self, client: AsyncClient):
        r = await client.get("/api/digests")
        assert r.status_code == 401


class TestCreateDigest:
    async def test_creates_digest_with_sources(self, client: AsyncClient, db, auth_headers, user):
        r = await client.post(
            "/api/digests",
            headers=auth_headers,
            json={
                "name": "AI News",
                "description": "weekly AI",
                "frequency_cron": "0 9 * * 1",
                "recipient_email": "me@example.com",
                "sources": [
                    {"source_type": "rss", "url": "https://example.com/feed.xml"},
                    {"source_type": "url", "url": "https://example.com/page"},
                ],
            },
        )
        assert r.status_code == 201, r.text
        data = r.json()
        assert data["name"] == "AI News"
        assert len(data["sources"]) == 2

        rows = (await db.execute(select(DigestSource))).scalars().all()
        assert len(rows) == 2

    async def test_validates_required_fields(self, client: AsyncClient, auth_headers):
        r = await client.post(
            "/api/digests",
            headers=auth_headers,
            json={"description": "missing name"},
        )
        assert r.status_code == 422

    async def test_rejects_invalid_cron(self, client: AsyncClient, auth_headers):
        r = await client.post(
            "/api/digests",
            headers=auth_headers,
            json={
                "name": "Bad Cron",
                "recipient_email": "me@example.com",
                "frequency_cron": "not-a-cron",
                "sources": [{"source_type": "rss", "url": "https://example.com/x"}],
            },
        )
        assert r.status_code == 422


class TestGetDigest:
    async def test_returns_digest_for_owner(self, client, auth_headers, digest_with_source):
        r = await client.get(f"/api/digests/{digest_with_source.id}", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["id"] == digest_with_source.id
        assert len(data["sources"]) == 1

    async def test_404_when_missing(self, client, auth_headers):
        r = await client.get("/api/digests/999999", headers=auth_headers)
        assert r.status_code == 404

    async def test_403_when_not_owner(self, client, other_auth_headers, digest_with_source):
        r = await client.get(f"/api/digests/{digest_with_source.id}", headers=other_auth_headers)
        assert r.status_code == 404  # Don't leak existence


class TestUpdateDigest:
    async def test_updates_fields(self, client, auth_headers, digest_with_source):
        r = await client.patch(
            f"/api/digests/{digest_with_source.id}",
            headers=auth_headers,
            json={"name": "Renamed", "frequency_cron": "0 12 * * *"},
        )
        assert r.status_code == 200
        assert r.json()["name"] == "Renamed"
        assert r.json()["frequency_cron"] == "0 12 * * *"


class TestDeleteDigest:
    async def test_deletes_owned(self, client, auth_headers, digest_with_source, db):
        r = await client.delete(f"/api/digests/{digest_with_source.id}", headers=auth_headers)
        assert r.status_code == 204
        remaining = (await db.execute(select(Digest))).scalars().all()
        assert remaining == []

    async def test_404_for_other(self, client, other_auth_headers, digest_with_source):
        r = await client.delete(f"/api/digests/{digest_with_source.id}", headers=other_auth_headers)
        assert r.status_code == 404


class TestPauseResume:
    async def test_pause_then_resume(self, client, auth_headers, digest_with_source):
        r = await client.post(f"/api/digests/{digest_with_source.id}/pause", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "paused"

        r = await client.post(f"/api/digests/{digest_with_source.id}/resume", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["status"] == "active"


class TestResend:
    async def test_resend_queues_new_delivery(self, client, auth_headers, digest_with_source, mocker):
        enqueued = mocker.patch("src.routers.digests.generate_digest_task.delay")

        r = await client.post(f"/api/digests/{digest_with_source.id}/resend", headers=auth_headers)
        assert r.status_code == 202
        enqueued.assert_called_once_with(digest_with_source.id)

    async def test_resend_forbidden_for_others(self, client, other_auth_headers, digest_with_source):
        r = await client.post(
            f"/api/digests/{digest_with_source.id}/resend", headers=other_auth_headers
        )
        assert r.status_code == 404
