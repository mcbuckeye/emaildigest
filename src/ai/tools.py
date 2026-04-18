"""Tools exposed to the AI assistant."""

from __future__ import annotations

import logging
from typing import Any

import feedparser

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


TOOLS_SPEC: list[dict[str, Any]] = [
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
