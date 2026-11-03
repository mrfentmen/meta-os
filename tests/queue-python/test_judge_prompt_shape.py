"""Judge prompt shape tests (CB2-035..036). Offline; pure text."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import judge  # noqa: E402


class PromptShapeTests(unittest.TestCase):
    def test_both_readings_appear_and_extra_incident_data_does_not(self):
        first = {"product": "ignis",
                 "timestamp": "2026-11-02T10:00:00Z",
                 "assessment": {"category": "visible flame",
                                "summary": "first summary"},
                 "secret": "do-not-leak"}
        review = {"product": "ignis",
                  "timestamp": "2026-11-02T10:00:01Z",
                  "assessment": {"category": "visible smoke",
                                 "summary": "review summary"},
                  "incident_notes": "private notes"}
        text = judge.build_judge_prompt("ignis", first, review)
        self.assertIn("visible flame", text)
        self.assertIn("visible smoke", text)
        self.assertIn("first summary", text)
        self.assertNotIn("do-not-leak", text)
        self.assertNotIn("private notes", text)

    def test_assessment_rule_appears_exactly_once(self):
        text = judge.build_judge_prompt(
            "vigiles",
            {"assessment": {"category": "person down"}},
            {"assessment": {"category": "person down"}})
        self.assertEqual(text.count("never confirm on a guess"), 1)
        self.assertEqual(text.count("Set confidence to null"), 1)


if __name__ == "__main__":
    unittest.main()
