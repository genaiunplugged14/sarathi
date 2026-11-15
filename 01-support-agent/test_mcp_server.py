"""Tests for lesson 20, the MCP server. No API key, no bill.

uv run python -m unittest discover -s 01-support-agent -v
"""
import asyncio
import json
import os
import pathlib
import unittest
from unittest import mock

import mcp_server as s

HERE = pathlib.Path(__file__).parent
KEY = {"SARATHI_STORE_KEY": "not-a-real-key"}


def error_of(call, *args):
    result = call(*args)
    assert getattr(result, "is_error", False), result
    return json.loads(result.content[0].text)


class Base(unittest.TestCase):
    def setUp(self):
        s.reset()


class Descriptions(Base):
    def test_four_tools_with_long_descriptions(self):
        listed = asyncio.run(s.server.list_tools())
        self.assertEqual({t.name for t in listed},
                         {"get_customer", "lookup_order",
                          "process_refund", "escalate_to_human"})
        for t in listed:
            self.assertGreater(len(t.description), 200, t.name)

    def test_each_description_names_its_boundary(self):
        self.assertIn("get_customer first", s.LOOKUP_ORDER)
        self.assertIn("Never use it to find a customer",
                      s.LOOKUP_ORDER)
        self.assertIn("lookup_order", s.GET_CUSTOMER)
        self.assertIn("escalate_to_human", s.PROCESS_REFUND)

    def test_every_line_fits_on_screen(self):
        for line in (HERE / "mcp_server.py").read_text().splitlines():
            self.assertLessEqual(len(line), 67, line)


class Empty(Base):
    def test_a_missing_order_is_found_false_not_an_error(self):
        self.assertEqual(s.lookup_order("O-9999"),
                         {"found": False, "order_id": "O-9999"})

    def test_an_unknown_email_is_found_false(self):
        self.assertFalse(s.get_customer("nobody@example.com")["found"])

    def test_a_real_order(self):
        order = s.lookup_order("o-5001")
        self.assertTrue(order["found"])
        self.assertEqual(order["status"], "delivered")


class Errors(Base):
    def test_a_malformed_id_is_validation_and_not_retryable(self):
        e = error_of(s.lookup_order, "5001")
        self.assertEqual(e["errorCategory"], "validation")
        self.assertFalse(e["isRetryable"])

    def test_an_outage_is_transient_and_the_retry_works(self):
        with mock.patch.dict(os.environ, {"SARATHI_FLAKY_ORDERS": "1"}):
            e = error_of(s.lookup_order, "O-5001")
            self.assertEqual(e["errorCategory"], "transient")
            self.assertTrue(e["isRetryable"])
            self.assertTrue(s.lookup_order("O-5001")["found"])

    def test_no_store_key_is_a_permission_error(self):
        with mock.patch.dict(os.environ, {}, clear=True):
            e = error_of(s.process_refund, "C-1001", "O-5001", 89.0)
        self.assertEqual(e["errorCategory"], "permission")

    def test_an_unverified_refund_is_a_business_error(self):
        with mock.patch.dict(os.environ, KEY):
            e = error_of(s.process_refund, "C-1001", "O-5001", 89.0)
        self.assertEqual(e["errorCategory"], "business")
        self.assertIn("get_customer", e["message"])

    def test_over_500_is_business_with_a_customer_sentence(self):
        s.get_customer("asha@example.com")
        with mock.patch.dict(os.environ, KEY):
            e = error_of(s.process_refund, "C-1001", "O-5002", 640.0)
        self.assertEqual(e["errorCategory"], "business")
        self.assertFalse(e["isRetryable"])
        self.assertIn("500 dollars", e["customerMessage"])

    def test_a_verified_refund_under_the_line_is_issued(self):
        s.get_customer("asha@example.com")
        with mock.patch.dict(os.environ, KEY):
            refund = s.process_refund("C-1001", "O-5001", 89.0)
        self.assertEqual(refund["status"], "issued")

    def test_the_client_sees_is_error_true(self):
        result = asyncio.run(s.server.call_tool(
            "lookup_order", {"order_id": "5001"}))
        self.assertTrue(result.is_error)
        body = json.loads(result.content[0].text)
        self.assertEqual(body["errorCategory"], "validation")


class ForcedFirstTool(unittest.TestCase):
    def test_turn_one_is_forced_then_auto(self):
        import agent
        import replay

        class Recorder(replay.ReplayClient):
            choices = []

            def create(self, **request):
                self.choices.append(request["tool_choice"])
                return super().create(**request)

        with mock.patch("builtins.print"):
            agent.run_agent(Recorder(replay.REFUND), replay.ASK)
        self.assertEqual(Recorder.choices[0],
                         {"type": "tool", "name": "get_customer"})
        self.assertTrue(all(c == {"type": "auto"}
                            for c in Recorder.choices[1:]))

    def test_no_email_means_auto(self):
        import agent
        self.assertEqual(agent.first_choice("where is O-5001?"),
                         {"type": "auto"})


class Config(unittest.TestCase):
    def test_mcp_json_holds_no_secret(self):
        config = json.loads(
            (HERE.parent / ".mcp.json").read_text())
        server = config["mcpServers"]["sarathi"]
        self.assertEqual(server["env"]["SARATHI_STORE_KEY"],
                         "${SARATHI_STORE_KEY:-}")


if __name__ == "__main__":
    unittest.main()
