"""Sarathi v1, part 2: the coordinator and its two subagents.

The research question is about the same online store as the
support agent: should it move from a 30 day to a 60 day return
window? The evidence is fake, in sources/, so every run reads
the same files and nothing goes to the web.
"""
import pathlib

from claude_agent_sdk import AgentDefinition, ClaudeAgentOptions

HERE = pathlib.Path(__file__).parent
MODEL = "haiku"  # Claude Haiku 5.5, as in lesson 7
SPAWN_TOOLS = {"Agent", "Task"}  # Task is the guide's name
TOOLS = ["Agent", "Read", "Glob", "Grep"]

FINDINGS = (
    "Reply with only a JSON list, no other text. Each item is "
    '{"claim": "...", "source": "<path of the file you read>", '
    '"date": "<the date written in that file>"}. '
    "A claim with no source does not count.")

AGENTS = {
    "customer-researcher": AgentDefinition(
        description="Finds what customers say: the survey, the "
                    "support tickets and competitor policies.",
        prompt="You research customer evidence. Read only the "
               "folder named in your brief. " + FINDINGS,
        tools=["Read", "Glob", "Grep"],
        model="haiku"),
    "numbers-researcher": AgentDefinition(
        description="Finds what the numbers say: orders, returns "
                    "and what a return costs.",
        prompt="You research the store's numbers. Read only the "
               "folder named in your brief. " + FINDINGS,
        tools=["Read", "Glob", "Grep"],
        model="haiku"),
}

SPAWN = {
    "parallel": "Call both subagents in the same response, so "
                "they run at the same time.",
    "sequential": "Call one subagent and wait for its reply "
                  "before you call the other.",
}


def coordinator_prompt(mode):
    return (
        "You coordinate a research brief. You never read files "
        "yourself. Split the question into two subtopics: what "
        "customers say (folder sources/customers) and what the "
        "numbers say (folder sources/numbers). Give each one to "
        "its subagent. A subagent sees nothing of this chat, so "
        "its prompt must carry the question, its subtopic, its "
        "folder and the reply format. Set run_in_background to "
        "false on every call, because you need the replies "
        "before you answer. " + SPAWN[mode] + " If a "
        "subagent returns no findings, brief it once more. Then "
        "answer the question in five sentences or fewer, with "
        "the source file after every claim, and say what the "
        "evidence does not cover.")


def build_options(mode="parallel"):
    return ClaudeAgentOptions(
        system_prompt=coordinator_prompt(mode),
        agents=AGENTS,
        tools=TOOLS,  # what exists in this session at all
        allowed_tools=TOOLS,  # what runs without asking
        model=MODEL,
        cwd=str(HERE),
        setting_sources=[],  # ignore your own settings and plugins
        max_turns=12,  # a fuse, not the switch
    )
