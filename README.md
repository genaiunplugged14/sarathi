# Sarathi

Sarathi means the charioteer. It is the one folder you build in across the
**Claude Certified Architect, Foundations** course by Dheeraj Sharma
(GenAI Unplugged). Six folders, one per exam scenario, and every build in the
course lands in one of them. By the end, the exam's own six scenarios sit on
your disk as working code.

| Folder | Exam scenario | Built in |
|---|---|---|
| `01-support-agent/` | Customer Support Resolution Agent | module 1 (loop, gate), 2 (tools, errors), 5 (reliability) |
| `02-claude-code/` | Code Generation with Claude Code | module 3 (CLAUDE.md, rules, skills, plan mode) |
| `03-research-system/` | Multi-Agent Research System | module 1 (coordinator, subagents), 5 (provenance) |
| `04-dev-productivity/` | Developer Productivity with Claude | module 2 (built-in tools, MCP) |
| `05-ci-review/` | Claude Code for Continuous Integration | module 3 (-p, JSON schema), 4 (criteria, passes) |
| `06-extraction/` | Structured Data Extraction | module 4 (schema, retry, batch), 5 (confidence) |

The folders are empty on purpose. Each one fills in the lesson that builds it.

## Setup (lesson 4)

You need Python 3.10 or newer, [uv](https://docs.astral.sh/uv/) (or pip with a
virtual environment), [Claude Code](https://code.claude.com/docs/en/setup),
an `ANTHROPIC_API_KEY` from [platform.claude.com](https://platform.claude.com)
and Node.js (many community MCP servers run on it).

```bash
git clone https://github.com/genaiunplugged14/sarathi.git
cd sarathi
uv sync
uv run python check_setup.py
```

With pip instead of uv:

```bash
python3 -m venv .venv && source .venv/bin/activate
# Windows: .venv\Scripts\activate
pip install "claude-agent-sdk>=0.2.164,<0.3" "anthropic>=1.12,<2"
python check_setup.py
```

The checker prints six lines, one per thing lesson 4 sets up, and says what
to run for any line that fails. It never prints your key.

The two packages are pinned on purpose. The Agent SDK was renamed once already
(Claude Code SDK to Claude Agent SDK) and every sample written before the
rename broke. A loose version gives you no warning.

## Sarathi v2: the MCP server (lesson 20)

`.mcp.json` in this folder starts `01-support-agent/mcp_server.py` for Claude
Code (project scope, lesson 18). Open Claude Code here and it asks once to
trust the project server. The store key is fake: any value lets refunds run.

```bash
export SARATHI_STORE_KEY=any-value      # Windows: set SARATHI_STORE_KEY=any-value
export SARATHI_FLAKY_ORDERS=1           # optional: first lookup times out
claude
```

Without a key the server still starts, and a refund comes back as a permission
error, which is the point. Tests for every module so far, with no key and no bill:

```bash
uv run python -m unittest discover -s 01-support-agent
uv run python -m unittest discover -s 03-research-system
uv run python -m unittest discover -s 04-dev-productivity -t 04-dev-productivity
```

## Checkpoints

Every module ships a checkpoint zip with this folder exactly as the module
leaves it, plus a pinned package list and this same setup check. If a build
breaks on your machine, unzip the checkpoint and carry on from there.

## The course

Every command in every lesson, in order, with the Windows variants, is in the
course preparation document that ships with the course. The video and the
lesson pages are published after the exam is cleared.

## License

MIT. See `LICENSE`.
