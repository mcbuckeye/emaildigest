"""Tests for per-source health tracking + alerts."""

from __future__ import annotations


class TestSourceHealth:
    async def test_success_keeps_healthy(self, db, digest_with_source, mocker):
        from src.tasks.pipeline import fetch_all_sources

        mocker.patch(
            "src.tasks.pipeline.fetch_rss",
            autospec=True,
            return_value=[{"title": "x", "url": "u", "source_url": "s", "summary": ""}],
        )

        await fetch_all_sources(digest_with_source, session=db)

        src = digest_with_source.sources[0]
        await db.refresh(src)
        assert src.consecutive_failures == 0
        assert src.health == "healthy"
        assert src.last_error is None

    async def test_failure_increments_counter_and_degrades(
        self, db, digest_with_source, mocker
    ):
        from src.tasks.pipeline import fetch_all_sources

        mocker.patch(
            "src.tasks.pipeline.fetch_rss", autospec=True, side_effect=RuntimeError("boom")
        )

        src = digest_with_source.sources[0]
        src.consecutive_failures = 2
        await db.commit()

        await fetch_all_sources(digest_with_source, session=db)

        await db.refresh(src)
        assert src.consecutive_failures == 3
        assert src.health == "degraded"
        assert "boom" in (src.last_error or "")

    async def test_many_failures_marks_broken(self, db, digest_with_source, mocker):
        from src.tasks.pipeline import fetch_all_sources

        mocker.patch(
            "src.tasks.pipeline.fetch_rss", autospec=True, side_effect=RuntimeError("boom")
        )
        src = digest_with_source.sources[0]
        src.consecutive_failures = 5
        await db.commit()

        await fetch_all_sources(digest_with_source, session=db)
        await db.refresh(src)
        assert src.health == "broken"
