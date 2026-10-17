"""Run the real coordinator code on replayed messages.

uv run python 03-research-system/demo.py              both modes
uv run python 03-research-system/demo.py parallel     just one

No model is called and nothing is billed, so every time reads
zero. The measured times come from coordinator.py --compare.
"""
import asyncio
import sys

from coordinator import run, show
from replay import PARALLEL, SEQUENTIAL, Replay

CASES = {"parallel": PARALLEL, "sequential": SEQUENTIAL}


async def main(names):
    for name in names or CASES:
        show(await run(mode=name, query_fn=Replay(CASES[name])))


if __name__ == "__main__":
    asyncio.run(main(sys.argv[1:]))
