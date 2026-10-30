"""DEM-011: the staged silent failure runs to its cue in rehearsal.

The drill script itself (intel/drills/demo_silent_failure.py)
is the acceptance artifact — DEMO.md Shot 7 staged on
fixtures: Milo's worker claims a job, posts exactly one
progress note, then goes silent on cue. These tests pin the
cue into the suite: exactly one progress note, nothing from
the worker after the cue, silence inside the stall window,
and exactly one presence-stall alert past the threshold —
so a detector or threshold change that breaks the demo
staging breaks the suite too.
"""

import io
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.drills import demo_silent_failure  # noqa: E402


class DemoSilentFailureDrillTest(unittest.TestCase):
    def test_drill_passes_and_cue_card_names_shot_nick_job(self):
        report = demo_silent_failure.run_drill()
        cue = report["cue"]
        self.assertEqual(cue["shot"], 7)
        self.assertEqual(cue["nick"], "milo")
        self.assertEqual(cue["job"], "7")
        self.assertEqual(cue["progress_notes"], 1)
        self.assertEqual(cue["claim_to_cue_seconds"], 120)
        self.assertEqual(cue["alert_kind"], "presence-stall")
        alert = report["alert"]
        self.assertEqual(alert["nick"], "milo")
        self.assertEqual(alert["job"], "7")
        self.assertEqual(len(report["log"]), 4)

    def test_cue_is_silence_not_absence_of_job(self):
        # The cue must leave the job claimed (the stall is the
        # story) while the worker itself contributes nothing
        # further: re-running the drill's staging by hand via
        # the report's cue fields is not possible, so this pins
        # the invariant through the alert: a presence-stall
        # alert exists only because the job is still claimed
        # by a nick that has vanished from presence.
        report = demo_silent_failure.run_drill()
        self.assertEqual(report["alert"]["kind"], "presence-stall")
        self.assertEqual(report["cue"]["progress_notes"], 1)

    def test_cli_main_exits_zero_and_prints_cue_card_and_pass(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = demo_silent_failure.main([])
        self.assertEqual(code, 0)
        text = out.getvalue()
        self.assertIn("CUE CARD", text)
        self.assertIn("demo_silent_failure drill: PASS", text)


if __name__ == "__main__":
    unittest.main()
