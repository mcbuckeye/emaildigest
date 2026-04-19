"""Tests for /api/ai/chat streaming."""

from __future__ import annotations


class TestChatStream:
    async def test_stream_returns_sse_events(self, client, auth_headers, mocker):
        async def fake_stream(message, history):
            yield {"type": "token", "content": "Hello"}
            yield {"type": "token", "content": " world"}
            yield {
                "type": "final",
                "reply": "Hello world",
                "tool_calls": [],
                "proposed_digest": None,
            }

        mocker.patch("src.routers.ai.stream_chat_turn", side_effect=fake_stream)

        async with client.stream(
            "POST",
            "/api/ai/chat/stream",
            headers=auth_headers,
            json={"message": "hi"},
        ) as r:
            assert r.status_code == 200
            assert r.headers["content-type"].startswith("text/event-stream")
            body = ""
            async for chunk in r.aiter_text():
                body += chunk
        assert "Hello" in body
        assert "final" in body
