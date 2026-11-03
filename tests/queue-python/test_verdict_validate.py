"""Tests for the v2 judge verdict record validator (CB2-373..374).

Run from the repo root:

    python3 -m unittest discover -s tests/queue-python -p "test_verdict_validate.py"
"""

import copy
import os
import sys
import unittest

sys.path.insert(
    0,
    os.path.join(os.path.dirname(__file__), "..", "..", "server", "queue"),
)

from judge import build_verdict_record  # noqa: E402
from verdict_validate import (  # noqa: E402
    JUDGE_MODES,
    VERDICTS,
    validate_verdict_record,
)


def real_record(**overrides):
    """The builder's own output -- the validator is never fed a shape
    the judge does not emit."""
    fields = dict(
        at="2026-11-02T10:06:00-05:00",
        verdict="confirmed",
        category="crowd gathered",
        judge_mode="deterministic",
        judge_reasons=["both readings agree"],
        job_id="job-1",
        model=None,
        latency_ms=None,
        error=None,
        summary="both readers saw the same crowd",
        first_timestamp="2026-11-02T10:05:33-05:00",
        review_timestamp="2026-11-02T10:05:58-05:00",
    )
    fields.update(overrides)
    return build_verdict_record(**fields)


class TestValid(unittest.TestCase):
    def test_builder_output_passes(self):
        self.assertEqual(validate_verdict_record(real_record()), [])

    def test_model_mode_passes(self):
        record = real_record(judge_mode="model", model="muse-spark-1.3",
                             latency_ms=1200)
        self.assertEqual(validate_verdict_record(record), [])

    def test_both_enums_are_the_documented_pairs(self):
        self.assertEqual(VERDICTS, ("confirmed", "cleared", "inconclusive"))
        self.assertEqual(JUDGE_MODES, ("deterministic", "model"))

    def test_validator_does_not_mutate(self):
        record = real_record()
        before = copy.deepcopy(record)
        validate_verdict_record(record)
        self.assertEqual(record, before)


class TestRefusals(unittest.TestCase):
    def test_not_an_object(self):
        self.assertEqual(
            validate_verdict_record([]), ["record: must be an object"])

    def test_judge_mode_outside_the_two_values_fails(self):
        record = real_record()
        record["judge_mode"] = "vibes"
        self.assertIn(
            "judge_mode: must be one of deterministic, model",
            validate_verdict_record(record))

    def test_verdict_outside_the_three_values_fails(self):
        record = real_record()
        record["verdict"] = "probably"
        self.assertIn(
            "verdict: must be one of confirmed, cleared, inconclusive",
            validate_verdict_record(record))

    def test_wrong_step_fails(self):
        record = real_record()
        record["step"] = "assess"
        self.assertIn("step: must be review", validate_verdict_record(record))

    def test_unknown_judge_is_named(self):
        record = real_record()
        record["judged_by"] = "someone-else"
        self.assertIn(
            "judged_by: must be imperium-judge",
            validate_verdict_record(record))

    def test_missing_field_is_named(self):
        record = real_record()
        del record["started_at"]
        self.assertIn(
            "missing required field: started_at",
            validate_verdict_record(record))

    def test_extra_field_is_named(self):
        record = real_record()
        record["tier"] = "gold"
        self.assertIn(
            "unexpected field: tier", validate_verdict_record(record))

    def test_non_list_reasons_fail(self):
        record = real_record()
        record["judge_reasons"] = "both agree"
        self.assertIn(
            "judge_reasons: must be a list",
            validate_verdict_record(record))

    def test_negative_latency_fails(self):
        record = real_record()
        record["latency_ms"] = -5
        self.assertIn(
            "latency_ms: must be a number >= 0 or null",
            validate_verdict_record(record))

    def test_bad_at_timestamp_fails(self):
        record = real_record()
        record["at"] = "now"
        self.assertIn(
            "at: must be an ISO-8601 string",
            validate_verdict_record(record))


if __name__ == "__main__":
    unittest.main()
