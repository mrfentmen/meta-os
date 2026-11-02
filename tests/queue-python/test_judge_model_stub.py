"""Model-judge stub tests (CB2-031..034). Offline; chat_fn stubbed."""
import json
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import judge  # noqa: E402

FIRST = {"product": "vigiles", "timestamp": "2026-11-02T10:00:00Z",
         "assessment": {"category": "person down"}}
REVIEW = {"product": "vigiles", "timestamp": "2026-11-02T10:00:01Z",
          "assessment": {"category": "person down"}}


def run(reply):
    return judge.rule_with_model(
        "vigiles", FIRST, REVIEW, lambda prompt: reply)


class ModelStubTests(unittest.TestCase):
    def test_well_formed_confirm_maps_exactly(self):
        reply = json.dumps({"verdict": "confirm", "category": "person down",
                            "reasons": ["both readings agree"]})
        verdict, category, reasons = run(reply)
        self.assertEqual(verdict, "confirmed")
        self.assertEqual(category, "person down")
        self.assertIn("model judge ruling", reasons[0])

    def test_unknown_outcome_rules_inconclusive_never_coerced(self):
        reply = json.dumps({"verdict": "send it", "reasons": []})
        verdict, category, reasons = run(reply)
        self.assertEqual(verdict, "inconclusive")
        self.assertIsNone(category)
        self.assertIn("unusable", " ".join(reasons))

    def test_invalid_json_rules_inconclusive(self):
        verdict, _category, reasons = run("not json at all")
        self.assertEqual(verdict, "inconclusive")
        self.assertIn("unusable", " ".join(reasons))

    def test_missing_verdict_rules_inconclusive(self):
        verdict, _category, reasons = run(json.dumps({"reasons": []}))
        self.assertEqual(verdict, "inconclusive")
        self.assertIn("unusable", " ".join(reasons))


if __name__ == "__main__":
    unittest.main()
