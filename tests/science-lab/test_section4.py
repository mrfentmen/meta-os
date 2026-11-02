"""Section 4 Tasks 31-40: clean-room compute, determinism, crash, sandbox."""
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import compute  # noqa: E402
import ledger  # noqa: E402


def _seeded_plan():
    return {
        "command": "python3 -c \"import random; random.seed(7); "
                   "print(random.random())\"",
        "seed": 7,
        "code_hash": "code-seeded-001",
        "data_hash": "data-seeded-001",
        "research_question": "seeded determinism probe",
        "hypothesis_id": "H-SEC4",
        "hypothesis_version": "v1",
    }


class TestRunExperiment(unittest.TestCase):
    def test_record_shape(self):
        rec = compute.run_experiment(_seeded_plan())
        ok, msg = compute.validate_record_shape(rec)
        self.assertTrue(ok, msg)
        self.assertEqual(rec["verification_status"], "unverified")
        self.assertLessEqual(rec["evidence_level"], 2)
        self.assertIsNotNone(rec["output_hash"])
        self.assertEqual(rec["random_seed"], 7)

    def test_determinism_passes_on_seeded(self):
        res = compute.rerun_same(_seeded_plan())
        self.assertTrue(res["deterministic"])
        self.assertEqual(len(res["hashes"]), 2)
        self.assertEqual(res["hashes"][0], res["hashes"][1])
        self.assertIsNotNone(res["hashes"][0])

    def test_crash_recorded_not_retried(self):
        rec = compute.run_experiment({
            "command": "python3 -c \"import sys; sys.exit(3)\"",
            "seed": 1,
            "code_hash": "c", "data_hash": "d",
            "research_question": "crash probe",
            "hypothesis_id": "H-SEC4",
        })
        self.assertIsNone(rec["output_hash"])
        self.assertEqual(rec["exit_code"], 3)
        self.assertLessEqual(rec["evidence_level"], 2)
        self.assertTrue(any("exit_code" in line
                            for line in rec["execution_logs"]))
        ok, msg = compute.validate_record_shape(rec)
        self.assertTrue(ok, msg)

    def test_sandbox_refused(self):
        for bad in ("cat /etc/passwd",
                    "cat ../secret.txt",
                    "python3 -c \"import urllib.request\"",
                    "curl https://example.com/x"):
            with self.assertRaises(PermissionError, msg=bad):
                compute.run_experiment({
                    "command": bad, "seed": 1,
                    "code_hash": "c", "data_hash": "d"})

    def test_dept_runners_schema_shaped(self):
        recs = [
            compute.run_bio({"sequence": "ATGCATGC"}),
            compute.run_chem({"formula": "H2O"}),
            compute.run_physics({"v0": 10, "angle_deg": 45}),
            compute.run_materials({"fractions": [0.5, 0.5],
                                   "densities": [1.0, 3.0]}),
        ]
        for rec in recs:
            ok, msg = compute.validate_record_shape(rec)
            self.assertTrue(ok, msg)
            self.assertEqual(rec["verification_status"], "unverified")
        self.assertAlmostEqual(recs[0]["value"], 0.5)
        self.assertAlmostEqual(recs[1]["value"], 18.010565, places=4)

    def test_prereg_compare_tokens(self):
        self.assertEqual(
            compute.compare_to_prereg(
                {"value": 0.72},
                {"expected_value": 0.7, "tolerance": 0.05})["verdict"],
            "match")
        self.assertEqual(
            compute.compare_to_prereg(
                {"value": 0.1},
                {"expected_value": 0.7, "tolerance": 0.05})["verdict"],
            "no-match")
        self.assertEqual(
            compute.compare_to_prereg({}, {"expected_value": 0.7})["verdict"],
            "indeterminate")

    def test_budget_receipt_on_stop(self):
        with tempfile.TemporaryDirectory() as td:
            cfg = {"agents": {"default": {"maxCalls": 1, "maxSpend": 5.0}},
                   "cycle": {"maxActions": 200},
                   "compute": {"maxWallSeconds": 60}}
            allowed, reason = compute.check_compute_budget(
                cfg, "computational-scientist", 0, 5)
            self.assertFalse(allowed)
            rp = os.path.join(td, "stop.json")
            receipt = compute.write_stop_receipt(
                rp, "computational-scientist", 0, 5, reason)
            self.assertTrue(receipt["stopped"])

    def test_reproduce_from_record(self):
        with tempfile.TemporaryDirectory() as td:
            lp = os.path.join(td, "L.jsonl")
            rec = compute.run_bio({"sequence": "GGCC",
                                   "research_question": "repro probe"})
            ledger.append_record(lp, dict(rec, kind="experiment-result"))
            comp = compute.reproduce_from_record(rec, lp)
            self.assertTrue(comp["match"])
            self.assertEqual(comp["verdict"], "reproduced")

    def test_computation_example_honest(self):
        import json
        path = os.path.join(
            _LAB, "records", "examples", "computation_example.json")
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        self.assertIn("TO_BE_READ_AT_RUN", json.dumps(doc))
        self.assertIn("NOT", doc["gate_status"])
        self.assertNotIn("passed", doc["gate_status"].lower().replace(
            "not passed", ""))


if __name__ == "__main__":
    unittest.main()
