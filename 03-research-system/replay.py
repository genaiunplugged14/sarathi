"""A stand-in for the Agent SDK's query() that replays messages.

Nothing here calls Claude. Every message is built from the SDK's
own types, in the order a live run sends them, so the coordinator
code cannot tell the difference. Times read zero on a replay.
"""
import json

from claude_agent_sdk import (AssistantMessage, ResultMessage,
                              TextBlock, ToolResultBlock,
                              ToolUseBlock, UserMessage)

from coordinator import QUESTION

FORMAT = ('Reply with only a JSON list of {"claim", "source", '
          '"date"}.')
BRIEF = {
    "customer-researcher": (
        f"Question: {QUESTION} Your subtopic: what customers "
        "say. Read the files in sources/customers. " + FORMAT),
    "numbers-researcher": (
        f"Question: {QUESTION} Your subtopic: what the numbers "
        "say. Read the files in sources/numbers. " + FORMAT),
}

CUSTOMER_FINDINGS = [
    {"claim": "38 percent of 412 customers would buy more "
              "electronics with a 60 day window",
     "source": "sources/customers/survey-2026-09.md",
     "date": "2026-09-12"},
    {"claim": "96 returns after day 30 were refused in Q3, "
              "61 of them monitors or headphones",
     "source": "sources/customers/support-tickets-2026-q3.md",
     "date": "2026-10-01"},
    {"claim": "Store B moved from 30 to 60 days in March 2026",
     "source": "sources/customers/competitors-2026.md",
     "date": "2026-08-20"},
    {"claim": "Customers love long return windows",
     "source": "", "date": ""},
    {"claim": "Reviews ask for 90 days",
     "source": "sources/customers/reviews-2026.md",
     "date": "2026-09-01"},
]

NUMBERS_FINDINGS = [
    {"claim": "The return rate held between 6.0 and 6.5 percent "
              "from April to September",
     "source": "sources/numbers/returns-2026.csv",
     "date": "2026-09"},
    {"claim": "Handling one return costs 11 dollars on average",
     "source": "sources/numbers/return-costs-2026.md",
     "date": "2026-09-30"},
    {"claim": "A 60 day window would add about 40 returns a month",
     "source": "sources/numbers/return-costs-2026.md",
     "date": "2026-09-30"},
]

ANSWER = ("For: 38 percent of customers would buy more "
          "(sources/customers/survey-2026-09.md). Against: about "
          "40 more returns a month at 11 dollars each "
          "(sources/numbers/return-costs-2026.md). Not covered: "
          "whether the extra sales outweigh the extra returns.")


def spawn(call_id, agent):
    return ToolUseBlock(id=call_id, name="Agent", input={
        "subagent_type": agent, "description": f"Research {agent}",
        "prompt": BRIEF[agent], "run_in_background": False})


def coordinator_says(reply_id, *blocks):
    return AssistantMessage(content=list(blocks),
                            model="claude-haiku-5-5",
                            message_id=reply_id)


def subagent_says(call_id, words):
    return AssistantMessage(content=[TextBlock(text=words)],
                            model="claude-haiku-5-5",
                            parent_tool_use_id=call_id,
                            message_id=f"sub-{call_id}")


def hand_back(call_id, items):
    words = ("[Subagent hand-back] The report follows:\n```json\n"
             + json.dumps(items, indent=2) + "\n```")
    return UserMessage(content=[ToolResultBlock(
        tool_use_id=call_id,
        content=[{"type": "text", "text": words}])])


def done(turns):
    return ResultMessage(subtype="success", duration_ms=0,
                         duration_api_ms=0, is_error=False,
                         num_turns=turns, session_id="replay",
                         total_cost_usd=0.0, result=ANSWER)


# Both spawn calls in ONE coordinator reply.
PARALLEL = [
    coordinator_says("reply-1", spawn("s1", "customer-researcher"),
                     spawn("s2", "numbers-researcher")),
    subagent_says("s1", "Reading sources/customers now."),
    subagent_says("s2", "Reading sources/numbers now."),
    hand_back("s2", NUMBERS_FINDINGS),
    hand_back("s1", CUSTOMER_FINDINGS),
    coordinator_says("reply-2", TextBlock(text=ANSWER)),
    done(2),
]

# One spawn call per reply: the second waits for the first.
SEQUENTIAL = [
    coordinator_says("reply-1", spawn("s1", "customer-researcher")),
    subagent_says("s1", "Reading sources/customers now."),
    hand_back("s1", CUSTOMER_FINDINGS),
    coordinator_says("reply-2", spawn("s2", "numbers-researcher")),
    subagent_says("s2", "Reading sources/numbers now."),
    hand_back("s2", NUMBERS_FINDINGS),
    coordinator_says("reply-3", TextBlock(text=ANSWER)),
    done(3),
]


class Replay:
    """Call it like query(prompt=..., options=...)."""

    def __init__(self, script):
        self.script = script
        self.options = None

    async def __call__(self, prompt, options):
        self.prompt, self.options = prompt, options
        for message in self.script:
            yield message
