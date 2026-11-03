"""Verdict record shape tests (CB2-044..045). Offline; pure builder."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import judge  # noqa: E402


def build(mode):
    return judge.build_verdict_record(
        at="2026-11-02T10:00:02Z", verdict="confirmed",
        category="person down", judge_mode=mode,
        judge_reasons=["reason"], job_id="trio-review",
        model="muse-spark-1.3", latency_ms=4, error=None,
        summary="summary", first_timestamp="2026-11-02T10:00:01Z",
        review_timestamp="2026-11-02T10:00:00Z")


class VerdictRecordTests(unittest.TestCase):
    def test_deterministic_and_model_paths_share_one_key_set(self):
        det = build("deterministic")
        model = build("model")
        self.assertEqual(set(det), set(model))
        self.assertEqual(det["step"], "review")
        self.assertEqual(det["judged_by"], "imperium-judge")

    def test_started_at_is_the_earlier_reading(self):
        self.assertEqual(build("model")["started_at"],
                         "2026-11-02T10:00:00Z")

    def test_judge_mode_is_limited_to_two_values(self):
        self.assertEqual(build("deterministic")["judge_mode"],
                         "deterministic")
        self.assertEqual(build("model")["judge_mode"], "model")
        with self.assertRaises(ValueError):
            build("human")


if __name__ == "__main__":
    unittest.main()
