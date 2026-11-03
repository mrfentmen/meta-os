"""Reasoning variable tests (CB2-128..129). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning  # noqa: E402


class VariableTests(unittest.TestCase):
    def test_two_named_variables_keep_order(self):
        self.assertEqual(
            reasoning.extract_variables(
                "As `temperature` rises, `pressure` rises"),
            ["temperature", "pressure"])
        self.assertEqual(reasoning.extract_variables("X and Y differ"),
                         ["X", "Y"])

    def test_no_variable_is_untestable(self):
        record = {
            "id": "H1", "research_question": "What happens?",
            "proposed_explanation": "Things happen.",
            "measurable_prediction": "Something may change.",
            "alternative_explanation": "Nothing happens.",
            "disproof_condition": "No change.",
            "evidence_level": 0,
        }
        self.assertEqual(reasoning.extract_variables("Things happen."), [])
        self.assertEqual(reasoning.classify_hypothesis(record), "untestable")


if __name__ == "__main__":
    unittest.main()
