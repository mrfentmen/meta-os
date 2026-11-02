"""Ladder level tests (CB2-166..167, 170, 175). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import ladder  # noqa: E402


class LadderLevelTests(unittest.TestCase):
    def test_level_zero_lists_the_next_required_evidence(self):
        self.assertEqual(ladder.required_evidence(0), ["pinned_source_claims"])
        self.assertEqual(ladder.missing_evidence(0, []),
                         ["pinned_source_claims"])

    def test_complete_evidence_promotes_level_one_to_two(self):
        self.assertEqual(
            ladder.promote(1, 2, "computational_result", "unverified"), 2)

    def test_removing_a_required_entry_demotes_the_computed_level(self):
        full = [
            {"kind": "pinned_source_claims", "verification_status": "unverified"},
            {"kind": "computational_result", "verification_status": "unverified"},
        ]
        self.assertEqual(ladder.level_from_evidence(full), 2)
        self.assertEqual(ladder.level_from_evidence(full[:-1]), 1)

    def test_level_names_match_the_documented_zero_to_six_ladder(self):
        self.assertEqual(sorted(ladder.LEVELS), list(range(7)))
        self.assertEqual(
            [ladder.LEVELS[i]["status"] for i in range(7)],
            ["Idea", "Evidence supported", "Computationally tested",
             "Independently reproduced", "Experimentally validated",
             "Independently replicated", "Established application"])


if __name__ == "__main__":
    unittest.main()
