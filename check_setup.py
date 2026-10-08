"""Is this machine ready for the Claude Architect certification course?

    uv run python check_setup.py        (or: python check_setup.py)

Six checks, one per thing lesson 4 sets up, in the lesson's order. Prints one
line per check and exits 0 only when all six pass. Never prints a key or a
token. The Claude Code sign-in is checked silently through `claude auth
status`; the lesson never asks you to run that by hand.
"""
from __future__ import annotations

import importlib
import json
import os
import shutil
import subprocess
import sys
from importlib import metadata

WIN = sys.platform.startswith("win")


def run(cmd: list[str]) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=30, shell=WIN)
        return p.returncode, (p.stdout or p.stderr).strip()
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return 127, ""


def version_of(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "?"


def main() -> int:
    results: list[tuple[str, bool, str]] = []

    # 1. Python
    ok = sys.version_info >= (3, 10)
    results.append(("1. Python 3.10 or newer", ok,
                    f"you have {sys.version.split()[0]}" if ok else
                    f"you have {sys.version.split()[0]}: get 3.10+ from python.org"))

    # 2. uv, or an active virtual environment for the pip path
    has_uv = shutil.which("uv") is not None
    in_venv = sys.prefix != getattr(sys, "base_prefix", sys.prefix)
    results.append(("2. uv, or a venv for pip", has_uv or in_venv,
                    "uv found" if has_uv else "venv active" if in_venv else
                    "install uv (astral.sh/uv) or activate a venv"))

    # 3. Claude Code installed and signed in (sign-in checked silently)
    code, out = run(["claude", "--version"])
    installed = code == 0
    signed = False
    if installed:
        _, auth = run(["claude", "auth", "status"])
        try:
            signed = bool(json.loads(auth).get("loggedIn"))
        except (ValueError, AttributeError):
            signed = "loggedIn" in auth and "true" in auth
    ver = out.split()[0] if out else "?"
    note = ((f"{ver}, signed in" if signed else f"{ver}, not signed in: run claude, then /login")
            if installed else "claude not found: see lesson 4 install line, then open a new terminal")
    results.append(("3. Claude Code, signed in", installed and signed, note))

    # 4. API key
    key = bool(os.environ.get("ANTHROPIC_API_KEY"))
    results.append(("4. ANTHROPIC_API_KEY set", key,
                    "set" if key else "export ANTHROPIC_API_KEY=... (platform.claude.com, 5 dollars is plenty)"))

    # 5. Node
    code, out = run(["node", "--version"])
    results.append(("5. Node.js for MCP servers", code == 0,
                    out if out else "get Node from nodejs.org, install, open a new terminal"))

    # 6. The two packages
    missing = []
    for mod, pkg in (("claude_agent_sdk", "claude-agent-sdk"), ("anthropic", "anthropic")):
        try:
            importlib.import_module(mod)
        except Exception:  # noqa: BLE001
            missing.append(pkg)
    results.append(("6. claude-agent-sdk and anthropic", not missing,
                    f"{version_of('claude-agent-sdk')} and {version_of('anthropic')}"
                    if not missing else f"missing {', '.join(missing)}: run uv sync (or the pip line)"))

    width = max(len(r[0]) for r in results)
    for name, passed, note in results:
        print(f"{'PASS' if passed else 'FAIL'}  {name.ljust(width)}  {note}")
    failed = [r for r in results if not r[1]]
    print()
    print("Ready. See you in lesson 5." if not failed else f"{len(failed)} to fix. Each line above says how.")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
