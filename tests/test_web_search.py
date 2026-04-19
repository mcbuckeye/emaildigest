"""Tests for the web_search tool exposed to the AI assistant."""

from __future__ import annotations


class TestWebSearch:
    async def test_returns_top_results(self, mocker):
        from src.ai.tools import web_search

        mocker.patch(
            "src.ai.tools._run_duckduckgo_search",
            autospec=True,
            return_value=[
                {"title": "AI News", "url": "https://news.example/ai", "snippet": "latest"},
                {"title": "arXiv", "url": "https://arxiv.org/list/cs.AI", "snippet": "papers"},
            ],
        )
        result = await web_search("ai newsletters")
        assert result["ok"] is True
        assert len(result["results"]) == 2
        assert result["results"][0]["title"] == "AI News"

    async def test_filters_unsafe_urls(self, mocker):
        from src.ai.tools import web_search

        mocker.patch(
            "src.ai.tools._run_duckduckgo_search",
            autospec=True,
            return_value=[
                {"title": "bad", "url": "http://localhost/", "snippet": "ssrf"},
                {"title": "good", "url": "https://example.com/", "snippet": "ok"},
            ],
        )
        result = await web_search("anything")
        urls = [r["url"] for r in result["results"]]
        assert "http://localhost/" not in urls
        assert "https://example.com/" in urls

    async def test_handles_empty(self, mocker):
        from src.ai.tools import web_search

        mocker.patch("src.ai.tools._run_duckduckgo_search", autospec=True, return_value=[])
        result = await web_search("zzz")
        assert result["ok"] is False
