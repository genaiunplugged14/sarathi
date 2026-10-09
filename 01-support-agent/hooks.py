"""Sarathi's hooks, in the same shape the Agent SDK uses.

Each hook takes the event the SDK would pass (tool_name,
tool_input, and tool_response after the tool ran) and returns
the dict the SDK expects back. Lesson 9 registers these same
functions with the Agent SDK.
"""
from datetime import datetime, timezone

REFUND_LIMIT = 500
STATUS = {1: "placed", 2: "shipped", 3: "delivered", 4: "returned"}
verified = set()  # customer ids that get_customer has verified


def reset():
    verified.clear()


def named(event, tool):
    """True for tool, and for the SDK's mcp__server__tool form."""
    return event["tool_name"].split("__")[-1] == tool


def deny(reason):
    return {"hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": reason}}


def refund_gate(event):
    """PreToolUse: no refund before verification, none over 500."""
    if not named(event, "process_refund"):
        return {}
    args = event["tool_input"]
    if args["customer_id"] not in verified:
        return deny("Customer is not verified. "
                    "Call get_customer first.")
    if args["amount"] > REFUND_LIMIT:
        return deny("Refunds over 500 dollars need a human. "
                    "Call escalate_to_human with a summary.")
    return {}


def remember_verified(event):
    """PostToolUse: note every customer get_customer verified."""
    result = event["tool_response"]
    if not named(event, "get_customer"):
        return {}
    if result.get("verified"):
        verified.add(result["customer_id"])
    return {}


def normalize(event):
    """PostToolUse: one date format, and status as a word."""
    result = dict(event["tool_response"])
    if isinstance(result.get("placed_at"), int):
        when = datetime.fromtimestamp(
            result["placed_at"], timezone.utc)
        result["placed_at"] = when.strftime("%Y-%m-%d")
    if isinstance(result.get("status"), int):
        result["status"] = STATUS[result["status"]]
    if "member_since" in result:
        result["member_since"] = result["member_since"][:10]
    return {"hookSpecificOutput": {
        "hookEventName": "PostToolUse",
        "updatedToolOutput": result}}
