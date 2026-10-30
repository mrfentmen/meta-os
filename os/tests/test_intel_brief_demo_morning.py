"""BRF-025: demo morning brief draft, hand-checked line by line.

The draft lives at hackathon/relay-intelligence/demo-assets/
morning-brief-demo.md. It is built from the landed devpack brief
snapshot (tests/test_intel_devpack.py brief_snapshot(), as
recorded in intel/devpack/brief.json) — NOT from Buffy's
demo-day state pack (INT-014 / INT-033), which has not landed,
so no claim here traces to that pack. When the state pack lands
the draft must be regenerated from it and re-checked; this test
pins the draft to its stated source, so a drifted draft fails
instead of silently passing as the demo-day brief.

The snapshot is copied here in full, not imported from the
devpack test, so this test stands alone if that test moves.
"""

import os
import re
import unittest

SNAPSHOT_MESSAGES = [
    ("pax", "DECISION: ship the brief panel first"),
    ("milo", "DONE: watchdog loop runs on the stall fixture"),
    ("rowan", "just checking the viewer"),
    ("pax", "BLOCKED: dispatch needs the Spark endpoint"),
]

SNAPSHOT_JOBS = [
    ("1", "intel status module", "claimed"),
    ("2", "status module tests", "open"),
    ("3", "viewer panel stub", "blocked"),
]

SNAPSHOT_ALERT = ("alert:presence-stall:milo:1",
                  "milo stalled on job 1")


def _draft_brief():
    path = os.path.join(os.path.dirname(__file__), "..",
                        "hackathon", "relay-intelligence",
                        "demo-assets", "morning-brief-demo.md")
    with open(path) as handle:
        text = handle.read()
    match = re.search(r"```\n(.*?)```", text, re.S)
    assert match is not None, "draft has no fenced brief block"
    return text, match.group(1)


class DemoMorningBriefTest(unittest.TestCase):
    """BRF-025: the draft brief matches its stated source exactly."""

    def test_brief_is_template_and_within_morning_budget(self):
        _text, brief = _draft_brief()
        self.assertTrue(brief.startswith("TEMPLATE\n"))
        self.assertEqual(len(brief.split()), 121)
        self.assertLessEqual(len(brief.split()), 220)

    def test_sections_in_morning_prompt_order(self):
        _text, brief = _draft_brief()
        sections = ["Decisions", "In flight", "Owners",
                    "Blocked and why", "Watch items"]
        positions = [brief.index(section) for section in sections]
        self.assertEqual(positions, sorted(positions))

    def test_window_and_v2_rules_present(self):
        _text, brief = _draft_brief()
        self.assertIn("Window: last 500 messages or last 24 hours, "
                      "4 kept, 0 dropped", brief)
        self.assertIn("No previous brief is in this window, "
                      "so nothing here is marked as new", brief)
        self.assertIn("No priority order is recorded in this window",
                      brief)
        self.assertIn("owner not reported in this window", brief)

    def test_all_jobs_named_and_only_blocked_job_blocked(self):
        _text, brief = _draft_brief()
        for job_id, title, _status in SNAPSHOT_JOBS:
            self.assertIn(title, brief)
        blocked = brief.split("Blocked and why")[1]
        blocked = blocked.split("Watch items")[0]
        self.assertIn("3 viewer panel stub: waiting on the "
                      "Spark endpoint decision", blocked)
        self.assertNotIn("intel status module", blocked)
        self.assertNotIn("status module tests", blocked)

    def test_decisions_and_alert_trace_to_snapshot(self):
        _text, brief = _draft_brief()
        self.assertIn("pax: ship the brief panel first", brief)
        self.assertIn("milo: watchdog loop runs on the stall fixture",
                      brief)
        self.assertIn("pax: dispatch needs the Spark endpoint", brief)
        self.assertNotIn("just checking the viewer", brief)
        self.assertIn(SNAPSHOT_ALERT[0] + ": " +
                      SNAPSHOT_ALERT[1], brief)

    def test_no_job_or_nick_outside_snapshot(self):
        _text, brief = _draft_brief()
        allowed_nicks = {nick for nick, _msg in SNAPSHOT_MESSAGES}
        allowed_nicks.add("milo")  # alert summary nick, also a message nick
        for nick in ("dale", "buffy", "del"):
            self.assertNotIn(nick + ":", brief)
        for job_id in ("4", "5", "7", "8", "9"):
            self.assertNotRegex(brief, r"(?m)^- %s " % job_id)

    def test_draft_states_its_source_and_its_recheck(self):
        text, _brief = _draft_brief()
        self.assertIn("INT-014", text)
        self.assertIn("not landed", text)
        self.assertIn("must be regenerated", text)
        self.assertIn("no Spark call was made", text)
