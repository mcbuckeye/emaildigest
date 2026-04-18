"""Tests for recipient management and unsubscribe flow."""

from __future__ import annotations

from sqlalchemy import select

from src.models import DigestRecipient


class TestRecipientSync:
    async def test_creating_digest_creates_primary_recipient(
        self, client, auth_headers, db
    ):
        r = await client.post(
            "/api/digests",
            headers=auth_headers,
            json={
                "name": "D",
                "recipient_email": "me@example.com",
                "frequency_cron": "0 9 * * *",
                "sources": [{"source_type": "rss", "url": "https://example.com/feed"}],
            },
        )
        assert r.status_code == 201, r.text
        rows = (await db.execute(select(DigestRecipient))).scalars().all()
        assert len(rows) == 1
        assert rows[0].email == "me@example.com"
        assert rows[0].unsubscribe_token
        assert rows[0].unsubscribed_at is None

    async def test_add_extra_recipient(self, client, auth_headers, digest_with_source, db):
        r = await client.post(
            f"/api/digests/{digest_with_source.id}/recipients",
            headers=auth_headers,
            json={"email": "friend@example.com"},
        )
        assert r.status_code == 201
        data = r.json()
        assert data["email"] == "friend@example.com"
        assert data["unsubscribed_at"] is None

        # Dupes return 409
        r2 = await client.post(
            f"/api/digests/{digest_with_source.id}/recipients",
            headers=auth_headers,
            json={"email": "friend@example.com"},
        )
        assert r2.status_code == 409

    async def test_list_recipients_enforces_ownership(
        self, client, other_auth_headers, digest_with_source
    ):
        r = await client.get(
            f"/api/digests/{digest_with_source.id}/recipients", headers=other_auth_headers
        )
        assert r.status_code == 404


class TestUnsubscribeLink:
    async def test_public_unsubscribe_marks_row(self, client, db, digest_with_source, user):
        # Create a recipient manually
        rec = DigestRecipient(
            digest_id=digest_with_source.id,
            email="friend@example.com",
            unsubscribe_token="tok-abc123",
        )
        db.add(rec)
        await db.commit()

        r = await client.post(f"/api/unsubscribe/{rec.unsubscribe_token}")
        assert r.status_code == 200
        assert "unsubscribed" in r.json()["detail"].lower()

        # Fresh session to see effect
        await db.refresh(rec)
        assert rec.unsubscribed_at is not None

    async def test_unsubscribe_with_unknown_token_returns_404(self, client):
        r = await client.post("/api/unsubscribe/not-a-real-token")
        assert r.status_code == 404

    async def test_unsubscribed_recipient_is_skipped_on_delivery(
        self, client, db, digest_with_source, mocker
    ):
        from datetime import datetime

        from src.models import DigestRecipient

        active = DigestRecipient(
            digest_id=digest_with_source.id,
            email="active@example.com",
            unsubscribe_token="t1",
        )
        gone = DigestRecipient(
            digest_id=digest_with_source.id,
            email="gone@example.com",
            unsubscribe_token="t2",
            unsubscribed_at=datetime.utcnow(),
        )
        db.add_all([active, gone])
        await db.commit()

        mocker.patch("src.tasks.pipeline.fetch_all_sources", autospec=True, return_value=[])
        mocker.patch("src.tasks.pipeline.summarize_items", autospec=True, return_value=[])
        sent = mocker.patch("src.tasks.pipeline.send_email_message", autospec=True)

        from src.tasks.pipeline import run_delivery

        await run_delivery(digest_with_source.id)

        to_addrs = [call.args[0]["To"] for call in sent.call_args_list]
        assert "active@example.com" in to_addrs
        assert "gone@example.com" not in to_addrs
