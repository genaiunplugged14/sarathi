"""Run the real loop on replayed replies. No API key, no cost.

uv run python 01-support-agent/demo.py            all three
uv run python 01-support-agent/demo.py refund     just one
"""
import json
import sys

import tools
from agent import run_agent
from replay import (ASK, OVER_LIMIT, REFUND, SKIP_VERIFY,
                    ReplayClient)

CASES = {"refund": REFUND, "skip-verify": SKIP_VERIFY,
         "over-limit": OVER_LIMIT}


def show(name):
    tools.reset()
    print(f"== {name}")
    answer = run_agent(ReplayClient(CASES[name]), ASK)
    print(f"answer:   {answer}")
    print(f"refunds:  {json.dumps(tools.REFUNDS)}")
    print(f"handoffs: {json.dumps(tools.HANDOFFS, indent=2)}")
    print()


if __name__ == "__main__":
    for name in sys.argv[1:] or CASES:
        show(name)
