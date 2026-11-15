"""Tests for lesson 10. No API key, no Claude Code call, no bill.

uv run python -m unittest discover -s 03-research-system -v
"""
import asyncio
import unittest

from claude_agent_sdk import ToolUseBlock

import agents
import findings
import replay
import verify
from agents import HERE, build_options
from coordinator import run


def replayed(script, mode="parallel"):
    client = replay.Replay(script)
    return asyncio.run(run(mode=mode, query_fn=client)), client


class Options(unittest.TestCase):
    def test_two_researchers_with_read_only_tools(self):
        options = build_options()
        self.assertEqual(set(options.agents),
                         {"customer-researcher",
                          "numbers-researcher",
                          "synthesis-writer"})
        for name in agents.RESEARCHERS:
            definition = options.agents[name]
            self.assertEqual(definition.tools,
                             ["Read", "Glob", "Grep"])
            self.assertIn("claim", definition.prompt)
            self.assertIn("source", definition.prompt)

    def test_the_writer_holds_only_verify_fact(self):
        writer = build_options().agents["synthesis-writer"]
        self.assertEqual(writer.tools,
                         ["mcp__research__verify_fact"])
        self.assertIn("research", build_options().mcp_servers)

    def test_the_coordinator_cannot_read(self):
        def call(tool, **extra):
            return asyncio.run(agents.coordinator_reads_nothing(
                {"tool_name": tool, **extra}, "t1", None))
        denied = call("Read")["hookSpecificOutput"]
        self.assertEqual(denied["permissionDecision"], "deny")
        self.assertEqual(call("Agent"), {})
        self.assertEqual(call("Read", agent_id="a1"), {})

    def test_no_bash_anywhere(self):
        self.assertNotIn("Bash", build_options().tools)

    def test_your_own_settings_are_not_loaded(self):
        self.assertEqual(build_options().setting_sources, [])

    def test_mode_changes_only_the_spawn_rule(self):
        fast = build_options("parallel").system_prompt
        slow = build_options("sequential").system_prompt
        self.assertIn("same response", fast)
        self.assertIn("wait for its reply", slow)
        self.assertEqual(fast.replace(agents.SPAWN["parallel"], ""),
                         slow.replace(agents.SPAWN["sequential"], ""))

    def test_the_brief_carries_its_own_context(self):
        prompt = build_options().system_prompt
        for must in ("question", "subtopic", "folder", "format"):
            self.assertIn(must, prompt)


class Coordinator(unittest.TestCase):
    def test_parallel_puts_both_spawns_in_one_reply(self):
        result, client = replayed(replay.PARALLEL)
        self.assertEqual(result["spawns_per_reply"], [2])
        self.assertEqual(client.options.agents.keys(),
                         agents.AGENTS.keys())

    def test_sequential_spawns_one_per_reply(self):
        result, _ = replayed(replay.SEQUENTIAL, "sequential")
        self.assertEqual(result["spawns_per_reply"], [1, 1])

    def test_subagent_messages_are_not_counted_as_spawns(self):
        result, _ = replayed(replay.PARALLEL)
        self.assertEqual(sum(result["spawns_per_reply"]), 2)

    def test_findings_from_both_subagents_are_aggregated(self):
        result, _ = replayed(replay.PARALLEL)
        agents_seen = {f["agent"] for f in result["kept"]}
        self.assertEqual(agents_seen, {"customer-researcher",
                                       "numbers-researcher"})
        self.assertEqual(len(result["kept"]), 6)

    def test_a_claim_with_no_source_or_a_missing_file_is_dropped(self):
        result, _ = replayed(replay.PARALLEL)
        reasons = sorted(f["why"] for f in result["dropped"])
        self.assertEqual(len(reasons), 2)
        self.assertEqual(reasons[0], "no source")
        self.assertTrue(reasons[1].startswith("source not found"))

    def test_each_brief_names_its_folder(self):
        result, _ = replayed(replay.PARALLEL)
        self.assertIn("sources/customers",
                      result["briefs"]["customer-researcher"])
        self.assertIn("sources/numbers",
                      result["briefs"]["numbers-researcher"])

    def test_the_old_task_name_counts_as_a_spawn(self):
        script = list(replay.PARALLEL)
        first = script[0]
        renamed = [ToolUseBlock(id=b.id, name="Task", input=b.input)
                   for b in first.content]
        script[0] = replay.coordinator_says("reply-1", *renamed)
        result, _ = replayed(script)
        self.assertEqual(result["spawns_per_reply"], [2])

    def test_an_unreadable_reply_is_reported_not_lost(self):
        script = [replay.coordinator_says(
                      "r1", replay.spawn("s1", "numbers-researcher")),
                  replay.UserMessage(content=[
                      replay.ToolResultBlock(
                          tool_use_id="s1",
                          content="I could not find the folder.")]),
                  replay.done(1)]
        result, _ = replayed(script)
        self.assertEqual(result["kept"], [])
        self.assertIn("no JSON list", result["dropped"][0]["why"])


