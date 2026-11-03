"""Hypothesis evidence-link tests (CB2-140..141). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning  # noqa: E402


class EvidenceLinkTests(unittest.TestCase):
    def test_two_source_ids_are_kept_after_round_trip_through_dict(self):
        linked = reasoning.link_evidence(
            {"id": "H1", "sources": ["S0"]}, ["S1", "S2"],
            known_source_ids=["S0", "S1", "S2"])
        rebuilt = dict(linked)
        self.assertEqual(rebuilt["sources"], ["S0", "S1", "S2"])

    def test_unknown_source_id_is_refused(self):
        with self.assertRaisesRegex(ValueError, "S9"):
            reasoning.link_evidence(
                {"id": "H1", "sources": []}, ["S9"],
                known_source_ids=["S1"])


if __name__ == "__main__":
    unittest.main()
