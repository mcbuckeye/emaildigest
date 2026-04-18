"""Tests for the digest scheduler."""

from __future__ import annotations

from datetime import UTC, datetime

from freezegun import freeze_time

from src.models import Digest, DigestStatus


class TestComputeNextRun:
    def test_computes_next_fire_from_cron(self):
        from src.tasks.scheduler import compute_next_run_at

        now = datetime(2026, 1, 1, 8, 30, tzinfo=UTC)
        next_at = compute_next_run_at("0 9 * * *", now=now)
        assert next_at == datetime(2026, 1, 1, 9, 0, tzinfo=UTC)

    def test_rejects_invalid_cron(self):
        import pytest

        from src.tasks.scheduler import compute_next_run_at

        with pytest.raises(ValueError):
            compute_next_run_at("nonsense", now=datetime(2026, 1, 1, tzinfo=UTC))


class TestScanDueDigests:
    @freeze_time("2026-01-01 09:00:00")
    async def test_enqueues_only_due_active_digests(self, db, user, mocker):
        delay = mocker.patch("src.tasks.scheduler.generate_digest_task.delay")

        due = Digest(
            owner_id=user.id,
            name="Due",
            recipient_email=user.email,
            status=DigestStatus.ACTIVE.value,
            frequency_cron="0 9 * * *",
            next_run_at=datetime(2026, 1, 1, 8, 59),
        )
        future = Digest(
            owner_id=user.id,
            name="Future",
            recipient_email=user.email,
            status=DigestStatus.ACTIVE.value,
            frequency_cron="0 9 * * *",
            next_run_at=datetime(2026, 1, 1, 10, 0),
        )
        paused = Digest(
            owner_id=user.id,
            name="Paused",
            recipient_email=user.email,
            status=DigestStatus.PAUSED.value,
            frequency_cron="0 9 * * *",
            next_run_at=datetime(2026, 1, 1, 8, 0),
        )
        db.add_all([due, future, paused])
        await db.commit()
        await db.refresh(due)

        from src.tasks.scheduler import scan_due_digests_async

        await scan_due_digests_async()
        delay.assert_called_once_with(due.id)

    @freeze_time("2026-01-01 09:00:00")
    async def test_initializes_next_run_if_missing(self, db, user, mocker):
        mocker.patch("src.tasks.scheduler.generate_digest_task.delay")

        d = Digest(
            owner_id=user.id,
            name="No next_run",
            recipient_email=user.email,
            status=DigestStatus.ACTIVE.value,
            frequency_cron="0 10 * * *",
            next_run_at=None,
        )
        db.add(d)
        await db.commit()

        from src.tasks.scheduler import scan_due_digests_async

        await scan_due_digests_async()
        await db.refresh(d)
        assert d.next_run_at is not None

    @freeze_time("2026-01-01 09:05:00")
    async def test_advances_next_run_after_firing(self, db, user, mocker):
        mocker.patch("src.tasks.scheduler.generate_digest_task.delay")

        d = Digest(
            owner_id=user.id,
            name="Advance",
            recipient_email=user.email,
            status=DigestStatus.ACTIVE.value,
            frequency_cron="0 9 * * *",
            next_run_at=datetime(2026, 1, 1, 9, 0),
        )
        db.add(d)
        await db.commit()

        from src.tasks.scheduler import scan_due_digests_async

        await scan_due_digests_async()
        await db.refresh(d)
        assert d.next_run_at.date() == datetime(2026, 1, 2).date()