class Writer(unittest.TestCase):
    def test_the_writer_answer_and_its_checks_are_kept(self):
        check = ToolUseBlock(id="v1", name=verify.TOOL_NAME,
                             input={"fact": "11 dollars",
                                    "source": "sources/numbers/"
                                    "return-costs-2026.md"})
        script = [
            replay.coordinator_says("r1", ToolUseBlock(
                id="w1", name="Agent",
                input={"subagent_type": "synthesis-writer",
                       "prompt": "Write the answer."})),
            replay.AssistantMessage(
                content=[check], model="claude-haiku-5-5",
                parent_tool_use_id="w1", message_id="sub-w1"),
            replay.UserMessage(content=[replay.ToolResultBlock(
                tool_use_id="v1",
                content=[{"type": "text",
                          "text": '{"supported": true}'}])]),
            replay.UserMessage(content=[replay.ToolResultBlock(
                tool_use_id="w1",
                content=[{"type": "text", "text": "The answer."}])]),
        ]
        result, _ = replayed(script)
        self.assertEqual(result["dropped"], [])
        self.assertEqual(result["answer"], "The answer.")
        self.assertEqual(result["checks"][0]["fact"], "11 dollars")
        self.assertIn("true", result["checks"][0]["result"])


class VerifyFact(unittest.TestCase):
    def test_a_fact_in_its_source_is_supported(self):
        out = verify.check("11 dollars",
                           "sources/numbers/return-costs-2026.md")
        self.assertTrue(out["supported"])
        self.assertEqual(out["line"], 5)

    def test_a_fact_not_in_the_file_is_not_an_error(self):
        out = verify.check("14 dollars",
                           "sources/numbers/return-costs-2026.md")
        self.assertEqual(out, {"supported": False, "source":
                               "sources/numbers/return-costs-2026.md"})

    def test_outside_the_sources_is_a_permission_error(self):
        with self.assertRaises(verify.Failure) as caught:
            verify.check("Sarathi", "../README.md")
        self.assertEqual(caught.exception.error["errorCategory"],
                         "permission")

    def test_a_missing_file_is_a_validation_error(self):
        with self.assertRaises(verify.Failure) as caught:
            verify.check("11", "sources/numbers/nope.md")
        self.assertEqual(caught.exception.error["errorCategory"],
                         "validation")

    def test_the_tool_returns_is_error_true(self):
        out = asyncio.run(verify.verify_fact.handler(
            {"fact": "x", "source": "../README.md"}))
        self.assertTrue(out["is_error"])


class Findings(unittest.TestCase):
    def test_parse_finds_the_list_after_other_text(self):
        words = ('[Subagent hand-back] Here you go:\n```json\n'
                 '[{"claim": "x", "source": "y"}]\n```')
        items = findings.parse(words, "a")
        self.assertEqual(items, [{"claim": "x", "source": "y",
                                  "agent": "a"}])

    def test_parse_returns_nothing_for_plain_text(self):
        self.assertEqual(findings.parse("no list here", "a"), [])

    def test_repeated_claims_merge_and_keep_both_sources(self):
        same = "Store B moved from 30 to 60 days in March 2026"
        items = [
            {"claim": same, "agent": "a",
             "source": "sources/customers/competitors-2026.md"},
            {"claim": same.upper(), "agent": "b",
             "source": "sources/customers/survey-2026-09.md"}]
        kept, dropped = findings.aggregate(items, HERE)
        self.assertEqual(len(kept), 1)
        self.assertEqual(kept[0]["also_in"],
                         ["sources/customers/survey-2026-09.md"])

    def test_an_absolute_path_inside_the_folder_is_kept(self):
        path = HERE / "sources" / "numbers" / "returns-2026.csv"
        item = {"claim": "x", "source": str(path), "agent": "a"}
        kept, _ = findings.aggregate([item], HERE)
        self.assertEqual(kept[0]["source"],
                         "sources/numbers/returns-2026.csv")

    def test_a_source_outside_the_folder_is_dropped(self):
        item = {"claim": "x", "source": "../README.md", "agent": "a"}
        _, dropped = findings.aggregate([item], HERE)
        self.assertEqual(len(dropped), 1)

    def test_every_replayed_source_is_a_real_file(self):
        for f in replay.CUSTOMER_FINDINGS[:3] + replay.NUMBERS_FINDINGS:
            self.assertTrue((HERE / f["source"]).is_file(), f)


if __name__ == "__main__":
    unittest.main()
