"""CB2-216/217: selection includes the best and respects the cap."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from hortus import engine  # noqa: E402


POP = [
    (8.0, 18.0, 1.2, 2.0),
    (10.0, 24.0, 1.4, 2.5),
    (12.0, 30.0, 1.6, 3.0),
    (14.0, 36.0, 1.8, 3.5),
    (16.0, 42.0, 2.0, 4.0),
]


class TestSelection(unittest.TestCase):
    def test_top_scoring_individual_is_selected(self):
        best = max(POP, key=engine.fitness)
        selected = engine.select_parents(POP, parent_count=3)
        self.assertIn(best, selected)

    def test_never_more_than_configured(self):
        selected = engine.select_parents(POP, parent_count=2)
        self.assertEqual(len(selected), 2)
        selected = engine.select_parents(POP, parent_count=99)
        self.assertEqual(len(selected), len(POP))


if __name__ == "__main__":
    unittest.main()
