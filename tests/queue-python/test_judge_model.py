"""Tests for the judge's prompted ruling (judge.rule_with_model,
v2 wiring). Offline: chat_fn is faked. The crew-level fallback to
combine() on a transport failure is exercised via the fake raising."""
import json
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import judge  # noqa: E402

FIRST = {"assessment": {"category": "visible flame"},
         "observations": [{"category": "visible flame"}]}
REVIEW = {"assessment": {"category": "visible flame"},
          "observations": [{"category": "visible flame"}]}


def reply(verdict, category="visible flame", reasons=("flames in both",)):
    return lambda prompt: json.dumps({
        "verdict": verdict, "category": category,
        "reasons": list(reasons), "confidence": None})


class RuleWithModelTests(unittest.TestCase):
    def test_confirm_maps_to_confirmed(self):
        verdict, category, reasons = judge.rule_with_model(
            "ignis", FIRST, REVIEW, reply("confirm"))
        self.assertEqual(verdict, "confirmed")
        self.assertEqual(category, "visible flame")
        self.assertTrue(any("model judge" in r for r in reasons))

    def test_reject_maps_to_cleared(self):
        verdict, _, _ = judge.rule_with_model(
            "ignis", FIRST, REVIEW, reply("reject", "clear scene"))
        self.assertEqual(verdict, "cleared")

    def test_investigate_maps_to_inconclusive(self):
        verdict, _, _ = judge.rule_with_model(
            "ignis", FIRST, REVIEW, reply("investigate"))
        self.assertEqual(verdict, "inconclusive")

    def test_garbage_reply_never_confirms(self):
        verdict, _, _ = judge.rule_with_model(
            "ignis", FIRST, REVIEW, lambda prompt: "the flames, probably")
        self.assertEqual(verdict, "inconclusive")

    def test_transport_failure_raises_to_caller(self):
        def boom(prompt):
            raise RuntimeError("HTTP 500")
        with self.assertRaises(RuntimeError):
            judge.rule_with_model("ignis", FIRST, REVIEW, boom)

    def test_prompt_carries_both_readings(self):
        seen = {}

        def capture(prompt):
            seen["prompt"] = prompt
            return reply("confirm")(prompt)
        judge.rule_with_model("ignis", FIRST, REVIEW, capture)
        self.assertIn("First reading", seen["prompt"])
        self.assertIn("Second reading", seen["prompt"])
        self.assertIn("visible flame", seen["prompt"])


if __name__ == "__main__":
    unittest.main()
