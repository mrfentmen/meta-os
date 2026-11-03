"""CB2-203/204/205/224: one Hortus breeding step."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from hortus import engine  # noqa: E402


PARENT_A = (8.0, 20.0, 1.2, 2.0)
PARENT_B = (14.0, 35.0, 2.0, 4.0)


class TestBreedingStep(unittest.TestCase):
    def test_child_genes_come_only_from_parents(self):
        child = engine.breeding_step(PARENT_A, PARENT_B, seed=11,
                                     mutation_rate=0.0)
        for gene, a, b in zip(child["genome"], PARENT_A, PARENT_B):
            self.assertIn(gene, (a, b))

    def test_same_seed_reproduces_same_child(self):
        first = engine.breeding_step(PARENT_A, PARENT_B, seed=77,
                                     mutation_rate=0.0)
        second = engine.breeding_step(PARENT_A, PARENT_B, seed=77,
                                      mutation_rate=0.0)
        self.assertEqual(first["genome"], second["genome"])

    def test_different_seeds_can_differ(self):
        children = {
            engine.breeding_step(PARENT_A, PARENT_B, seed=seed,
                                 mutation_rate=0.0)["genome"]
            for seed in range(10)
        }
        self.assertGreaterEqual(len(children), 2)

    def test_crossover_result_is_pinned(self):
        child = engine.breeding_step(PARENT_A, PARENT_B, seed=3,
                                     mutation_rate=0.0)["genome"]
        self.assertEqual(child, (8.0, 35.0, 1.2, 4.0))


if __name__ == "__main__":
    unittest.main()
