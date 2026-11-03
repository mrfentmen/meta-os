"""CB2-218/219: five generations emit ordered records and pass verify."""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from hortus import engine, records, verifier  # noqa: E402


SEED_POP = [
    (8.0, 20.0, 1.2, 2.0),
    (9.0, 22.0, 1.4, 2.5),
    (10.0, 25.0, 1.5, 3.0),
    (11.0, 28.0, 1.7, 3.5),
    (12.0, 30.0, 1.8, 4.0),
    (13.0, 32.0, 1.9, 4.2),
]


def _run(path):
    population = list(SEED_POP)
    populations = []
    for gen in range(1, 6):
        next_pop = engine.population_step(
            population, population_size=6, seed=200 + gen,
            mutation_rate=0.0)
        parent_ids = ["G%d-%d" % (gen - 1, i)
                      for i in range(len(population))]
        child_ids = ["G%d-%d" % (gen, i) for i in range(len(next_pop))]
        records.write_generation(path, gen, parent_ids, child_ids)
        population = next_pop
        populations.append(population)
    return populations


class TestFiveGenerations(unittest.TestCase):
    def test_generation_numbers_run_one_to_five(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "generations.jsonl")
            _run(path)
            rows = records.list_generations(path)
            self.assertEqual([r["generation"] for r in rows],
                             [1, 2, 3, 4, 5])

    def test_every_generation_passes_verifier(self):
        with tempfile.TemporaryDirectory() as td:
            path = os.path.join(td, "generations.jsonl")
            populations = _run(path)
            for gen, population in enumerate(populations, start=1):
                for genome in population:
                    result = verifier.verify_child(genome)
                    self.assertTrue(result["passed"],
                                    "generation %d %r: %r"
                                    % (gen, genome, result["violations"]))


if __name__ == "__main__":
    unittest.main()
