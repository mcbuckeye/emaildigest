"""Tests for the AI-assisted digest creation flow."""

from __future__ import annotations


class TestValidateRssTool:
    async def test_valid_feed(self, mocker):
        from src.ai.tools import validate_rss

        mocker.patch(
            "src.ai.tools.feedparser.parse",
            return_value=type(
                "F",
                (),
                {
                    "entries": [type("E", (), {"title": "t", "link": "u"})],
                    "feed": {"title": "My Feed"},
                    "bozo": 0,
                },
            )(),
        )
        result = await validate_rss("https://example.com/feed.xml")
        assert result["ok"] is True
        assert result["entry_count"] >= 1
        assert result["title"] == "My Feed"

    async def test_blocks_unsafe_url(self):
        from src.ai.tools import validate_rss

        result = await validate_rss("http://localhost/feed.xml")
        assert result["ok"] is False
        assert "unsafe" in result["error"].lower()


class TestAiChatEndpoint:
    async def test_requires_auth(self, client):
        r = await client.post("/api/ai/chat", json={"message": "hi"})
        assert r.status_code == 401

    async def test_returns_assistant_reply(self, client, auth_headers, mocker):
        async def fake_chat(message, history):
            return {
                "reply": "I found a feed for you.",
                "tool_calls": [
                    {
                        "tool": "validate_rss",
                        "args": {"url": "https://example.com/feed.xml"},
                        "result": {"ok": True, "entry_count": 10, "title": "Example"},
                    }
                ],
                "proposed_digest": {
                    "name": "Example weekly",
                    "frequency_cron": "0 9 * * 1",
                    "sources": [{"source_type": "rss", "url": "https://example.com/feed.xml"}],
                },
            }

        mocker.patch("src.routers.ai.run_chat_turn", side_effect=fake_chat)

        r = await client.post(
            "/api/ai/chat",
            headers=auth_headers,
            json={"message": "weekly example"},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["reply"] == "I found a feed for you."
        assert data["proposed_digest"]["name"] == "Example weekly"

    async def test_rate_limited(self, client, auth_headers, mocker):
        mocker.patch("src.routers.ai.run_chat_turn", return_value={"reply": "ok"})
        # Exceed the test limit
        import os

        from src.config import reset_settings_cache

        os.environ["RATE_LIMIT_AI_CHAT"] = "2/minute"
        reset_settings_cache()
        try:
            from asgi_lifespan import LifespanManager
            from httpx import ASGITransport, AsyncClient

            from src.main import create_app

            app = create_app()
            async with LifespanManager(app):
                transport = ASGITransport(app=app)
                async with AsyncClient(transport=transport, base_url="http://test") as ac:
                    for _ in range(2):
                        r = await ac.post("/api/ai/chat", headers=auth_headers, json={"message": "a"})
                        assert r.status_code in (200, 429)
                    r = await ac.post("/api/ai/chat", headers=auth_headers, json={"message": "a"})
                    assert r.status_code == 429
        finally:
            os.environ.pop("RATE_LIMIT_AI_CHAT", None)
            reset_settings_cache()
