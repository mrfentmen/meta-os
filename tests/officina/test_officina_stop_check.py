"""CB2-455 — the STOP file, as a function and as the loop that honours it.

Function-level first: a fixture STOP file in a temp dir reads true, its absence
reads false. Then the real caller: `run_loop` stops before its next claim when
the file is there, and says so in the record. No service is started.
"""

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, "os", "worlds", "officina", "runtime"))

from design_loop import run_loop, stop_requested  # noqa: E402


class StopCheckTest(unittest.TestCase):
    def test_stop_file_present_is_true_and_absent_is_false(self):
        with tempfile.TemporaryDirectory() as tmp:
            stop = os.path.join(tmp, "officina.STOP")
            self.assertFalse(stop_requested(stop), "no file, no stop")
            with open(stop, "w") as f:
                f.write("operator\n")
            self.assertTrue(stop_requested(stop), "a filed STOP is a stop")

            # A missing path is not a stop, and neither is an empty argument.
            self.assertFalse(stop_requested(None))
            self.assertFalse(stop_requested(""))

    def test_the_loop_stops_before_claiming_when_a_stop_is_filed(self):
        with tempfile.TemporaryDirectory() as tmp:
            stop = os.path.join(tmp, "officina.STOP")
            with open(stop, "w") as f:
                f.write("operator\n")
            record = run_loop(8, seed=11, stop_path=stop)

        self.assertEqual(record["stopped"], "stop-file")
        # The jobs were posted before the first claim, as the loop always posts
        # them; what matters is that none was scored, which the empty curve shows.
        self.assertEqual(record["score_curve_best_so_far"], [], "no job was scored")
        self.assertTrue(all(j["status"] == "posted" for j in record["jobs"]), "nothing was claimed")
        self.assertEqual(record["winners"], [])
        self.assertIsNone(record["best"])
        self.assertEqual(record["n_variants"], 8)

    def test_without_a_stop_the_loop_runs_the_whole_board(self):
        record = run_loop(6, seed=11)
        self.assertIsNone(record["stopped"])
        self.assertEqual(len(record["jobs"]), 6, "every posted job was scored")
        self.assertTrue(all(j["status"] in ("done", "failed") for j in record["jobs"]))


if __name__ == "__main__":
    unittest.main()
