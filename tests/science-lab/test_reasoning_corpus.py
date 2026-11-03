"""Reasoning corpus test (CB2-146). Pure; 8 local fixtures."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning  # noqa: E402


def hypothesis(n, statement, prediction, **kw):
    item = {
        "id": "H%d" % n, "research_question": "Q%d?" % n,
        "proposed_explanation": statement,
        "measurable_prediction": prediction,
        "alternative_explanation": "Alternative %d" % n,
        "disproof_condition": "No change for H%d" % n,
        "evidence_level": 0,
    }
    item.update(kw)
    return item


class CorpusTests(unittest.TestCase):
    def test_eight_hypotheses_count_by_classification(self):
        records = [
            hypothesis(1, "`X` increases `Y`", "`Y` increases by 2"),
            hypothesis(2, "`A` raises `B`", "`B` rises by 3"),
            hypothesis(3, "`P` lowers `Q`", "`Q` falls by 1"),
            hypothesis(4, "Things happen.", "Something may change"),
            hypothesis(5, "The world varies.", "It might differ"),
            hypothesis(6, "`M` changes `N`", "`N` may change"),
            hypothesis(7, "`C` alters `D`", "`D` could vary"),
            hypothesis(8, "`E` increases `F`", "`F` increases by 1",
                       chain_cycle=True),
        ]
        counts = {}
        for record in records:
            name = reasoning.classify_hypothesis(record)
            counts[name] = counts.get(name, 0) + 1
        self.assertEqual(counts, {
            "testable": 3, "untestable": 2,
            "needs_refinement": 2, "cyclic": 1})


if __name__ == "__main__":
    unittest.main()
