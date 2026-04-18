"""Tools exposed to the AI assistant."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import quote_plus, urljoin

import aiohttp
import feedparser
from bs4 import BeautifulSoup

from src.tasks.fetchers import assert_safe_url

logger = logging.getLogger(__name__)


async def validate_rss(url: str) -> dict[str, Any]:
    """Confirm an RSS URL is safe, reachable, and produces entries."""
    try:
        assert_safe_url(url)
    except ValueError as exc:
        return {"ok": False, "error": f"unsafe url: {exc}"}

    try:
        feed = feedparser.parse(url)
    except Exception as exc:
        return {"ok": False, "error": f"parse failed: {exc}"}

    entries = getattr(feed, "entries", []) or []
    if not entries:
        return {"ok": False, "error": "no entries found"}

    feed_meta = getattr(feed, "feed", {}) or {}
    return {
        "ok": True,
        "entry_count": len(entries),
        "title": feed_meta.get("title") if isinstance(feed_meta, dict) else getattr(feed_meta, "title", None),
    }


async def _run_duckduckgo_search(query: str, max_results: int = 8) -> list[dict[str, str]]:
    """Hit DuckDuckGo's HTML endpoint and parse results. Returns [] on failure."""
    url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
    timeout = aiohttp.ClientTimeout(total=10)
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session, session.get(
            url, headers={"User-Agent": "Mozilla/5.0 EmailDigest"}
        ) as resp:
            html = await resp.text()
    except Exception as exc:
        logger.warning("web search failed: %s", exc)
        return []

    soup = BeautifulSoup(html, "html.parser")
    out: list[dict[str, str]] = []
    for result in soup.select("div.result")[:max_results]:
        link = result.select_one("a.result__a")
        snippet = result.select_one("a.result__snippet") or result.select_one(".result__snippet")
        if not link:
            continue
        href = link.get("href") or ""
        href = urljoin("https://duckduckgo.com/", href)
        out.append(
            {
                "title": link.get_text(strip=True),
                "url": href,
                "snippet": (snippet.get_text(strip=True) if snippet else "")[:300],
            }
        )
    return out


async def web_search(query: str) -> dict[str, Any]:
    """Search the web for sources. Returns a filtered result list."""
    raw = await _run_duckduckgo_search(query)
    safe: list[dict[str, str]] = []
    for r in raw:
        try:
            assert_safe_url(r["url"])
        except ValueError:
            continue
        safe.append(r)

    if not safe:
        return {"ok": False, "error": "no results"}
    return {"ok": True, "results": safe}


TOOLS_SPEC: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the open web for candidate sources matching a topic.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "validate_rss",
            "description": "Validate that a URL is a real, parseable RSS/Atom feed.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "The RSS feed URL."},
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_digest",
            "description": "Propose a digest configuration for the user to confirm.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "frequency_cron": {"type": "string"},
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "source_type": {"type": "string", "enum": ["rss", "url"]},
                                "url": {"type": "string"},
                            },
                            "required": ["source_type", "url"],
                        },
                    },
                },
                "required": ["name", "frequency_cron", "sources"],
            },
        },
    },
]
