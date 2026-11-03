"""Step-8 block tests (CB2-136..137). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning  # noqa: E402


class Step8Tests(unittest.TestCase):
    def test_step8_always_returns_blocking_marker(self):
        result = reasoning.step8_block()
        self.assertEqual(result["step"], reasoning.STEP_8)
        self.assertTrue(result["blocked"])
        self.assertEqual(result["marker"], "UNIMPLEMENTED")
        self.assertTrue(reasoning.requires_step8(8))
        self.assertTrue(reasoning.requires_step8({"phase": "step-8-unimplemented"}))

    def test_no_reasoning_function_returns_a_step8_result(self):
        record = {
            "id": "H1", "research_question": "Q?",
            "proposed_explanation": "`X` increases `Y`",
            "measurable_prediction": "`Y` increases by 2",
            "alternative_explanation": "No link",
            "disproof_condition": "No change",
            "evidence_level": 0,
        }
        parsed = reasoning.parse_hypothesis(record)
        self.assertNotIn("step", parsed)
        self.assertNotEqual(parsed.get("status"), "step-8-unimplemented")
        self.assertNotIn("step", reasoning.extract_prediction(
            record["measurable_prediction"]))


if __name__ == "__main__":
    unittest.main()
