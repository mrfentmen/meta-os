#!/usr/bin/env python3
"""tests/test_intel_brief_cold_start.py -- INT-027: cold-start test.

A lane member who skipped a day uses only the morning brief to
resume work. This is Hana's own cold-start attempt, run the way
the BRF-018 cold-read verdict was run: the brief is generated
from a hand-written snapshot, and the attempt is judged from the
brief text alone, with no lane file, git log, or eval log open
during the attempt. An independent lane member's cold-start is
still owed, the same caveat BRF-018 carries.

The snapshot is hand-written, NOT a live room and NOT Buffy's
fixtures (not in this repo yet). Its job titles mirror real
recent lane work so the attempt is grounded, not invented:
the brief cost check (BRF-027), the on-join brief score
(BRF-018), the e2e brief window fix (INT-024 fix), the
spoofed-dispatch drill (PAX INT-010), and the watchdog
threshold lock (MILO INT-022). The blocked job carries the
real standing blocker, "waiting on the real Spark endpoint".
The brief is the BRF-008 template brief: real Spark transport
is still blocked, so no Spark-composed cold-start is scored
here, and that re-score is still owed.

Verdict, pinned here and logged in intel/evals/log.md:
PARTIAL. Job-level resume works from the brief alone; lane-
level resume does not. A returner can start on the one open
job, can see the owners to ask, and can see the blocked job
to avoid. A returner cannot tell, from the brief alone, which
lane task is next in priority order, what changed since their
last brief, which decisions are held waiting on Dale, where
the details live, or who to ask about the blocked job. Those
five gaps are documented as limits in the log entry, not
fixed here: fixing them would need brief sources the FND-033
source map does not provide (a lane-plan queue, a held-
decision list, a previous-brief diff), and inventing those
fields into a snapshot would make the brief claim facts its
sources do not contain. The gaps are pinned, not hidden.
"""

import os
import unittest

import sys
sys.path.insert(0, ".")
from intel import brief  # noqa: E402


class ColdStartTest(unittest.TestCase):
    # INT-027: the cold-start attempt, judged from the brief
    # text alone. The snapshot below is the "yesterday" state
    # the returner missed; the brief is the only thing they
    # are allowed to read in the attempt.
    def _snapshot(self):
        return {
            "source_window": "2026-10-27 08:00 ET onward, "
                             "last 24 hours",
            "messages": [
                {"nick": "hana",
                 "text": "DECISION: brief cost stays inside cap"},
                {"nick": "hana",
                 "text": "DONE: e2e brief window fix"},
                {"nick": "hana",
                 "text": "DECISION: recovery line renders incomplete "
                         "never a false all-clear"},
            ],
            "jobs": [
                {"id": "2", "title": "watchdog thresholds",
                 "status": "claimed", "claim": "milo",
                 "claimed_at": 1000},
                {"id": "3", "title": "spoofed dispatch drill",
                 "status": "claimed", "claim": "pax",
                 "claimed_at": 1000},
                {"id": "6", "title": "cold-start test",
                 "status": "open"},
                {"id": "7", "title": "spark client",
                 "status": "blocked",
                 "note": "waiting on the real Spark endpoint"},
                {"id": "11", "title": "brief cost check",
                 "status": "done", "note": "finished"},
                {"id": "12", "title": "on-join brief score",
                 "status": "done", "note": "finished"},
            ],
            "alerts": [{"id": "ALERT-1",
                        "summary": "stall on job 2"}],
            "presence": ["pax", "milo", "rowan", "hana"],
        }

    def test_morning_brief_scores_rubric_on_cold_snapshot(self):
        text = brief.compose_template_brief(self._snapshot())
        # Morning budget 220 (FND-034); window stated first.
        self.assertLessEqual(len(text.split()), 220)
        self.assertIn("Window: 2026-10-27 08:00 ET onward, "
                      "last 24 hours", text)
        # Decisions trace to the snapshot markers, verbatim.
        self.assertIn("- decision: brief cost stays inside cap",
                      text)
        self.assertIn("- done: e2e brief window fix", text)
        self.assertIn("- decision: recovery line renders "
                      "incomplete never a false all-clear", text)
        # Blocked job named with its reason verbatim.
        self.assertIn("- 7 spark client: waiting on the real "
                      "Spark endpoint", text)
        # Alert linked by id.
        self.assertIn("- ALERT-1: stall on job 2", text)

    def test_job_level_resume_works_from_brief_alone(self):
        text = brief.compose_template_brief(self._snapshot())
        # The returner can start on the one open job, can see
        # the owners to ask, and can see the blocked job to
        # avoid -- all from this brief alone.
        self.assertIn("- 6 cold-start test (open)", text)
        self.assertIn("- milo: watchdog thresholds", text)
        self.assertIn("- pax: spoofed dispatch drill", text)
        self.assertIn("spark client", text)

    def test_lane_level_gaps_pinned_not_hidden(self):
        text = brief.compose_template_brief(self._snapshot())
        # Gap 1, no priority order: the brief lists jobs by
        # section, never by lane task id or dependency order,
        # so the returner cannot tell which lane task is next.
        self.assertNotIn("INT-027", text)
        self.assertNotIn("BRF-019", text)
        self.assertNotIn("next task", text)
        # Gap 2, no diff: nothing says what changed since the
        # returner's last brief, so old news and new news
        # look identical.
        self.assertNotIn("since your last brief", text)
        self.assertNotIn("new since", text)
        # Gap 3, no held decisions: decisions waiting on Dale
        # (brief posting, the stretch call, the Spark
        # endpoint) are not jobs, so they never appear.
        self.assertNotIn("BRF-010", text)
        self.assertNotIn("GOV-007", text)
        self.assertNotIn("GOV-001", text)
        # Gap 4, no source pointers: the brief never says
        # where the details live (lane file, eval log).
        self.assertNotIn("plan/lanes", text)
        self.assertNotIn("evals/log", text)
        # Gap 5, no ask-nick on the blocked job: the blocked
        # line names the job and its reason, but no owner to
        # ask about it, unlike the Owners section.
        blocked_line = [line for line in text.splitlines()
                        if line.startswith("- 7 spark client")][0]
        self.assertNotIn("milo", blocked_line)
        self.assertNotIn("pax", blocked_line)
        self.assertNotIn("rowan", blocked_line)

    def test_eval_log_documents_the_cold_start_gaps(self):
        # The INT-027 log entry and this test were written
        # together: the entry must name the verdict and all
        # five gaps, or the test fails and the gaps are not
        # documented anywhere.
        here = os.path.dirname(os.path.abspath(__file__))
        log_path = os.path.join(here, "..", "intel", "evals",
                                "log.md")
        with open(log_path, encoding="utf-8") as handle:
            log = handle.read()
        self.assertIn("## 2026-10-27 — INT-027", log)
        self.assertIn("cold-start", log)
        self.assertIn("PARTIAL", log)
        for gap in ("no priority order", "no diff",
                    "no held decisions", "no source pointers",
                    "no ask-nick"):
            self.assertIn(gap, log)
