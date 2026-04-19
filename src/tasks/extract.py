"""Fetch and extract readable article text from a URL."""

from __future__ import annotations

import logging

import aiohttp
from bs4 import BeautifulSoup

from src.tasks.fetchers import assert_safe_url

logger = logging.getLogger(__name__)

_DROP = {"nav", "footer", "header", "aside", "script", "style", "form", "noscript"}


async def _fetch_html(url: str) -> str:
    assert_safe_url(url)
    timeout = aiohttp.ClientTimeout(total=12)
    async with aiohttp.ClientSession(timeout=timeout) as session, session.get(
        url, headers={"User-Agent": "Mozilla/5.0 EmailDigest"}
    ) as resp:
        return await resp.text()


def _strip_to_article(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(_DROP):
        tag.decompose()

    # Prefer <article> or role=main
    candidate = soup.find("article") or soup.find(attrs={"role": "main"}) or soup.body or soup
    text = candidate.get_text(" ", strip=True)
    return " ".join(text.split())[:8000]


async def extract_article(url: str) -> str:
    """Fetch and return readable article text. Returns "" on any failure."""
    try:
        html = await _fetch_html(url)
    except Exception as exc:
        logger.info("extract failed for %s: %s", url, exc)
        return ""
    return _strip_to_article(html)
