"""AI chat loop for digest creation (sync + streaming variants)."""

from __future__ import annotations

import json
import logging
from collections.abc import AsyncIterator
from typing import Any

from src.ai.client import get_openai_client
from src.ai.tools import TOOLS_SPEC, validate_rss, web_search
from src.config import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are EmailDigest's onboarding assistant. Help the user create a newsletter digest.\n"
    "1. Understand what topics/sources they want.\n"
    "2. Use web_search to discover candidate sources when the user is vague.\n"
    "3. Use validate_rss to confirm candidate feeds.\n"
    "4. Propose a concrete digest via the propose_digest tool (name, frequency_cron, sources).\n"
    "Keep responses short and actionable."
)


async def _dispatch_tool(name: str, args: dict[str, Any]) -> Any:
    if name == "validate_rss":
        return await validate_rss(args["url"])
    if name == "web_search":
        return await web_search(args["query"])
    if name == "propose_digest":
        return {"proposed": args}
    return {"error": f"unknown tool: {name}"}


async def run_chat_turn(message: str, history: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    """Run one chat turn. Returns {reply, tool_calls, proposed_digest?}."""
    settings = config()
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    client = get_openai_client()

    tool_calls_out: list[dict[str, Any]] = []
    proposed: dict[str, Any] | None = None

    for _ in range(4):
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=TOOLS_SPEC,
            tool_choice="auto",
            temperature=0.2,
        )
        choice = resp.choices[0]
        msg = choice.message

        if not msg.tool_calls:
            return {
                "reply": msg.content or "",
                "tool_calls": tool_calls_out,
                "proposed_digest": proposed,
            }

        messages.append(msg.model_dump())
        for call in msg.tool_calls:
            name = call.function.name
            try:
                args = json.loads(call.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = await _dispatch_tool(name, args)
            tool_calls_out.append({"tool": name, "args": args, "result": result})
            if name == "propose_digest":
                proposed = args
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result),
                }
            )

    return {
        "reply": "Stopped after 4 tool-call iterations.",
        "tool_calls": tool_calls_out,
        "proposed_digest": proposed,
    }


async def stream_chat_turn(
    message: str, history: list[dict[str, Any]] | None = None
) -> AsyncIterator[dict[str, Any]]:
    """Run one chat turn and yield SSE-friendly events.

    Events:
        {"type": "tool", "name": ..., "args": ..., "result": ...}
        {"type": "token", "content": ...}
        {"type": "final", "reply": ..., "tool_calls": [...], "proposed_digest": ...}
    """
    settings = config()
    messages: list[dict[str, Any]] = [{"role": "system", "content": SYSTEM_PROMPT}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})

    client = get_openai_client()
    tool_calls_out: list[dict[str, Any]] = []
    proposed: dict[str, Any] | None = None

    for _ in range(4):
        resp = await client.chat.completions.create(
            model=settings.openai_model,
            messages=messages,
            tools=TOOLS_SPEC,
            tool_choice="auto",
            temperature=0.2,
            stream=True,
        )

        pending_tool_calls: dict[int, dict[str, Any]] = {}
        content_buf: list[str] = []

        async for chunk in resp:
            delta = chunk.choices[0].delta
            if delta.content:
                content_buf.append(delta.content)
                yield {"type": "token", "content": delta.content}
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    slot = pending_tool_calls.setdefault(idx, {"id": "", "name": "", "args": ""})
                    if tc.id:
                        slot["id"] = tc.id
                    if tc.function and tc.function.name:
                        slot["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        slot["args"] += tc.function.arguments

        if not pending_tool_calls:
            reply = "".join(content_buf)
            yield {
                "type": "final",
                "reply": reply,
                "tool_calls": tool_calls_out,
                "proposed_digest": proposed,
            }
            return

        # Add assistant message referencing the tool calls
        messages.append(
            {
                "role": "assistant",
                "content": "".join(content_buf) or None,
                "tool_calls": [
                    {
                        "id": slot["id"],
                        "type": "function",
                        "function": {"name": slot["name"], "arguments": slot["args"]},
                    }
                    for slot in pending_tool_calls.values()
                ],
            }
        )
        for slot in pending_tool_calls.values():
            try:
                args = json.loads(slot["args"] or "{}")
            except json.JSONDecodeError:
                args = {}
            result = await _dispatch_tool(slot["name"], args)
            tool_calls_out.append({"tool": slot["name"], "args": args, "result": result})
            if slot["name"] == "propose_digest":
                proposed = args
            yield {"type": "tool", "name": slot["name"], "args": args, "result": result}
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": slot["id"],
                    "content": json.dumps(result),
                }
            )

    yield {
        "type": "final",
        "reply": "Stopped after 4 tool-call iterations.",
        "tool_calls": tool_calls_out,
        "proposed_digest": proposed,
    }
