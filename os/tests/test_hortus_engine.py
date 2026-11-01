"""Hortus breeding engine: evolution, verifier gate, run records.

Hortus is the Science Lab's candidate generator
(worlds/science-lab/hortus). These tests pin the three claims
the engine is allowed to make:

1. Selection pressure works: on a fixed seed, the best score
   improves over generations against the deterministic toy
   scorer (and, with elitism, never regresses).
2. The verifier gate bites: a genome constructed to win under
   the training conditions by hugging the fin-spacing floor is
   rejected when re-scored under held-out environments with a
   tighter floor, even though it is feasible and beats the
   reference design at home.
3. The run log is append-only and complete: births, deaths, and
   generation records reconstruct the whole family tree, with
   nothing lost and nothing rewritten.

Nothing here proves anything about real heatsinks: the scorer
is an analytic toy model and model.py says so.
"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, ".")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "worlds", "science-lab"))

from hortus import engine, model, records, verifier  # noqa: E402


class HortusRunTest(unittest.TestCase):
    """One shared short run (60 generations) for the run-level
    assertions; the full 300-generation demo log is produced by
    hortus/run_demo.py, not by the test suite."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = os.path.join(cls.tmp.name, "run.jsonl")
        cls.summary = engine.run_evolution(
            cls.path, seed=20261101, generations=60,
            population_size=48)
        cls.recs = records.load_records(cls.path)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_selection_pressure_improves_best_score(self):
        self.assertGreater(self.summary["final_best_score"],
                           self.summary["first_best_score"])

    def test_best_score_never_regresses_with_elites(self):
        gens = [r for r in self.recs if r["kind"] == "generation"]
        self.assertEqual(len(gens), 61)
        bests = [g["best_score"] for g in gens]
        self.assertEqual(bests, sorted(bests))

    def test_run_is_deterministic_for_a_seed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path_a = os.path.join(tmp, "a.jsonl")
            path_b = os.path.join(tmp, "b.jsonl")
            engine.run_evolution(path_a, seed=7, generations=10,
                                 population_size=24, verify=False)
            engine.run_evolution(path_b, seed=7, generations=10,
                                 population_size=24, verify=False)
            gens_a = [r["best_score"] for r in records.load_records(path_a)
                      if r["kind"] == "generation"]
            gens_b = [r["best_score"] for r in records.load_records(path_b)
                      if r["kind"] == "generation"]
            self.assertEqual(gens_a, gens_b)

    def test_records_reconstruct_the_whole_family_tree(self):
        tree = records.reconstruct(self.recs)
        births = [r for r in self.recs if r["kind"] == "birth"]
        deaths = [r for r in self.recs if r["kind"] == "death"]
        self.assertEqual(len(tree["organisms"]), len(births))
        self.assertEqual(
            len(births) - len(deaths),
            len(tree["final_population"]))
        for org in tree["organisms"].values():
            for parent in org["parents"]:
                self.assertIn(parent, tree["organisms"])
        self.assertEqual(tree["champion_id"],
                         self.summary["champion_id"])
        self.assertIsNotNone(tree["verdict"])

    def test_records_are_append_only(self):
        with open(self.path, "rb") as fh:
            before = fh.read()
        writer = records.RecordWriter(self.path)
        writer.write("generation", generation=999, population=0,
                     best_score=0.0, mean_score=0.0, champion=-1)
        writer.close()
        with open(self.path, "rb") as fh:
            after = fh.read()
        self.assertTrue(after.startswith(before))
        self.assertGreater(len(after), len(before))

    def test_champion_is_capped_at_ladder_level_2(self):
        self.assertEqual(engine.EVIDENCE_LEVEL_CAP, 2)
        run_start = self.recs[0]
        self.assertEqual(run_start["kind"], "run_start")
        self.assertEqual(run_start["evidence_level_cap"], 2)
        self.assertTrue(run_start["is_prediction"])
        verdict = [r for r in self.recs if r["kind"] == "verdict"]
        self.assertEqual(len(verdict), 1)
        self.assertEqual(verdict[0]["evidence_level_cap"], 2)

    def test_evolved_champion_passes_the_verifier(self):
        self.assertTrue(self.summary["verdict"]["passed"])
        self.assertEqual(self.summary["verdict"]["champion_status"],
                         "verified-candidate")


class HortusVerifierTest(unittest.TestCase):
    def test_verifier_rejects_boundary_hugging_overfit(self):
        # Constructed overfit: 20 fins at 4.0 mm leaves a 1.053 mm
        # gap - feasible under the training floor (1.0 mm) and
        # stronger than the reference design at home, but dead
        # under every held-out floor (1.5 mm).
        genome = (20.0, 20.0, 4.0, 2.0)
        geo = model.geometry(genome, model.TRAIN_ENV)
        self.assertTrue(geo["spacing_ok"])
        self.assertTrue(geo["mass_ok"])
        self.assertGreater(
            model.heat_watts(genome, model.TRAIN_ENV),
            model.heat_watts(model.REFERENCE_GENOME, model.TRAIN_ENV))
        verdict = verifier.verify_champion(genome)
        self.assertFalse(verdict["passed"])
        self.assertEqual(verdict["champion_status"], "rejected")
        self.assertTrue(all(not c["spacing_ok"]
                            for c in verdict["checks"]))

    def test_scorer_is_deterministic(self):
        genome = (12.0, 30.0, 1.2, 2.5)
        self.assertEqual(model.score(genome, model.TRAIN_ENV),
                         model.score(genome, model.TRAIN_ENV))


if __name__ == "__main__":
    unittest.main()
