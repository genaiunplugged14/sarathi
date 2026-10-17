"""Sarathi v1 on the Agent SDK: the same tools, the same hooks.

uv run python 01-support-agent/sdk_agent.py "your message"

Lesson 9. The Agent SDK runs the loop, so this file has no loop
of its own. The four tools become an in-process MCP server, and
the hooks from lesson 7 plug in through HookMatcher, unchanged.
It signs in the way your Claude Code does, or with
ANTHROPIC_API_KEY if you set one. The key is never printed.
"""
import asyncio
import json
import sys

from claude_agent_sdk import (ClaudeAgentOptions, HookMatcher,
                              ResultMessage, create_sdk_mcp_server,
                              query, tool)

import hooks
import tools
from agent import SYSTEM


def as_sdk_tool(spec):
    @tool(spec["name"], spec["description"], spec["input_schema"])
    async def run(args):
        result = tools.run_tool(spec["name"], args)
        return {"content": [{"type": "text",
                             "text": json.dumps(result)}]}
    return run


SERVER = create_sdk_mcp_server(
    "support", tools=[as_sdk_tool(t) for t in tools.TOOLS])


def unwrap(response):
    """An MCP tool's result comes as text blocks; read the JSON."""
    if isinstance(response, dict) and "content" in response:
        response = response["content"]
    if isinstance(response, list):
        text = "".join(b.get("text", "") for b in response
                       if isinstance(b, dict))
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"text": text}
    return response


def sdk_hook(hook):
    """Wrap a lesson 7 hook in the async shape the SDK calls."""
    async def callback(input_data, tool_use_id, context):
        event = dict(input_data)
        if "tool_response" in event:
            event["tool_response"] = unwrap(event["tool_response"])
        return hook(event)
    return callback


def build_options():
    return ClaudeAgentOptions(
        system_prompt=SYSTEM,
        model="haiku",
        mcp_servers={"support": SERVER},
        tools=[],  # no built-in tools, only the four of ours
        allowed_tools=[f"mcp__support__{t['name']}"
                       for t in tools.TOOLS],
        hooks={
            "PreToolUse": [HookMatcher(
                hooks=[sdk_hook(hooks.refund_gate)])],
            "PostToolUse": [HookMatcher(
                hooks=[sdk_hook(hooks.remember_verified),
                       sdk_hook(hooks.normalize)])],
        },
        setting_sources=[],
        max_turns=20,  # a fuse, not the switch
    )


async def main(question):
    hooks.reset()
    tools.reset()
    options = build_options()
    async for msg in query(prompt=question, options=options):
        if isinstance(msg, ResultMessage):
            print(f"answer:   {msg.result}")
            print(f"turns:    {msg.num_turns}")
    print(f"refunds:  {json.dumps(tools.REFUNDS)}")
    print(f"handoffs: {json.dumps(tools.HANDOFFS)}")


if __name__ == "__main__":
    asyncio.run(main(" ".join(sys.argv[1:]) or (
        "Hi, I am Asha Rao, asha@example.com. My headphones "
        "from order O-5001 arrived broken. Please refund me.")))
