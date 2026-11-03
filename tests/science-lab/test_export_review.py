"""CB2-194/195: review contract and the human-only ladder guard."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import export  # noqa: E402


class TestReviewExport(unittest.TestCase):
    def test_review_contract_fields(self):
        doc = export.export_session("CYCLE-EXAMPLE-001", write=False)
        expected = ("cycle_id", "phase", "gate_state", "claims",
                    "claims_by_level", "verdicts", "display", "sources",
                    "honesty")
        for key in expected:
            self.assertIn(key, doc)

    def test_levels_above_three_never_auto_confirmed(self):
        for level in (4, 5, 6):
            row = export.claim_display({
                "claim_id": "H-%d" % level,
                "statement": "human-only claim",
                "level": level,
                "basis": "physical experiment",
                "verdict": "confirmed",
            })
            self.assertFalse(row["automatically_confirmed"])
            self.assertIn("human-only", row["colour"])

    def test_level_two_reproduction_can_be_auto_confirmed(self):
        row = export.claim_display({
            "claim_id": "A-2",
            "statement": "reproduced",
            "level": 2,
            "basis": "blind re-run",
            "verdict": "reproduced",
        })
        self.assertTrue(row["automatically_confirmed"])


if __name__ == "__main__":
    unittest.main()
