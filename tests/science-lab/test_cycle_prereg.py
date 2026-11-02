"""Cycle pre-registration tests (CB2-163..165, 173). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import cycle  # noqa: E402


class PreregTests(unittest.TestCase):
    def test_same_question_and_plan_hash_the_same(self):
        one = cycle.preregistration_hash("Q?", {"test": "R2"})
        two = cycle.preregistration_hash("Q?", {"test": "R2"})
        self.assertEqual(one, two)

    def test_changing_the_plan_changes_the_hash(self):
        self.assertNotEqual(
            cycle.preregistration_hash("Q?", {"test": "R2"}),
            cycle.preregistration_hash("Q?", {"test": "R3"}))

    def test_edited_plan_is_detected_by_hash_mismatch(self):
        record = cycle.set_preregistration(
            cycle.new_cycle("C1", "Q?"), {"test": "R2"})
        self.assertTrue(cycle.verify_preregistration(record))
        record["preregistration"]["plan"] = {"test": "R3"}
        self.assertFalse(cycle.verify_preregistration(record))

    def test_question_whitespace_collapses_before_hashing(self):
        one = cycle.preregistration_hash("  Q   here? ", {"p": 1})
        two = cycle.preregistration_hash("Q here?", {"p": 1})
        self.assertEqual(one, two)


if __name__ == "__main__":
    unittest.main()
