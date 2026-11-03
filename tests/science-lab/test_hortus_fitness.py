"""CB2-214/215: deterministic fitness and a hand-checked value."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from hortus import engine, model  # noqa: E402


class TestFitness(unittest.TestCase):
    def test_reference_scores_its_unpenalised_heat(self):
        env = model.TRAIN_ENV
        geo = model.geometry(model.REFERENCE_GENOME, env)
        self.assertGreaterEqual(geo["spacing_m"], env["margin_spacing_m"])
        self.assertLessEqual(geo["mass_kg"], env["mass_cap_kg"])
        expected = model.heat_watts(model.REFERENCE_GENOME, env)
        self.assertAlmostEqual(engine.fitness(model.REFERENCE_GENOME),
                               expected, places=12)

    def test_fitness_is_deterministic(self):
        first = engine.fitness(model.REFERENCE_GENOME)
        for _ in range(3):
            self.assertEqual(engine.fitness(model.REFERENCE_GENOME), first)


if __name__ == "__main__":
    unittest.main()
