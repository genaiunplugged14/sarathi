"""Sarathi v1, part 2: run the research coordinator.

Live:     uv run python 03-research-system/coordinator.py
Compare:  uv run python 03-research-system/coordinator.py --compare
Offline:  uv run python 03-research-system/demo.py

The live run uses the Agent SDK, which drives Claude Code. It
signs in the way your Claude Code does, or with ANTHROPIC_API_KEY
if you set one (lesson 4). The key is never printed.
"""
import asyncio
import sys
import time

from claude_agent_sdk import (AssistantMessage, ResultMessage,
                              ToolResultBlock, ToolUseBlock,
                              UserMessage, query)

import findings
import verify
from agents import HERE, SPAWN_TOOLS, WRITER, build_options

QUESTION = ("Should our store move from a 30 day to a 60 day "
            "return window? Find the evidence for and against.")


def text_of(content):
    if isinstance(content, str):
        return content
    return "".join(part.get("text", "") for part in content or []
                   if isinstance(part, dict))


def clock(started):
    return round(time.monotonic() - started, 1)


async def run(question=QUESTION, mode="parallel", query_fn=query):
    started = time.monotonic()
    spawns = {}   # coordinator reply id -> its spawn calls
    briefs = {}   # spawn call id -> subagent name
    prompts = {}  # subagent name -> the brief it was given
    sent = {}     # spawn call id -> seconds after the start
    returned = {}  # spawn call id -> seconds after the start
    found, result, written = [], None, ""
    checks = {}   # verify_fact call id -> its input and result
    async for msg in query_fn(prompt=question,
                              options=build_options(mode)):
        if isinstance(msg, AssistantMessage):
            if msg.parent_tool_use_id:
                for block in msg.content:  # lesson 20
                    if (isinstance(block, ToolUseBlock)
                            and block.name == verify.TOOL_NAME):
                        checks[block.id] = dict(block.input)
                continue  # a subagent talking, not the coordinator
            for block in msg.content:
                if (isinstance(block, ToolUseBlock)
                        and block.name in SPAWN_TOOLS):
                    reply = msg.message_id or id(msg)
                    spawns.setdefault(reply, []).append(block.id)
                    briefs[block.id] = block.input.get(
                        "subagent_type", "?")
                    sent[block.id] = clock(started)
                    prompts[briefs[block.id]] = block.input.get(
                        "prompt", "")
        elif isinstance(msg, UserMessage) and isinstance(
                msg.content, list):
            for block in msg.content:
                if (isinstance(block, ToolResultBlock)
                        and block.tool_use_id in checks):
                    checks[block.tool_use_id]["result"] = (
                        "error" if block.is_error
                        else text_of(block.content))
                if (isinstance(block, ToolResultBlock)
                        and block.tool_use_id in briefs):
                    agent = briefs[block.tool_use_id]
                    if agent == WRITER:  # the answer, not findings
                        written = text_of(block.content)
                        continue
                    returned[block.tool_use_id] = clock(started)
                    items = findings.parse(
                        text_of(block.content), agent)
                    found += items or [findings.unreadable(agent)]
        elif isinstance(msg, ResultMessage):
            result = msg
    kept, dropped = findings.aggregate(found, HERE)
    research = (max(returned.values())
                - min(sent[i] for i in returned)
                if returned else 0.0)
    return {
        "mode": mode,
        "seconds": clock(started),
        "research_seconds": round(research, 1),
        "spawns_per_reply": [len(c) for c in spawns.values()],
        "returned_at": [returned[i] for i in briefs
                        if i in returned],
        "briefs": prompts,
        "kept": kept,
        "dropped": dropped,
        "answer": result.result if result else written,
        "written_by_synthesis": bool(written),
        "checks": list(checks.values()),
        "cost": result.total_cost_usd if result else None,
    }


def show(run_):
    """Briefs, findings and the answer first; the numbers last,
    so they are what stays on screen when the run ends."""
    print(f"== {run_['mode']}")
    for agent, brief in run_["briefs"].items():
        print(f"brief to {agent}: {brief[:150]}...")
    print(findings.report(run_["kept"], run_["dropped"]))
    print(f"answer: {run_['answer']}")
    print()
    print(f"spawn calls per coordinator reply: "
          f"{run_['spawns_per_reply']}")
    print(f"subagent replies came back at (s): "
          f"{run_['returned_at']}")
    print(f"research phase, first spawn to last reply: "
          f"{run_['research_seconds']} s")
    print(f"findings kept: {len(run_['kept'])}, "
          f"dropped: {len(run_['dropped'])}")
    for check in run_["checks"]:  # lesson 20
        result = check.get("result", "")
        verdict = ("error" if result == "error" else
                   "supported" if '"supported": true' in result
                   else "not supported")
        print(f"verify_fact {check.get('fact')!r} in "
              f"{check.get('source')}: {verdict}")
    cost = run_["cost"]
    if cost is not None:
        print(f"cost: about {cost:.4f} dollars (as reported)")
    print(f"time: {run_['seconds']} seconds")
    print()


async def main(args):
    if "--compare" in args:
        slow = await run(mode="sequential")
        show(slow)
        fast = await run(mode="parallel")
        show(fast)
        for key, name in (("research_seconds", "research phase"),
                          ("seconds", "whole run")):
            print(f"{name}: sequential {slow[key]} s, "
                  f"parallel {fast[key]} s")
    else:
        slow = "--sequential" in args
        mode = "sequential" if slow else "parallel"
        show(await run(mode=mode))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
