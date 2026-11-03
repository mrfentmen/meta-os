"""CB2-181/182/196: RMSE gate decision and evidence-level assignment."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import verify  # noqa: E402


class TestGate(unittest.TestCase):
    def test_dress_rehearsal_shape_matches(self):
        gate = verify.gate_decision(0.818, 1.5)
        self.assertTrue(gate["match"])
        self.assertEqual(gate["decision"], "match")
        self.assertEqual(gate["evidence_level"], 2)

    def test_above_threshold_no_match(self):
        gate = verify.gate_decision(2.0, 1.5)
        self.assertFalse(gate["match"])
        self.assertEqual(gate["decision"], "no-match")
        self.assertNotEqual(gate.get("decision"), "confirmed")

    def test_matching_reproduction_assigns_level_two(self):
        self.assertEqual(verify.assign_evidence_level(0.818, 1.5), 2)
        self.assertEqual(verify.assign_evidence_level(2.0, 1.5), 0)

    def test_bad_threshold_refused(self):
        with self.assertRaises(ValueError):
            verify.gate_decision(0.1, -1)


if __name__ == "__main__":
    unittest.main()
