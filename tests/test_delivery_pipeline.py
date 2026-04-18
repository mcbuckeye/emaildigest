"""Tests for the delivery pipeline (fetch, summarize, render, send)."""

from __future__ import annotations

from email.message import EmailMessage

import pytest
from pytest_mock import MockerFixture


class TestSSRFGuard:
    @pytest.mark.parametrize(
        "url",
        [
            "http://localhost/foo",
            "http://127.0.0.1/foo",
            "http://169.254.169.254/",
            "http://10.0.0.1/foo",
            "file:///etc/passwd",
            "ftp://example.com",
            "http://192.168.1.1/",
        ],
    )
    def test_blocks_unsafe_urls(self, url):
        from src.tasks.fetchers import assert_safe_url

        with pytest.raises(ValueError):
            assert_safe_url(url)

    @pytest.mark.parametrize(
        "url",
        [
            "https://example.com/feed.xml",
            "http://news.ycombinator.com/rss",
            "https://techcrunch.com",
        ],
    )
    def test_allows_public_urls(self, url):
        from src.tasks.fetchers import assert_safe_url

        assert_safe_url(url)


class TestRenderEmail:
    async def test_builds_multipart_message(self, digest_with_source):
        from src.tasks.render import build_email_message

        items = [
            {
                "title": "Hello",
                "url": "https://example.com/1",
                "summary": "First",
                "source_url": "https://example.com/feed.xml",
                "published_at": None,
            },
            {
                "title": "World",
                "url": "https://example.com/2",
                "summary": "Second",
                "source_url": "https://example.com/feed.xml",
                "published_at": None,
            },
        ]
        msg: EmailMessage = build_email_message(digest_with_source, items, to_email="target@example.com")
        assert msg["To"] == "target@example.com"
        assert "Test Digest" in msg["Subject"]

        body_parts = list(msg.iter_parts())
        content_types = {p.get_content_type() for p in body_parts}
        assert {"text/plain", "text/html"} <= content_types

        html = next(p for p in body_parts if p.get_content_type() == "text/html").get_content()
        assert "Hello" in html
        assert "World" in html

    async def test_html_is_sanitized(self, digest_with_source):
        from src.tasks.render import build_email_message

        items = [
            {
                "title": "XSS",
                "url": "https://example.com/x",
                "summary": '<script>alert(1)</script><p>safe</p>',
                "source_url": "https://example.com/feed.xml",
                "published_at": None,
            }
        ]
        msg = build_email_message(digest_with_source, items, to_email="target@example.com")
        html = next(p for p in msg.iter_parts() if p.get_content_type() == "text/html").get_content()
        assert "<script" not in html
        assert "safe" in html


class TestSummarize:
    async def test_summarizes_items_via_llm(self, mocker: MockerFixture):
        from src.ai.summarizer import summarize_items

        mock_llm = mocker.patch("src.ai.summarizer.get_openai_client")
        mock_client = mocker.AsyncMock()
        mock_llm.return_value = mock_client

        async def fake_summary(*args, **kwargs):
            class Resp:
                choices = [
                    type("C", (), {"message": type("M", (), {"content": "A pithy summary."})})()
                ]
            return Resp()

        mock_client.chat.completions.create = fake_summary

        items = [
            {"title": "A", "url": "u", "summary": "long long long", "source_url": "s"},
            {"title": "B", "url": "u", "summary": "other text", "source_url": "s"},
        ]
        result = await summarize_items(items)
        assert all(r["summary"] == "A pithy summary." for r in result)


class TestRunDelivery:
    async def test_success_path_persists_items_and_marks_sent(
        self, db, digest_with_source, mocker: MockerFixture
    ):
        from src.tasks.pipeline import run_delivery

        items_in = [
            {
                "title": "T1",
                "url": "https://example.com/1",
                "summary": "s",
                "source_url": "https://example.com/feed.xml",
                "source_id": digest_with_source.sources[0].id,
                "published_at": None,
            },
        ]
        fetch_mock = mocker.patch("src.tasks.pipeline.fetch_all_sources", autospec=True)
        fetch_mock.return_value = items_in
        summ_mock = mocker.patch("src.tasks.pipeline.summarize_items", autospec=True)
        summ_mock.return_value = items_in
        send_mock = mocker.patch("src.tasks.pipeline.send_email_message", autospec=True)

        delivery_id = await run_delivery(digest_with_source.id)

        from src.models import DigestDelivery

        delivery = await db.get(DigestDelivery, delivery_id)
        assert delivery.status == "sent"
        assert delivery.sent_at is not None
        assert delivery.subject
        send_mock.assert_awaited_once()

    async def test_failure_marks_failed(self, db, digest_with_source, mocker):
        from src.tasks.pipeline import run_delivery

        fetch_mock = mocker.patch("src.tasks.pipeline.fetch_all_sources", autospec=True)
        fetch_mock.side_effect = RuntimeError("network down")

        with pytest.raises(RuntimeError):
            await run_delivery(digest_with_source.id)

        from sqlalchemy import select

        from src.models import DigestDelivery

        rows = (
            await db.execute(select(DigestDelivery).where(DigestDelivery.digest_id == digest_with_source.id))
        ).scalars().all()
        assert len(rows) == 1
        assert rows[0].status == "failed"
        assert "network down" in (rows[0].error_message or "")
