"""Cycle transition tests (CB2-160..162). Temp ledger only."""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import cycle  # noqa: E402


def _inputs(c):
    c["inputs"].update({
        "sources": ["S1"], "hypotheses": ["H1"],
        "compute_results": {"v": 1}, "critique": {"issues": ["x"]},
        "verification": {"status": "reproduced"},
    })
    return c


class TransitionTests(unittest.TestCase):
    def test_documented_forward_transitions_are_accepted_one_by_one(self):
        c = _inputs(cycle.new_cycle("C1", "Q?"))
        ledger_path = tempfile.mktemp(suffix=".jsonl")
        for target in ("literature", "hypotheses", "cheap-computations",
                       "critic", "verification", "sealing"):
            ok, message = cycle.can_transition(c, target)
            self.assertTrue(ok, message)
            cycle.transition(c, target, "forward", ledger_path)
        self.assertEqual(c["phase"], "sealing")

    def test_backwards_transition_is_rejected(self):
        c = _inputs(cycle.new_cycle("C2", "Q?"))
        c["phase"] = "hypotheses"
        ok, message = cycle.can_transition(c, "literature")
        self.assertFalse(ok)
        self.assertIn("backwards", message)

    def test_skipping_a_phase_is_rejected(self):
        c = _inputs(cycle.new_cycle("C3", "Q?"))
        ok, message = cycle.can_transition(c, "cheap-computations")
        self.assertFalse(ok)
        self.assertIn("skip", message)


if __name__ == "__main__":
    unittest.main()
