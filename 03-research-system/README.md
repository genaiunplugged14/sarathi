# 03-research-system

Exam scenario: Multi-Agent Research System.

Lesson 10 builds the coordinator with two subagents in parallel. Lesson 50 adds claim-source provenance.

## What is here (module 1, part 2)

The question is about the same online store as the support agent: should it move
from a 30 day to a 60 day return window? The evidence is fake and lives in
`sources/`, so every run reads the same files and nothing goes to the web.

| File | Lesson | What it does |
|---|---|---|
| `agents.py` | 9, 10 | Two `AgentDefinition`s (`customer-researcher`, `numbers-researcher`), read-only tools each, and the coordinator's options. The coordinator never reads a file itself. |
| `coordinator.py` | 10 | Runs the coordinator on the Agent SDK. Counts spawn calls per coordinator reply, collects each subagent's findings, aggregates them, times the research phase. |
| `findings.py` | 9, 10 | Structured findings `{claim, source, date}`: parse, drop what has no claim, no source or a source file that is not on disk, merge repeats. |
| `replay.py`, `demo.py` | 10 | The real coordinator code on replayed SDK messages, both modes. Free. |
| `test_research_system.py` | 10 | 19 tests. No key, no Claude Code call. |
| `sources/` | 10 | Three customer files and two number files. Fake data. |

```bash
uv run python 03-research-system/demo.py                 # free, replayed
uv run python -m unittest discover -s 03-research-system
uv run python 03-research-system/coordinator.py          # live, parallel
uv run python 03-research-system/coordinator.py --compare
```

`--compare` runs the same brief twice, sequential first, then parallel, and prints
the research phase (first spawn to last subagent reply) and the whole run for
both. Times move from run to run, so run it more than once before you believe a
number.

## What the live run needs

The Agent SDK drives Claude Code. It signs in the way your Claude Code does, or
with `ANTHROPIC_API_KEY` if you set one in your terminal (lesson 4). Nothing in
this folder holds a key. `setting_sources=[]` keeps your own Claude Code settings,
plugins and CLAUDE.md files out of the run, so it behaves the same on every machine.

## Three things the build taught (checked on claude-agent-sdk 0.2.164)

- Subagents run in the background by default today. The coordinator prompt asks
  for `run_in_background: false`, so each subagent's final message comes back as
  the Agent tool's result, the way the exam guide describes the hub.
- A subagent only gets tools the session has. With `tools=["Agent"]` alone, both
  subagents came back empty handed, so `tools` lists Read, Glob and Grep too.
- The exam guide says `allowedTools` must include "Task". Today the tool is
  `Agent` (Task still works as a name). Leaving it out of `allowed_tools` did not
  stop spawning; leaving it out of `tools` did.
