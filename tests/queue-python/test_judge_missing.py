"""Missing-case tests for the Imperium judge (B234).

Covers the branches tests/queue-python/test_judge.py does not:
a failed review that still carries a category, a cleared reading that
matches the patrol reading, verdict parsing of odd JSON shapes, and the
prompt's unknown-division and truncation rules.

Run with: python3 -m pytest tests/queue-python/test_judge_missing.py -q
"""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew_common  # noqa: E402
import judge  # noqa: E402


def rule(first, review, ok=True, division="vigiles"):
    return judge.combine(division, first, review, ok,
                         crew_common.is_flagged_category)


class CombineEdgeTests(unittest.TestCase):
    def test_failed_review_with_a_category_still_refuses_to_confirm(self):
        verdict, reasons = rule("person down", "person down", ok=False)
        self.assertEqual(verdict, "inconclusive")
        self.assertIn("missing reading", reasons[0])

    def test_review_ok_but_no_category_is_inconclusive(self):
        verdict, _ = rule("person down", None, ok=True)
        self.assertEqual(verdict, "inconclusive")

    def test_baseline_review_clears_even_when_patrol_flagged(self):
        verdict, reasons = rule("person down", "normal activity")
        self.assertEqual(verdict, "cleared")
        self.assertIn("normal activity", reasons[0])

    def test_two_flagged_readings_confirm_with_the_patrol_category_named(self):
        verdict, reasons = rule("person down", "possible altercation")
        self.assertEqual(verdict, "confirmed")
        self.assertIn("person down", reasons[0])
        self.assertIn("possible altercation", reasons[0])


class ParseVerdictEdgeTests(unittest.TestCase):
    def test_verdict_word_is_case_and_whitespace_tolerant(self):
        self.assertEqual(
            judge.parse_verdict('{"verdict": "  CONFIRM  "}')[0], "confirmed")

    def test_json_scalars_are_not_objects(self):
        for bad in ("42", '"confirm"', "null", "true", "[1, 2]"):
            self.assertEqual(judge.parse_verdict(bad)[0], "inconclusive", bad)

    def test_non_list_reasons_become_an_empty_list(self):
        verdict, category, reasons = judge.parse_verdict(
            '{"verdict": "reject", "category": "normal activity",'
            ' "reasons": "because"}')
        self.assertEqual(verdict, "cleared")
        self.assertEqual(category, "normal activity")
        self.assertEqual(reasons, [])

    def test_list_reasons_are_stringified(self):
        _, _, reasons = judge.parse_verdict(
            '{"verdict": "investigate", "reasons": [1, null, {"a": 1}]}')
        self.assertEqual(reasons, ["1", "None", "{'a': 1}"])

    def test_unknown_verdict_quotes_the_offending_value(self):
        verdict, category, reasons = judge.parse_verdict(
            '{"verdict": "dispatch", "category": "person down"}')
        self.assertEqual(verdict, "inconclusive")
        self.assertIsNone(category)
        self.assertIn("dispatch", reasons[0])


class PromptEdgeTests(unittest.TestCase):
    def test_unknown_division_is_named_unknown_never_guessed(self):
        text = judge.build_judge_prompt("custodes", {}, {})
        self.assertIn("the unknown", text)
        self.assertNotIn("police", text)

    def test_long_readings_are_cut_at_the_prompt_limit(self):
        text = judge.build_judge_prompt(
            "vigiles", {"summary": "a" * 3000}, {})
        self.assertNotIn("a" * 3000, text)
        self.assertIn("a" * 100, text)

    def test_prompt_demands_json_only_and_a_null_confidence(self):
        text = judge.build_judge_prompt("medicus", {}, {})
        self.assertIn("Return JSON ONLY", text)
        self.assertIn('"confidence": null', text)


if __name__ == "__main__":
    unittest.main()
