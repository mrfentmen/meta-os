"""CB2-206/207: mutation at maximum and at zero."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from hortus import engine  # noqa: E402


A = (8.0, 20.0, 1.2, 2.0)
B = (14.0, 35.0, 2.0, 4.0)


class TestMutation(unittest.TestCase):
    def test_maximum_mutation_differs_from_pure_crossover(self):
        pure = engine.breeding_step(A, B, seed=42, mutation_rate=0.0)
        mutated = engine.breeding_step(A, B, seed=42, mutation_rate=1.0)
        self.assertNotEqual(mutated["genome"], pure["genome"])

    def test_zero_mutation_stays_with_parents(self):
        child = engine.breeding_step(A, B, seed=42, mutation_rate=0.0)
        for gene, a, b in zip(child["genome"], A, B):
            self.assertIn(gene, (a, b))

    def test_mutation_rate_zero_is_identity(self):
        self.assertEqual(engine.mutate_step(A, seed=1, mutation_rate=0.0), A)


if __name__ == "__main__":
    unittest.main()
