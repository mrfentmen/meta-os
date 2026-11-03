"""Hypothesis confidence tests (CB2-144..145). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning  # noqa: E402


def hypothesis(**kw):
    item = {
        "id": "H1", "research_question": "Q?",
        "proposed_explanation": "`X` increases `Y`",
        "measurable_prediction": "`Y` increases by 2",
        "alternative_explanation": "No link",
        "disproof_condition": "No change", "evidence_level": 0,
    }
    item.update(kw)
    return item


class ConfidenceTests(unittest.TestCase):
    def test_unset_confidence_stays_null(self):
        self.assertIsNone(reasoning.parse_hypothesis(hypothesis())["confidence"])

    def test_out_of_range_confidence_is_rejected(self):
        for bad in (-0.1, 1.1, 2, True):
            with self.assertRaises(ValueError, msg=repr(bad)):
                reasoning.parse_hypothesis(hypothesis(confidence=bad))


if __name__ == "__main__":
    unittest.main()
