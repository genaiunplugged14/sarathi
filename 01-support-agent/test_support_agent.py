"""Tests for lessons 6 and 7. No API key needed, nothing billed.

uv run python -m unittest discover -s 01-support-agent -v
"""
import json
import unittest

import agent
import hooks
import naive_loops
import tools
from replay import (ASK, OVER_LIMIT, REFUND, SKIP_VERIFY,
                    ReplayClient, reply, text)


def quiet(*args, **kwargs):
    pass


agent.print = quiet  # keep the test output clean


class NaiveLoops(unittest.TestCase):
    def setUp(self):
        tools.reset()

    def test_parse_done_stops_before_the_refund(self):
        client = ReplayClient(REFUND, repeat=True)
        naive_loops.loop_parse_done(client, ASK)
        self.assertEqual(client.calls, 2)
        self.assertEqual(tools.REFUNDS, [])

    def test_cap_at_50_keeps_calling_after_the_answer(self):
        client = ReplayClient(REFUND, repeat=True)
        naive_loops.loop_capped(client, ASK)
        self.assertEqual(client.calls, 50)
        self.assertEqual(len(tools.REFUNDS), 1)

    def test_cap_at_2_dies_mid_task(self):
        client = ReplayClient(REFUND, repeat=True)
        naive_loops.loop_capped(client, ASK, cap=2)
        self.assertEqual(tools.REFUNDS, [])

    def test_check_for_text_stops_on_the_first_reply(self):
        client = ReplayClient(REFUND, repeat=True)
        answer = naive_loops.loop_check_text(client, ASK)
        self.assertEqual(client.calls, 1)
        self.assertEqual(answer, "Let me look up your account first.")


class RealLoop(unittest.TestCase):
    def setUp(self):
        tools.reset()

    def test_refund_runs_to_end_turn(self):
        client = ReplayClient(REFUND)
        answer = agent.run_agent(client, ASK)
        self.assertEqual(client.calls, 4)
        self.assertIn("R-0001", answer)
        self.assertEqual(len(tools.REFUNDS), 1)

    def test_history_alternates_and_results_follow_their_call(self):
        client = ReplayClient(REFUND)
        agent.run_agent(client, ASK)
        messages = client.last_request["messages"]
        roles = [m["role"] for m in messages]
        self.assertEqual(roles, ["user", "assistant"] * 4)
        for i in range(1, len(messages) - 1, 2):
            calls = [b.id for b in messages[i]["content"]
                     if b.type == "tool_use"]
            results = [r["tool_use_id"] for r in messages[i + 1]
                       ["content"]]
            self.assertEqual(calls, results)

    def test_gate_blocks_until_verified(self):
        agent.run_agent(ReplayClient(SKIP_VERIFY), ASK)
        self.assertEqual(len(tools.REFUNDS), 1)  # only after verify

    def test_blocked_call_returns_an_error_result(self):
        client = ReplayClient(SKIP_VERIFY)
        agent.run_agent(client, ASK)
        blocked = client.last_request["messages"][4]["content"][0]
        self.assertTrue(blocked["is_error"])
        self.assertIn("not verified", blocked["content"])

    def test_over_limit_escalates_with_a_full_handoff(self):
        agent.run_agent(ReplayClient(OVER_LIMIT), ASK)
        self.assertEqual(tools.REFUNDS, [])
        self.assertEqual(set(tools.HANDOFFS[0]),
                         {"customer_id", "root_cause",
                          "refund_amount", "recommended_action"})

    def test_unhandled_stop_reason_stops_loudly(self):
        client = ReplayClient([reply("max_tokens", text("Your re"))])
        with self.assertRaises(RuntimeError):
            agent.run_agent(client, ASK)

    def test_the_fuse_blows_instead_of_looping_forever(self):
        looping = REFUND[0]
        client = ReplayClient([looping], repeat=True)
        with self.assertRaises(RuntimeError):
            agent.run_agent(client, ASK)
        self.assertEqual(client.calls, agent.MAX_TURNS)


