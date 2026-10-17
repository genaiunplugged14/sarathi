# 01-support-agent

Exam scenario: Customer Support Resolution Agent.

Lesson 7 builds the loop on stop_reason and the refund gate. Lesson 9 runs the same hooks on the Agent SDK. Lesson 20 gives it MCP tools with structured errors. Lesson 50 adds case facts and escalation criteria.

## What is here (module 1, part 1)

| File | Lesson | What it does |
|---|---|---|
| `tools.py` | 7 | The four scenario tools on fake data. Refunds land in a list; no money moves. |
| `agent.py` | 5, 7 | The loop: continue on `tool_use`, stop on `end_turn`, stop loudly on anything else. |
| `hooks.py` | 7 | `refund_gate` (PreToolUse), `remember_verified` and `normalize` (PostToolUse), in the Agent SDK's hook shape. |
| `naive_loops.py` | 6 | Three loops that look fine and are not: parse "done", cap at 50, check for text. |
| `replay.py` | 6, 7 | A stand-in for the API that replays hand-written replies, so a failure shows the same way every time. |
| `demo.py` | 7 | The real loop on three replayed cases: refund, skip-verify, over-limit. |
| `test_support_agent.py` | 6, 7 | 19 tests. No API key needed. |
| `sdk_agent.py` | 9 | The same tools and the same three hooks on the Agent SDK: the tools become an in-process MCP server, the hooks register through `HookMatcher` with a one-line async wrapper. No loop of its own. |
| `test_sdk_agent.py` | 9 | 4 tests: the gate under the SDK's `mcp__support__process_refund` name, and the hooks reading MCP text results. |

```bash
uv run python 01-support-agent/naive_loops.py     # lesson 6, free
uv run python 01-support-agent/demo.py            # lesson 7, free
uv run python -m unittest discover -s 01-support-agent
uv run python 01-support-agent/agent.py           # live, needs ANTHROPIC_API_KEY
uv run python 01-support-agent/sdk_agent.py       # live, lesson 9, signs in like Claude Code
```

The live run uses Claude Haiku 5.5 and prints its own token count and cost on the last line.
