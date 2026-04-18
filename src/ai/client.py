"""OpenAI client factory."""

from __future__ import annotations

from functools import lru_cache

from openai import AsyncOpenAI

from src.config import config


@lru_cache
def get_openai_client() -> AsyncOpenAI:
    settings = config()
    kwargs: dict = {"api_key": settings.openai_api_key or "dummy"}
    if settings.openai_base_url:
        kwargs["base_url"] = settings.openai_base_url
    return AsyncOpenAI(**kwargs)
