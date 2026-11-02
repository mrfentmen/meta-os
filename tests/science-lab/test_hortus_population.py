"""CB2-208/209/223: population step size and empty-population refusal."""
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
    (8.0, 20.0, 1.2, 2.0),
    (9.0, 22.0, 1.4, 2.5),
    (10.0, 25.0, 1.5, 3.0),
    (11.0, 28.0, 1.7, 3.5),
    (12.0, 30.0, 1.8, 4.0),
    (13.0, 32.0, 1.9, 4.2),
]


class TestPopulationStep(unittest.TestCase):
    def test_six_parents_produce_configured_size(self):
        out = engine.population_step(POP, population_size=8, seed=5,
                                     mutation_rate=0.0)
        self.assertEqual(len(out), 8)

    def test_size_never_drifts_over_five_generations(self):
        population = list(POP)
        for gen in range(5):
            population = engine.population_step(
                population, population_size=6, seed=100 + gen,
                mutation_rate=0.0)
            self.assertEqual(len(population), 6, "generation %d" % gen)

    def test_empty_population_refused(self):
        with self.assertRaisesRegex(ValueError, "empty population"):
            engine.population_step([], population_size=6, seed=1)


if __name__ == "__main__":
    unittest.main()
