"""Summarize digest items with OpenAI (with graceful fallback)."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from src.ai.client import get_openai_client
from src.config import config

logger = logging.getLogger(__name__)

SUMMARY_PROMPT = (
    "You are a concise newsletter editor. Summarize the article in 1–2 short sentences. "
    "Do not include disclaimers."
)


async def _summarize_one(client, model: str, item: dict[str, Any]) -> str:
    content_bits = [
        item.get("title") or "",
        item.get("summary") or "",
    ]
    content = "\n".join(bit for bit in content_bits if bit)
    if not content.strip():
        return ""
    resp = await client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": content[:4000]},
        ],
        temperature=0.3,
        max_tokens=120,
    )
    return (resp.choices[0].message.content or "").strip()


async def summarize_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Add an LLM-generated summary to each item. Falls back to original summary on error."""
    settings = config()
    if not items:
        return items
    if not settings.openai_api_key:
        return items

    client = get_openai_client()
    model = settings.openai_model

    async def enrich(item: dict[str, Any]) -> dict[str, Any]:
        try:
            summary = await _summarize_one(client, model, item)
            if summary:
                item = {**item, "summary": summary}
        except Exception as exc:  # pragma: no cover - network dependent
            logger.warning("summary generation failed: %s", exc)
        return item

    return await asyncio.gather(*(enrich(i) for i in items))
