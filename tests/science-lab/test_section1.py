"""Section 1 (tasks 1-10): schemas round-trip, ledger chain, ladder guard, cycle gates.

stdlib unittest only. Run from repo root:
    python3 -m unittest discover -s tests/science-lab -v
"""
import json
import os
import sys
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import ladder  # noqa: E402
import ledger  # noqa: E402
import cycle  # noqa: E402
import lab_config  # noqa: E402


class TestSchemasRoundTrip(unittest.TestCase):
    def test_experiment_schema_loads(self):
        p = os.path.join(_LAB, "schemas", "experiment.schema.json")
        d = json.load(open(p))
        self.assertIn("properties", d)
        for f in ("research_question", "input_hash", "random_seed",
                  "verification_status", "evidence_level"):
            self.assertIn(f, d["properties"])

    def test_hypothesis_schema_requires_disproof(self):
        p = os.path.join(_LAB, "schemas", "hypothesis.schema.json")
        d = json.load(open(p))
        self.assertIn("disproof_condition", d.get("required", []))
        self.assertIn("evidence_level", d.get("properties", {}))

    def test_cycle_schema_loads(self):
        p = os.path.join(_LAB, "schemas", "cycle.schema.json")
        d = json.load(open(p))
        self.assertIn("properties", d)
        self.assertIn("step-8-unimplemented", json.dumps(d))

    def test_experiment_record_validates_required_keys(self):
        schema = json.load(open(os.path.join(
            _LAB, "schemas", "experiment.schema.json")))
        rec = {k: ("x" if k not in ("evidence_level",) else 2)
               for k in schema["required"]}
        # fill typed fields to plausible values
        rec.update({"evidence_level": 2, "random_seed": 1,
                    "verification_status": "unverified",
                    "output_hash": None, "parameters": {},
                    "execution_logs": [], "software": {"name": "s", "version": "1"},
                    "model": {"name": "m", "version": "1"}})
        for k in schema["required"]:
            self.assertIn(k, rec)


class TestLedgerChain(unittest.TestCase):
    def test_append_and_verify(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "ledger.jsonl")
            e1 = ledger.append_record(p, {"kind": "cycle.start", "cycle": "C1"})
            e2 = ledger.append_record(p, {"kind": "cycle.advance", "cycle": "C1"})
            self.assertEqual(e1["prev_hash"], "GENESIS")
            self.assertEqual(e2["prev_hash"], e1["entry_hash"])
            ok, msg = ledger.verify_chain(p)
            self.assertTrue(ok, msg)

    def test_tamper_breaks_chain(self):
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "ledger.jsonl")
            ledger.append_record(p, {"kind": "a"})
            ledger.append_record(p, {"kind": "b"})
            lines = open(p).read().strip().split("\n")
            obj = json.loads(lines[0])
            obj["kind"] = "tampered"
            lines[0] = json.dumps(obj, sort_keys=True)
            open(p, "w").write("\n".join(lines) + "\n")
            ok, _ = ledger.verify_chain(p)
            self.assertFalse(ok)

    def test_missing_file_reads_empty(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(ledger.read_all(os.path.join(td, "nope.jsonl")), [])


class TestLadderGuardBlocks(unittest.TestCase):
    def test_blocks_over_level_export(self):
        with self.assertRaises(ValueError):
            ladder.assert_export_allowed(2, 3)

    def test_allows_equal_and_under(self):
        ladder.assert_export_allowed(2, 2)
        ladder.assert_export_allowed(3, 1)

    def test_cap_unverified_is_2(self):
        self.assertEqual(ladder.cap_for_experiment("unverified", False), 2)
        self.assertEqual(ladder.cap_for_experiment("reproduced", False), 3)


class TestCycleGates(unittest.TestCase):
    def test_missing_critique_blocks_verification(self):
        c = cycle.new_cycle("C1", "q?")
        c["inputs"] = {"problem_statement": "q?"}
        ok, msg = cycle.can_transition(c, "verification")
        self.assertFalse(ok)
        self.assertIn("critique", msg.lower())

    def test_step8_is_unimplemented(self):
        c = cycle.new_cycle("C1", "q?")
        ok, msg = cycle.can_transition(c, cycle.STEP_8)
        self.assertFalse(ok)
        self.assertIn("UNIMPLEMENTED", msg)

    def test_human_gate_parks_and_resumes(self):
        c = cycle.new_cycle("C1", "q?")
        c["phase"] = "sealing"
        c["inputs"]["sealed_record"] = {"id": "s1"}
        parked = cycle.park_for_human_gate(c, "wetlab")
        self.assertEqual(parked["gate_state"], "human-gated")
        with self.assertRaises(ValueError):
            cycle.transition(dict(parked), "wetlab", "try auto",
                             os.path.join(tempfile.gettempdir(), "lab-test-ledger.jsonl"))
        resumed = cycle.resume_with_decision(
            parked, {"gate": "wetlab", "approved": True, "decided_by": "human"})
        self.assertEqual(resumed["phase"], "wetlab")

    def test_budget_cap_writes_receipt(self):
        cfg = lab_config.load_config(os.path.join(_LAB, "lab_config.json"))
        ok, msg = lab_config.check_budget(cfg, "literature-researcher",
                                          calls=1000, spend=1000.0)
        self.assertFalse(ok)
        with tempfile.TemporaryDirectory() as td:
            rp = os.path.join(td, "receipt.json")
            lab_config.write_receipt(rp, "literature-researcher",
                                     calls=1000, spend=1000.0, reason=msg)
            self.assertTrue(json.load(open(rp))["stopped"])


if __name__ == "__main__":
    unittest.main()
