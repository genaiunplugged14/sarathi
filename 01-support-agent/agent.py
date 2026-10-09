"""Sarathi v1, part 1: the support agent loop, run on stop_reason.

Live:    uv run python 01-support-agent/agent.py "your message"
Offline: uv run python 01-support-agent/demo.py
"""
import json
import os
import sys

import hooks
import tools

MODEL = "claude-haiku-5-5"
PRICE_IN, PRICE_OUT = 0.10, 0.50  # dollars per million tokens
MAX_TURNS = 20  # a fuse, not the switch
SYSTEM = (
    "You are Sarathi, the support agent for an online store. "
    "Verify the customer with get_customer before any refund. "
    "Refunds over 500 dollars go to a human."
)
PRE = [hooks.refund_gate]
POST = [hooks.remember_verified, hooks.normalize]


def call_tool(block):
    event = {"tool_name": block.name, "tool_input": block.input}
    for hook in PRE:
        out = hook(event).get("hookSpecificOutput", {})
        if out.get("permissionDecision") == "deny":
            print(f"  BLOCKED {block.name}: "
                  f"{out['permissionDecisionReason']}")
            return out["permissionDecisionReason"], True
    event["tool_response"] = tools.run_tool(
        block.name, block.input)
    for hook in POST:
        out = hook(event).get("hookSpecificOutput", {})
        if "updatedToolOutput" in out:
            event["tool_response"] = out["updatedToolOutput"]
    result = json.dumps(event["tool_response"])
    print(f"  tool    {block.name} -> {result}")
    return result, False


def text_of(response):
    return "".join(b.text for b in response.content
                   if b.type == "text")


def run_agent(client, question):
    hooks.reset()
    messages = [{"role": "user", "content": question}]
    tokens_in = tokens_out = 0
    for turn in range(1, MAX_TURNS + 1):
        response = client.messages.create(
            model=MODEL, max_tokens=1024, system=SYSTEM,
            tools=tools.TOOLS, messages=messages)
        tokens_in += response.usage.input_tokens
        tokens_out += response.usage.output_tokens
        print(f"turn {turn}: stop_reason = {response.stop_reason}")
        messages.append(
            {"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            cost = (tokens_in * PRICE_IN
                    + tokens_out * PRICE_OUT) / 1_000_000
            print(f"cost: {tokens_in} in, {tokens_out} out, "
                  f"about {cost:.4f} dollars")
            return text_of(response)

        if response.stop_reason != "tool_use":
            raise RuntimeError(
                f"Stopped on {response.stop_reason}, not handled")

        results = []
        for block in response.content:
            if block.type == "tool_use":
                content, is_error = call_tool(block)
                results.append({"type": "tool_result",
                                "tool_use_id": block.id,
                                "content": content,
                                "is_error": is_error})
        messages.append({"role": "user", "content": results})

    raise RuntimeError(f"No answer after {MAX_TURNS} turns")


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("ANTHROPIC_API_KEY is not set. See lesson 4.")
    import anthropic
    question = " ".join(sys.argv[1:]) or (
        "Hi, I am Asha Rao, asha@example.com. My headphones "
        "from order O-5001 arrived broken. Please refund me.")
    print(run_agent(anthropic.Anthropic(), question))
