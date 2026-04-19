"""AI assistant endpoints."""

from __future__ import annotations

import json
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from src.ai.chat import run_chat_turn, stream_chat_turn
from src.config import config
from src.models import User
from src.rate_limit import limiter
from src.routers.auth import get_current_user

router = APIRouter(prefix="/api/ai", tags=["ai"])


class ChatMessage(BaseModel):
    role: str
    content: str | None = None


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    history: list[ChatMessage] = Field(default_factory=list)


class ChatOut(BaseModel):
    reply: str
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    proposed_digest: dict[str, Any] | None = None


def _rate_limit() -> str:
    import os

    return os.environ.get("RATE_LIMIT_AI_CHAT") or config().rate_limit_ai_chat


@router.post("/chat", response_model=ChatOut)
@limiter.limit(_rate_limit)
async def chat(
    request: Request,
    payload: ChatIn,
    current_user: Annotated[User, Depends(get_current_user)],
) -> ChatOut:
    history = [m.model_dump(exclude_none=True) for m in payload.history]
    result = await run_chat_turn(payload.message, history)
    return ChatOut(**result)


@router.post("/chat/stream")
@limiter.limit(_rate_limit)
async def chat_stream(
    request: Request,
    payload: ChatIn,
    current_user: Annotated[User, Depends(get_current_user)],
) -> StreamingResponse:
    history = [m.model_dump(exclude_none=True) for m in payload.history]

    async def sse():
        async for event in stream_chat_turn(payload.message, history):
            yield f"data: {json.dumps(event)}\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
