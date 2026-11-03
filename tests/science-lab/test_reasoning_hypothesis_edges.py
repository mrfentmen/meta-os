"""Hypothesis edge tests (CB2-126..127). Offline."""
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
        "id": "H1", "research_question": "Does X change Y?",
        "proposed_explanation": "`X` increases `Y`",
        "measurable_prediction": "`Y` increases by 2",
        "alternative_explanation": "No causal link",
        "disproof_condition": "No reproducible change in Y",
        "evidence_level": 0, "sources": [],
    }
    item.update(kw)
    return item


class HypothesisEdgeTests(unittest.TestCase):
    def test_missing_statement_is_rejected(self):
        record = hypothesis()
        record.pop("proposed_explanation")
        with self.assertRaisesRegex(ValueError, "statement"):
            reasoning.parse_hypothesis(record)

    def test_parsed_hypothesis_validates_against_schema(self):
        parsed = reasoning.parse_hypothesis(hypothesis())
        self.assertEqual(reasoning.validate_hypothesis_against_schema(parsed),
                         [])


if __name__ == "__main__":
    unittest.main()
