"""Hypothesis duplicate tests (CB2-149..150). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning  # noqa: E402


class DuplicateTests(unittest.TestCase):
    def test_same_statement_twice_is_flagged(self):
        records = [{"statement": "X rises with Y"},
                   {"statement": "X rises with Y"}]
        self.assertEqual(reasoning.find_duplicate_statements(records), [1])

    def test_whitespace_only_difference_is_a_duplicate(self):
        records = [{"statement": "  X   rises with Y. "},
                   {"statement": "x rises with y"}]
        self.assertEqual(reasoning.find_duplicate_statements(records), [1])


if __name__ == "__main__":
    unittest.main()
