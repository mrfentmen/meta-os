#!/usr/bin/env python3
"""tests/test_intel_brief_held_sources.py -- INT-027 follow-up.

Closes cold-start gaps 3 (no held decisions) and 4 (no source
pointers) for the template brief, from stated snapshot records
the caller supplies: "held_decisions" (decisions waiting on a
named decider) and "source_pointers" (where the details live).
The INT-027 verdict documented both gaps as limits because no
such source existed in the FND-033 source map; these records
are that source, supplied by the caller the same way the daily,
memory, and federation records are, never re-derived from raw
history and never guessed from a job title.

Still owed, stated plainly: a Spark-composed brief carrying
these lines (real Spark transport is still blocked), and an
independent lane member's cold-start re-run under the new
sections. This file pins the template renderer only.
"""

import os
import unittest

import sys
sys.path.insert(0, ".")
from intel import brief  # noqa: E402


def _content_snapshot(**extra):
    snapshot = {
        "source_window": "2026-10-28 08:00 ET onward, "
                         "last 24 hours",
        "messages": [{"nick": "hana",
                      "text": "DECISION: ship the brief panel first"}],
        "jobs": [{"id": "6", "title": "cold-start test",
                  "status": "open"}],
    }
    snapshot.update(extra)
    return snapshot


class HeldDecisionsLinesTest(unittest.TestCase):
    def test_questions_verbatim_with_decider_in_order(self):
        record = {"decisions": [
            {"question": "Approve posting brief announcements?",
             "decider": "dale"},
            {"question": "Pick the boot target for demo day?",
             "decider": "dale"},
        ], "as_of": 1793101200}
        lines = brief.held_decisions_lines(record)
        self.assertEqual(len(lines), 2)
        self.assertIn("Approve posting brief announcements?", lines[0])
        self.assertIn("(waiting on dale)", lines[0])
        self.assertIn("Pick the boot target for demo day?", lines[1])
        self.assertIn("(as of ", lines[0])

    def test_missing_decider_reads_not_reported(self):
        lines = brief.held_decisions_lines(
            {"decisions": [{"question": "Pick the boot target?"}]})
        self.assertEqual(len(lines), 1)
        self.assertIn("(decider not reported)", lines[0])
        self.assertIn("(snapshot time not reported)", lines[0])

    def test_entries_without_a_question_are_skipped(self):
        lines = brief.held_decisions_lines(
            {"decisions": ["not a dict", {"decider": "dale"},
                           {"question": ""},
                           {"question": "Real question?",
                            "decider": "dale"}]})
        self.assertEqual(len(lines), 1)
        self.assertIn("Real question?", lines[0])

    def test_empty_record_reads_none_reported(self):
        lines = brief.held_decisions_lines({"decisions": []})
        self.assertTrue(lines[0].startswith("Held decisions: none reported"))
        lines = brief.held_decisions_lines("not a record")
        self.assertTrue(lines[0].startswith("Held decisions: none reported"))


class SourcePointerLinesTest(unittest.TestCase):
    def test_pointers_verbatim_in_order(self):
        lines = brief.source_pointer_lines(
            ["plan/lanes/HANA.md", "intel/evals/log.md"])
        self.assertEqual(lines, ["Source: plan/lanes/HANA.md",
                                 "Source: intel/evals/log.md"])

    def test_absent_empty_or_unusable_yields_no_lines(self):
        self.assertEqual(brief.source_pointer_lines(None), [])
        self.assertEqual(brief.source_pointer_lines([]), [])
        self.assertEqual(brief.source_pointer_lines(
            ["", 42, None]), [])


class HeldSourcesComposerTest(unittest.TestCase):
    def _snapshot(self):
        return _content_snapshot(
            held_decisions={"decisions": [
                {"question": "Approve posting brief announcements?",
                 "decider": "dale"}]},
            source_pointers=["plan/lanes/HANA.md"])

    def test_sections_present_after_watch_items(self):
        text = brief.compose_template_brief(self._snapshot())
        self.assertIn("\nHeld decisions\n", text)
        self.assertIn("Held decision: Approve posting brief "
                      "announcements? (waiting on dale)", text)
        self.assertIn("\nSources\n", text)
        self.assertIn("Source: plan/lanes/HANA.md", text)
        self.assertLess(text.index("Watch items"),
                        text.index("Held decisions"))
        self.assertLess(text.index("Held decisions"),
                        text.index("Sources"))

    def test_no_record_means_no_section(self):
        text = brief.compose_template_brief(_content_snapshot())
        self.assertNotIn("Held decisions", text)
        self.assertNotIn("Sources", text)

    def test_empty_window_carries_sections_before_no_activity(self):
        snapshot = {"held_decisions": {"decisions": [
            {"question": "Approve posting brief announcements?",
             "decider": "dale"}]},
            "source_pointers": ["plan/lanes/HANA.md"]}
        text = brief.compose_template_brief(snapshot)
        self.assertIn("Held decision: Approve posting brief "
                      "announcements?", text)
        self.assertIn("Source: plan/lanes/HANA.md", text)
        self.assertLess(text.index("Held decisions"),
                        text.index("no activity yet"))
        self.assertLess(text.index("Sources"),
                        text.index("no activity yet"))

    def test_trim_keeps_plain_lines_after_dropping_bullets(self):
        jobs = [{"id": str(i), "title": "job number %d" % i,
                 "status": "open"} for i in range(60)]
        snapshot = _content_snapshot(
            jobs=jobs,
            held_decisions={"decisions": [
                {"question": "Approve posting brief announcements?",
                 "decider": "dale"}]},
            source_pointers=["plan/lanes/HANA.md"])
        trimmed = brief._trim_to_budget(
            brief.compose_template_brief(snapshot), 220)
        self.assertLessEqual(len(trimmed.split()), 220)
        self.assertIn("Held decision: Approve posting brief "
                      "announcements?", trimmed)
        self.assertIn("Source: plan/lanes/HANA.md", trimmed)


class HeldSourcesRubricTest(unittest.TestCase):
    def test_rubric_names_the_gaps_check(self):
        path = os.path.join("intel", "evals", "brief_rubric.md")
        with open(path) as handle:
            rubric = handle.read()
        self.assertIn("INT-027 gaps 3/4", rubric)
        self.assertIn("Held decisions", rubric)
        self.assertIn("Sources", rubric)


if __name__ == "__main__":
    unittest.main()