class Hooks(unittest.TestCase):
    def setUp(self):
        hooks.reset()

    def refund(self, amount):
        return {"tool_name": "process_refund",
                "tool_input": {"customer_id": "C-1001",
                               "order_id": "O-5001",
                               "amount": amount}}

    def decision(self, out):
        return out.get("hookSpecificOutput", {}).get(
            "permissionDecision")

    def test_unverified_refund_is_denied(self):
        out = hooks.refund_gate(self.refund(89.0))
        self.assertEqual(self.decision(out), "deny")

    def test_verified_refund_under_the_line_passes(self):
        hooks.verified.add("C-1001")
        self.assertEqual(hooks.refund_gate(self.refund(89.0)), {})

    def test_over_500_is_denied_even_when_verified(self):
        hooks.verified.add("C-1001")
        out = hooks.refund_gate(self.refund(500.01))
        self.assertEqual(self.decision(out), "deny")

    def test_gate_also_fires_on_the_sdk_mcp_name(self):
        event = self.refund(89.0)
        event["tool_name"] = "mcp__support__process_refund"
        self.assertEqual(
            self.decision(hooks.refund_gate(event)), "deny")

    def test_other_tools_pass_the_gate(self):
        event = {"tool_name": "lookup_order",
                 "tool_input": {"order_id": "O-5001"}}
        self.assertEqual(hooks.refund_gate(event), {})

    def test_normalize_dates_and_status(self):
        event = {"tool_name": "lookup_order", "tool_input": {},
                 "tool_response": tools.lookup_order("O-5001")}
        out = hooks.normalize(event)["hookSpecificOutput"]
        result = out["updatedToolOutput"]
        self.assertEqual(result["placed_at"], "2026-09-21")
        self.assertEqual(result["status"], "delivered")

    def test_output_keys_match_the_agent_sdk_types(self):
        from claude_agent_sdk.types import (
            PostToolUseHookSpecificOutput,
            PreToolUseHookSpecificOutput)
        pre = hooks.deny("x")["hookSpecificOutput"]
        post = hooks.normalize({"tool_name": "t", "tool_input": {},
                                "tool_response": {}})
        post = post["hookSpecificOutput"]
        self.assertLessEqual(
            set(pre), set(PreToolUseHookSpecificOutput.__annotations__))
        self.assertLessEqual(
            set(post), set(PostToolUseHookSpecificOutput.__annotations__))


class RealClientOverFakeHttp(unittest.TestCase):
    """The real anthropic client, with HTTP answered locally."""

    def test_live_request_shape_round_trips(self):
        import anthropic
        import httpx2

        replies = [
            {"stop_reason": "tool_use", "content": [
                {"type": "tool_use", "id": "toolu_1",
                 "name": "get_customer",
                 "input": {"email": "asha@example.com"}}]},
            {"stop_reason": "end_turn", "content": [
                {"type": "text", "text": "You are verified."}]},
        ]
        seen = []

        def handler(request):
            body = json.loads(request.content)
            seen.append(body)
            r = replies[len(seen) - 1]
            return httpx2.Response(200, json={
                "id": f"msg_{len(seen)}", "type": "message",
                "role": "assistant", "model": body["model"],
                "content": r["content"],
                "stop_reason": r["stop_reason"],
                "stop_sequence": None,
                "usage": {"input_tokens": 900, "output_tokens": 60}})

        client = anthropic.Anthropic(
            api_key="test-key-not-real",
            http_client=httpx2.Client(
                transport=httpx2.MockTransport(handler)))
        tools.reset()
        answer = agent.run_agent(client, ASK)
        self.assertEqual(answer, "You are verified.")
        second = seen[1]["messages"]
        self.assertEqual(second[1]["content"][0]["type"], "tool_use")
        result = second[2]["content"][0]
        self.assertEqual(result["tool_use_id"], "toolu_1")
        self.assertEqual(seen[0]["model"], "claude-haiku-5-5")


if __name__ == "__main__":
    unittest.main()
