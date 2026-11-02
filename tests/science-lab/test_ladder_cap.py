"""Ladder cap tests (CB2-168..169). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import ladder  # noqa: E402


class LadderCapTests(unittest.TestCase):
    def test_automated_path_stops_at_level_three(self):
        self.assertEqual(ladder.MAX_AUTOMATED_LEVEL, 3)
        self.assertEqual(ladder.cap_for_experiment("reproduced"), 3)
        with self.assertRaisesRegex(NotImplementedError, "level 4"):
            ladder.promote(3, 4, "human_physical_experiment", "unverified")

    def test_fake_fixture_never_promotes(self):
        evidence = [
            {"kind": "pinned_source_claims", "verification_status": "unverified"},
            {"kind": "computational_result", "verification_status": "unverified"},
            {"kind": "independent_reproduction",
             "verification_status": "reproduced", "fake": True},
        ]
        self.assertEqual(ladder.level_from_evidence(evidence), 2)


if __name__ == "__main__":
    unittest.main()
