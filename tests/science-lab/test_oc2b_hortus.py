"""OC2B Hortus runs 001-003 (Sections 12-13, tasks 276-325).

Verifies the filed run packs under labs/hortus/runs without touching
the read-only engine: CSVs parse with generations 1-8, figures exist,
winner hashes recompute, pack hashes verify (zeroed-line scheme), the
engine reproduces each CSV from the recorded seed in a temp dir, and
each record carries its seed, selection, error, and pack-hash lines.

stdlib unittest only. Run from repo root:
    python3 -m unittest discover -s tests/science-lab -p "test_oc2b_hortus.py" -v
"""
import csv
import hashlib
import json
import os
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
_RUNS = os.path.join(_REPO, "labs", "hortus", "runs")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

from hortus import engine, model, records as records_mod  # noqa: E402

EXPECTED = {
    "run-001": {"pop": 20, "calibrated": False,
                "final_best": 108.835191, "final_mean": 88.088470,
                "genome_sha": "e258d573537ee6ee241fa61d7161dd0ad160a"
                              "2c7eb348ec9dce5328e9adf8a65"},
    "run-002": {"pop": 40, "calibrated": False,
                "final_best": 115.783012, "final_mean": 92.876514,
                "genome_sha": "0f95218be2a816f6236c70fda929a62d8d58a"
                              "d16e3dbb16ca9c4e2f6cbf85092"},
    "run-003": {"pop": 20, "calibrated": True,
                "final_best": 38.021775, "final_mean": 29.961053,
                "genome_sha": "54c2e7cae76016ec71c9a84ef5a061d46ba1f"
                              "aed07572110828c99a9583728ec"},
}
SEED = 500001


def read_csv(run):
    with open(os.path.join(_RUNS, run, "generations.csv"), newline="",
              encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


class TestOc2bHortusPacks(unittest.TestCase):
    def test_csvs_parse_eight_rows(self):
        for run in ("run-001", "run-002", "run-003"):
            rows = read_csv(run)
            self.assertEqual([int(r["generation"]) for r in rows],
                             [1, 2, 3, 4, 5, 6, 7, 8], run)
            for r in rows:
                float(r["best_score"])
                float(r["mean_score"])

    def test_final_scores_match_expected(self):
        for run, exp in EXPECTED.items():
            rows = read_csv(run)
            self.assertAlmostEqual(float(rows[-1]["best_score"]),
                                   exp["final_best"], places=4, msg=run)
            self.assertAlmostEqual(float(rows[-1]["mean_score"]),
                                   exp["final_mean"], places=4, msg=run)

    def test_figures_exist_and_parse(self):
        for run in ("run-001", "run-002", "run-003"):
            p = os.path.join(_RUNS, run, "fitness.svg")
            root = ET.parse(p).getroot()
            polys = [e for e in root.iter()
                     if e.tag.endswith("polyline")]
            self.assertEqual(len(polys), 2, run)  # best + mean

    def test_winner_hash_recomputes(self):
        for run, exp in EXPECTED.items():
            with open(os.path.join(_RUNS, run, "winner.json"),
                     encoding="utf-8") as fh:
                d = json.load(fh)
            canon = json.dumps(d["genome"], separators=(",", ":")).encode()
            self.assertEqual(hashlib.sha256(canon).hexdigest(),
                             exp["genome_sha"], run)
            self.assertEqual(d["genome_sha256"], exp["genome_sha"], run)

    def test_pack_hash_verifies(self):
        for run in ("run-001", "run-002", "run-003"):
            d = os.path.join(_RUNS, run)
            table = {}
            filed_h = None
            with open(os.path.join(d, "pack.sha256"),
                         encoding="utf-8") as fh:
                man_lines = fh.read().split("\n")
            for line in man_lines:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                k, v = line.split(":", 1)
                if k.strip() == "pack-sha256":
                    filed_h = v.strip()
                else:
                    table[k.strip()] = v.strip()
            self.assertIsNotNone(filed_h, run)
            files = sorted(f for f in os.listdir(d)
                           if f != "pack.sha256"
                           and os.path.isfile(os.path.join(d, f)))
            self.assertEqual(sorted(table), files, run)
            h = hashlib.sha256()
            for f in files:
                with open(os.path.join(d, f), "rb") as fh:
                    b = fh.read()
                if f == "record.md":
                    b = b.replace(filed_h.encode(), b"0" * 64)
                self.assertEqual(hashlib.sha256(b).hexdigest(),
                                 table[f], "%s/%s" % (run, f))
                h.update(b)
            self.assertEqual(h.hexdigest(), filed_h, run)
            with open(os.path.join(d, "record.md"),
                         encoding="utf-8") as fh:
                rec = fh.read()
            self.assertIn("pack-sha256: " + filed_h, rec, run)

    def test_records_carry_required_lines(self):
        for run in ("run-001", "run-002", "run-003"):
            with open(os.path.join(_RUNS, run, "record.md"),
                         encoding="utf-8") as fh:
                rec = fh.read()
            self.assertIn("SEED=500001", rec, run)
            self.assertIn("select", rec.lower(), run)
            self.assertIn("pack-sha256: ", rec, run)
            low = rec.lower()
            self.assertTrue("no error" in low or "error" in low, run)

    def test_engine_reproduces_csv_from_seed(self):
        for run, exp in EXPECTED.items():
            with tempfile.TemporaryDirectory() as tmp:
                log = os.path.join(tmp, "records.jsonl")
                if exp["calibrated"]:
                    env = model.calibrated_train_env()
                    held = model.calibrated_held_out_envs()
                    label = "hortus-toy-fin-v1-calibrated"
                else:
                    env = dict(model.TRAIN_ENV)
                    held, label = None, None
                engine.run_evolution(
                    log, seed=SEED, generations=8,
                    population_size=exp["pop"], env=env,
                    held_out_envs=held, model_label=label)
                recs = records_mod.load_records(log)
                got = [(r["generation"], r["best_score"], r["mean_score"])
                       for r in recs if r.get("kind") == "generation"
                       and 1 <= r.get("generation", 0) <= 8]
                filed = read_csv(run)
                self.assertEqual(len(got), 8, run)
                for (g, b, m), f in zip(
                        sorted(got), filed):
                    self.assertEqual(g, int(f["generation"]), run)
                    self.assertAlmostEqual(b, float(f["best_score"]),
                                           places=6, msg=run)
                    self.assertAlmostEqual(m, float(f["mean_score"]),
                                           places=6, msg=run)


if __name__ == "__main__":
    unittest.main()
