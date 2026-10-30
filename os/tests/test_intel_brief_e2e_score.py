#!/usr/bin/env python3
"""tests/test_intel_brief_e2e_score.py -- INT-024: briefs generated
during e2e runs, scored against the BRF-015 rubric the same day.

The e2e run scored here is Pax's INT-002 loop (intel/e2e1.py),
which landed 2026-10-27. The loop is re-run inside this harness
with write_log=False, so Pax's committed transcript in
intel/evals/e2e1.log is untouched, and compose_template_brief is
wrapped to capture the two brief texts the loop actually produces:
the plain template brief and the boot brief carrying the OS-051
previous-session digest. No Spark call runs: both briefs are
BRF-008 template briefs, because real Spark transport is blocked.

Score, pinned here and logged in intel/evals/log.md: 8 of 8
rubric checks pass for both briefs, after the INT-024 fix below.
The earlier 7/8 score failed check 6 (window stated) because the
e2e snapshot carried no source_window and no window_start
(intel/ingest.py snapshot() never sets either), and the e2e brief
stage called compose_template_brief directly, bypassing
compose_brief's BRF-023 cap that would have set a source_window
record. The fix, landed 2026-10-27: the e2e brief stage in
intel/e2e1.py now caps the snapshot with
brief.cap_snapshot_window before composing either brief, so both
briefs carry the stated cap (last 500 messages or last 24 hours,
8 kept, 0 dropped). The cap states the cap; it invents no
history, and no brief fact changed. This test and the INT-024
eval log entry were updated together with the fix, as the old
pinned-gap test required.
"""

import re
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
from intel import brief  # noqa: E402
from intel import e2e1  # noqa: E402

TITLES = ("Write the e2e probe note",
          "Record the probe result in the e2e log")


class E2EBriefScoreTest(RelayTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        original = brief.compose_template_brief
        captured = {}

        def capturing(snapshot, boot=False):
            text = original(snapshot, boot=boot)
            captured[boot] = text
            return text

        brief.compose_template_brief = capturing
        try:
            result = e2e1.run_loop(write_log=False)
        finally:
            brief.compose_template_brief = original
        assert result["ok"], result["transcript"]
        cls.plain = captured[False]
        cls.boot = captured[True]

    def test_both_briefs_within_morning_budget(self):
        # Rubric check 4: boot briefs extend the morning format,
        # so the 220-word morning budget is the bar (the same bar
        # the OS-062/103/127 boot-brief entries used for trimming).
        self.assertLessEqual(len(self.boot.split()), 220)
        self.assertLessEqual(len(self.plain.split()), 220)

    def test_no_blocked_no_owners_no_alerts_match_manifest(self):
        # Rubric checks 1, 2, 8: the manifest holds 0 blocked
        # jobs, 0 claimed jobs (both jobs are done and jobs.py
        # clears the claim on done), and no alerts, so all three
        # sections must read empty -- never padded, never invented.
        for text in (self.plain, self.boot):
            self.assertIn("Nothing blocked in this window", text)
            self.assertIn("Nothing reported in this window", text)
            self.assertIn("Nothing to watch in this window", text)
            self.assertNotIn("worker-a:", text)
            self.assertNotIn("ALERT-", text)

    def test_decisions_trace_to_done_messages(self):
        # Rubric checks 3 and 7: the only Decisions lines are the
        # two DONE markers from the snapshot messages, verbatim.
        # JOB, CLAIM, and PROGRESS messages are not decision
        # markers and must not appear as decisions.
        for text in (self.plain, self.boot):
            self.assertIn("- done: 1 e2e1-no-real-commit", text)
            self.assertIn("- done: 2 e2e1-no-real-commit", text)
            self.assertNotIn("JOB:", text)
            self.assertNotIn("CLAIM:", text)
            self.assertNotIn("PROGRESS:", text)

    def test_boot_digest_and_system_lines_only_in_boot(self):
        # OS-051: the boot brief opens with the digest line right
        # after the window line, naming both completed titles and
        # 0 open threads; the plain brief carries no digest.
        # OS-062: the three system lines follow the digest in
        # order and precede Decisions, in the boot brief only.
        match = re.search(
            r"Previous session: last brief [^,]+, 2 jobs completed "
            r"\(Write the e2e probe note; "
            r"Record the probe result in the e2e log\), "
            r"0 open threads",
            self.boot)
        self.assertIsNotNone(match, self.boot)
        lines = self.boot.splitlines()
        self.assertEqual(lines[0], "TEMPLATE")
        self.assertEqual(
            lines[1],
            "Window: last 500 messages or last 24 hours, "
            "8 kept, 0 dropped")
        self.assertEqual(lines[2], match.group(0))
        self.assertIn("Drivers: not reported in this snapshot",
                      self.boot)
        self.assertIn("Tools: MCP gateway health not reported "
                      "in this snapshot", self.boot)
        self.assertIn("Skill apps: not reported in this snapshot",
                      self.boot)
        order = [self.boot.index("Drivers:"),
                 self.boot.index("Tools:"),
                 self.boot.index("Skill apps:"),
                 self.boot.index("Decisions")]
        self.assertEqual(order, sorted(order))
        self.assertNotIn("Previous session:", self.plain)
        self.assertNotIn("Drivers:", self.plain)
        self.assertNotIn("Tools:", self.plain)
        self.assertNotIn("Skill apps:", self.plain)

    def test_window_check_passes_after_cap_fix(self):
        # INT-024 rubric check 6, now PASSING after the fix: both
        # e2e briefs open with the stated BRF-023 cap line, so a
        # reader can say what span either brief covers. The cap
        # kept all 8 snapshot messages and dropped 0, so the
        # stated window is the cap, not an invented history.
        # This replaces test_window_check_fails_pinned_gap, which
        # pinned the old failure; the INT-024 eval log entry was
        # updated together with this test, as that test required.
        for text in (self.plain, self.boot):
            self.assertIn(
                "Window: last 500 messages or last 24 hours, "
                "8 kept, 0 dropped", text)
            self.assertNotIn("Window: not stated in this snapshot",
                             text)


if __name__ == "__main__":
    unittest.main()
