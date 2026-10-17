"""Tests for lesson 9: the lesson 7 hooks under the Agent SDK.

No API key, no Claude Code call. The callbacks are called the way
the SDK calls them, with the SDK's own MCP tool names.
"""
import asyncio
import json
import unittest

import hooks
import sdk_agent


def call(hook, event):
    return asyncio.run(sdk_agent.sdk_hook(hook)(event, "toolu_1", {}))


class SdkHooks(unittest.TestCase):
    def setUp(self):
        hooks.reset()

    def test_the_gate_denies_under_the_mcp_name(self):
        event = {"hook_event_name": "PreToolUse",
                 "tool_name": "mcp__support__process_refund",
                 "tool_input": {"customer_id": "C-1001",
                                "order_id": "O-5001",
                                "amount": 89.0}}
        out = call(hooks.refund_gate, event)["hookSpecificOutput"]
        self.assertEqual(out["permissionDecision"], "deny")

    def test_verified_is_read_from_the_mcp_text_blocks(self):
        record = {"customer_id": "C-1001", "verified": True}
        event = {"hook_event_name": "PostToolUse",
                 "tool_name": "mcp__support__get_customer",
                 "tool_input": {"email": "asha@example.com"},
                 "tool_response": [{"type": "text",
                                    "text": json.dumps(record)}]}
        call(hooks.remember_verified, event)
        self.assertIn("C-1001", hooks.verified)

    def test_every_hook_is_registered(self):
        options = sdk_agent.build_options()
        self.assertEqual(len(options.hooks["PreToolUse"][0].hooks), 1)
        self.assertEqual(len(options.hooks["PostToolUse"][0].hooks), 2)

    def test_only_our_four_tools_run(self):
        options = sdk_agent.build_options()
        self.assertEqual(options.tools, [])
        self.assertIn("mcp__support__process_refund",
                      options.allowed_tools)


if __name__ == "__main__":
    unittest.main()
