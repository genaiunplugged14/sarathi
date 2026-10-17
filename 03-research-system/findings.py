"""Structured findings: parse what a subagent returns, check it,
and put the findings of both subagents together.

A finding is {"claim", "source", "date"}. The code adds "agent",
the subagent that found it. A finding with no claim, no source,
or a source file that is not on disk is dropped, and the report
says so. Lesson 50 goes further and checks the claim against the
words in the file.
"""
import json
import pathlib

REQUIRED = ("claim", "source")


def parse(text, agent):
    """Pull the JSON list out of a subagent's final message.

    The list may sit after other text, so try every [ until one
    decodes to a list.
    """
    decoder = json.JSONDecoder()
    for start, char in enumerate(text):
        if char != "[":
            continue
        try:
            items, _ = decoder.raw_decode(text, start)
        except json.JSONDecodeError:
            continue
        if isinstance(items, list) and items and all(
                isinstance(item, dict) for item in items):
            return [{**item, "agent": agent} for item in items]
    return []


def where(source, root):
    """The source as a path under root, or None if it is not."""
    path = pathlib.Path(str(source))
    if not path.is_absolute():
        path = root / path
    try:
        return path.resolve().relative_to(root.resolve())
    except ValueError:
        return None


def unreadable(agent):
    """Stands in for a reply that held no list of findings."""
    return {"agent": agent, "unreadable": True}


def problem(finding, root):
    """Why a finding cannot be used, or None if it can."""
    if finding.get("unreadable"):
        return "the reply held no JSON list of findings"
    for field in REQUIRED:
        if not str(finding.get(field) or "").strip():
            return f"no {field}"
    rel = where(finding["source"], root)
    if rel is None or not (root / rel).is_file():
        return f"source not found: {finding['source']}"
    return None


def aggregate(findings, root):
    """Keep the usable findings, drop the rest, merge repeats."""
    kept, dropped, seen = [], [], {}
    for f in findings:
        why = problem(f, root)
        if why:
            dropped.append({**f, "why": why})
            continue
        f = {**f, "source": str(where(f["source"], root))}
        key = f["claim"].strip().lower()
        if key in seen:
            seen[key]["also_in"].append(f["source"])
            continue
        f["also_in"] = []
        seen[key] = f
        kept.append(f)
    return kept, dropped


def report(kept, dropped):
    lines = [f"findings kept: {len(kept)}, "
             f"dropped: {len(dropped)}"]
    for f in kept:
        lines.append(f"  [{f['agent']}] {f['claim']}")
        lines.append(f"      source: {f['source']} "
                     f"({f.get('date') or 'no date'})")
    for f in dropped:
        lines.append(f"  DROPPED [{f['agent']}] {f['why']}: "
                     f"{f.get('claim') or '(empty)'}")
    return "\n".join(lines)
