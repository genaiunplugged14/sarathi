"""Lesson 20: verify_fact, the synthesis agent's one tool.

A scoped cross-role tool (lesson 17). The synthesis agent may
check one short fact, a number, a date or a name, against the
source file a finding came from. Anything deeper goes back
through the coordinator. Failures are structured (lesson 16).
"""
import json
import pathlib
import re

from claude_agent_sdk import create_sdk_mcp_server, tool

SOURCES = pathlib.Path(__file__).parent / "sources"

DESCRIPTION = (
    "Check one short fact against one source file. Input: the "
    "fact, a number, date or name of at most 60 characters, "
    "and the source path a finding gave, like "
    "sources/numbers/return-costs-2026.md. Use it while "
    "writing, for example to check '11 dollars' before you "
    "repeat it. A fact with numbers is supported when one "
    "line holds all its numbers; one without, when one line "
    "holds all its longer words. Never use it to search for "
    "new evidence. "
    "Returns supported true with the line, or supported false "
    "when the file does not contain the fact, which is not an "
    "error.")


class Failure(Exception):
    def __init__(self, category, message):
        super().__init__(message)
        self.error = {"errorCategory": category,
                      "isRetryable": False, "message": message}


def check(fact, source):
    fact = fact.strip()
    if not fact or len(fact) > 60:
        raise Failure("validation", "The fact must be 1 to 60 "
                      "characters. Check one fact at a time.")
    path = (SOURCES.parent / source).resolve()
    if SOURCES.resolve() not in path.parents:
        raise Failure("permission", f"{source} is outside the "
                      "sources folder. Only sources can be read.")
    if not path.is_file():
        raise Failure("validation", f"There is no file {source}. "
                      "Use the path the finding gave.")
    numbers = re.findall(r"\d+(?:\.\d+)?", fact)
    words = [w for w in re.findall(r"[a-z]+", fact.lower())
             if len(w) > 3]
    lines = path.read_text().splitlines()
    for number, line in enumerate(lines, start=1):
        if numbers:
            found = set(re.findall(r"\d+(?:\.\d+)?", line))
            hit = all(n in found for n in numbers)
        else:
            hit = bool(words) and all(w in line.lower()
                                      for w in words)
        if hit:
            return {"supported": True, "source": source,
                    "line": number, "text": line.strip()}
    return {"supported": False, "source": source}


@tool("verify_fact", DESCRIPTION, {"fact": str, "source": str})
async def verify_fact(args):
    try:
        result = check(args["fact"], args["source"])
    except Failure as f:
        return {"content": [{"type": "text",
                             "text": json.dumps(f.error)}],
                "is_error": True}
    return {"content": [{"type": "text",
                         "text": json.dumps(result)}]}


SERVER = create_sdk_mcp_server("research", tools=[verify_fact])
TOOL_NAME = "mcp__research__verify_fact"
