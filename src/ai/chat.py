"""AI chat loop for digest creation."""

from __future__ import annotations

import json
import logging
from typing import Any

from src.ai.client import get_openai_client
from src.ai.tools import TOOLS_SPEC, validate_rss
from src.config import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are EmailDigest's onboarding assistant. Help the user create a newsletter digest.\n"
    "1. Understand what topics/sources they want.\n"
    "2. Use the validate_rss tool to confirm candidate feeds.\n"
    "3. Propose a concrete digest via the propose_digest tool (name, frequency_cron, sources).\n"
    "Keep responses short and actionable."
)


async def _dispatch_tool(name: str, args: dict[str, Any]) -> Any:
    if name == "validate_rss":
        return await validate_rss(args["url"])
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

    for _ in range(4):  # bound tool-call loop
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
