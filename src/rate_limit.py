"""Shared rate limiter instance."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address


def _identify(request):
    # Prefer user id from token if present, otherwise IP
    auth = request.headers.get("authorization") or ""
    if auth.lower().startswith("bearer "):
        return auth[7:64]
    return get_remote_address(request)


limiter = Limiter(key_func=_identify, default_limits=[])
