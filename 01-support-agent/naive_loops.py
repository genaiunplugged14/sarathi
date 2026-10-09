"""Lesson 6: three loops that look fine and are not.

Run: uv run python 01-support-agent/naive_loops.py
Each loop runs on the same replayed replies (see replay.py),
so each one breaks the same way every time.
"""
import json

import tools
from replay import ASK, REFUND, ReplayClient


def run_tools(response):
    results = []
    for block in response.content:
        if block.type == "tool_use":
            output = tools.run_tool(block.name, block.input)
            results.append({"type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(output)})
    return results


def text_of(response):
    return "".join(b.text for b in response.content
                   if b.type == "text")


def call(client, messages):
    return client.messages.create(
        model="claude-haiku-5-5", max_tokens=1024,
        tools=tools.TOOLS, messages=messages)


def loop_parse_done(client, question):
    """Naive 1: stop when the reply says 'done'."""
    messages = [{"role": "user", "content": question}]
    while True:
        response = call(client, messages)
        messages.append(
            {"role": "assistant", "content": response.content})
        if "done" in text_of(response).lower():
            return text_of(response)
        messages.append(
            {"role": "user", "content": run_tools(response)})


def loop_capped(client, question, cap=50):
    """Naive 2: run until the cap. The cap is the only stop."""
    messages = [{"role": "user", "content": question}]
    for turn in range(cap):
        response = call(client, messages)
        messages.append(
            {"role": "assistant", "content": response.content})
        results = run_tools(response)
        messages.append(
            {"role": "user", "content": results or "Continue."})
    return text_of(response)


def loop_check_text(client, question):
    """Naive 3: stop as soon as the reply has any text."""
    messages = [{"role": "user", "content": question}]
    while True:
        response = call(client, messages)
        messages.append(
            {"role": "assistant", "content": response.content})
        if text_of(response):
            return text_of(response)
        messages.append(
            {"role": "user", "content": run_tools(response)})


def show(name, loop, **options):
    tools.reset()
    client = ReplayClient(REFUND, repeat=True)
    answer = loop(client, ASK, **options)
    print(f"{name}")
    print(f"  calls to the model: {client.calls}")
    print(f"  refunds issued:     {len(tools.REFUNDS)}")
    print(f"  customer is told:   {answer!r}")


if __name__ == "__main__":
    show("parse 'done'", loop_parse_done)
    show("cap at 50", loop_capped)
    show("cap at 2", loop_capped, cap=2)
    show("check for text", loop_check_text)
