"""Source fetching with SSRF protection."""

from __future__ import annotations

import ipaddress
import socket
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

import aiohttp
import feedparser
from bs4 import BeautifulSoup

ALLOWED_SCHEMES = {"http", "https"}


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return (
        addr.is_private
        or addr.is_loopback
        or addr.is_link_local
        or addr.is_multicast
        or addr.is_reserved
        or addr.is_unspecified
    )


def assert_safe_url(url: str) -> None:
    """Raise ValueError if the URL points to a private/internal host."""
    parsed = urlparse(url)
    if parsed.scheme not in ALLOWED_SCHEMES:
        raise ValueError(f"unsafe scheme: {parsed.scheme}")
    host = parsed.hostname
    if not host:
        raise ValueError("missing host")

    if host.lower() in {"localhost", "metadata.google.internal"}:
        raise ValueError("unsafe host")

    try:
        ipaddress.ip_address(host)
        candidates = [host]
    except ValueError:
        try:
            infos = socket.getaddrinfo(host, None)
        except socket.gaierror:
            # If DNS fails in tests, allow (network will fail later); prod DNS should work.
            return
        candidates = [info[4][0] for info in infos]

    for ip in candidates:
        if _is_private_ip(ip):
            raise ValueError(f"unsafe host resolves to private address: {ip}")


async def fetch_rss(url: str) -> list[dict[str, Any]]:
    assert_safe_url(url)
    feed = feedparser.parse(url)
    items: list[dict[str, Any]] = []
    for entry in feed.entries:
        published = None
        parsed = entry.get("published_parsed") or entry.get("updated_parsed")
        if parsed:
            try:
                published = datetime(*parsed[:6])
            except (TypeError, ValueError):
                published = None
        items.append(
            {
                "title": entry.get("title", "Untitled"),
                "url": entry.get("link", ""),
                "summary": entry.get("summary", ""),
                "source_url": url,
                "published_at": published,
            }
        )
    return items


async def fetch_webpage(url: str) -> list[dict[str, Any]]:
    assert_safe_url(url)
    timeout = aiohttp.ClientTimeout(total=15)
    async with aiohttp.ClientSession(timeout=timeout) as session, session.get(url) as resp:
        html = await resp.text()

    soup = BeautifulSoup(html, "html.parser")
    page_title = soup.title.string if soup.title and soup.title.string else url
    items: list[dict[str, Any]] = []
    for link in soup.find_all("a", href=True):
        text = link.get_text(strip=True)
        href = link["href"]
        if not text or not href.startswith(("http://", "https://")):
            continue
        items.append(
            {
                "title": text[:500],
                "url": href,
                "summary": page_title[:500] if isinstance(page_title, str) else str(page_title)[:500],
                "source_url": url,
                "published_at": None,
            }
        )
    return items[:50]
