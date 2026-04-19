"""Tests for rich content extraction."""

from __future__ import annotations


class TestExtract:
    async def test_extracts_main_article_text(self, mocker):
        from src.tasks.extract import extract_article

        html = (
            "<html><body>"
            "<nav>menu</nav>"
            "<article><h1>Title</h1><p>This is the body paragraph with real content.</p></article>"
            "<footer>bye</footer>"
            "</body></html>"
        )

        mocker.patch(
            "src.tasks.extract._fetch_html",
            autospec=True,
            return_value=html,
        )

        text = await extract_article("https://example.com/article")
        assert "body paragraph" in text
        assert "menu" not in text

    async def test_handles_fetch_failure(self, mocker):
        from src.tasks.extract import extract_article

        mocker.patch("src.tasks.extract._fetch_html", autospec=True, side_effect=RuntimeError("x"))
        text = await extract_article("https://example.com/")
        assert text == ""
