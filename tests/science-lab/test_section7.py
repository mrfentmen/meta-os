"""Section 7 Tasks 61-70: breeding variants, selection, lineage.

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

import breeding  # noqa: E402
import compute  # noqa: E402
import ledger  # noqa: E402
import reasoning  # noqa: E402
import repository  # noqa: E402


def _parent_plan():
    return {
        "id": "P-T7-001",
        "research_question": "What is the exact molecular mass?",
        "hypothesis_id": "H-BREED-T7",
        "formula": "H2O",
        "seed": 700,
    }


def _setup(tmp_ledger):
    """Preregister FIRST, then run three real chem-formula variants.

    Order matters: reasoning.preregister refuses a late registration
    once results for the hypothesis exist, so the rule is filed
    before any run_variant call.
    """
    rule = _registered_rule(tmp_ledger)
    parent = _parent_plan()
    formulas = ["H2O", "CO2", "NaCl"]
    variants = []
    for i, formula in enumerate(formulas):
        variants.append(breeding.new_variant(
            "V%03d" % (i + 1), parent, {"formula": formula},
            700 + i, "recomputing the exact mass from an independent "
            "formula parse contradicting the stated value",
            hypothesis_id="H-BREED-T7"))
    results = [breeding.run_variant(v, ledger_path=tmp_ledger)
               for v in variants]
    return parent, variants, results, rule


def _registered_rule(tmp_ledger):
    return reasoning.preregister(
        "H-BREED-T7", "observed exact mass meets threshold",
        {"value": 20.0, "direction": ">="},
        "first archived formula parse per variant; max observed wins",
        tmp_ledger)


class TestVariantFalsifier(unittest.TestCase):
    def test_variant_without_falsifier_rejected(self):
        with self.assertRaises(ValueError):
            breeding.new_variant("V001", _parent_plan(), {}, 1, "")
        with self.assertRaises(ValueError):
            breeding.new_variant("V001", _parent_plan(), {}, 1, "   ")
        with self.assertRaises(ValueError):
            breeding.new_variant("V001", _parent_plan(), {}, 1, None)

    def test_propose_variants_rejects_falsifierless(self):
        plan = dict(_parent_plan())
        plan["claims"] = [
            {"claim": "mass scales with size",
             "disproof_condition": ""},
        ]
        out = breeding.propose_variants(plan, 3)
        self.assertEqual(len(out["variants"]) + len(out["rejected"]), 3)
        self.assertTrue(out["rejected"])
        for variant in out["variants"]:
            self.assertTrue(variant["falsifier"].strip())
            self.assertIn("hortus", variant)

    def test_propose_variants_range_guarded(self):
        with self.assertRaises(ValueError):
            breeding.propose_variants(_parent_plan(), 2)
        with self.assertRaises(ValueError):
            breeding.propose_variants(_parent_plan(), 6)


class TestVariantRunner(unittest.TestCase):
    def test_run_variant_same_records(self):
        with tempfile.TemporaryDirectory() as td:
            led = os.path.join(td, "ledger.jsonl")
            parent, variants, results, _ = _setup(led)
            self.assertEqual(len(results), 3)
            for item in results:
                ok, msg = compute.validate_record_shape(item["record"])
                self.assertTrue(ok, msg)
                self.assertLessEqual(item["record"]["evidence_level"], 2)
            entries = ledger.read_all(led)
            filed = [e for e in entries
                     if e.get("kind") == "experiment-result"]
            self.assertEqual(len(filed), 3)
            ok, msg = ledger.verify_chain(led)
            self.assertTrue(ok, msg)

    def test_run_variant_refuses_unrunnable(self):
        bad = breeding.new_variant("V009", _parent_plan(), {}, 5,
                                   "some falsifier")
        bad["plan"].pop("formula", None)
        with self.assertRaises(ValueError):
            breeding.run_variant(bad)


class TestSelectionGate(unittest.TestCase):
    def test_unregistered_rule_refused(self):
        with tempfile.TemporaryDirectory() as td:
            led = os.path.join(td, "ledger.jsonl")
            # Results WITHOUT any registration: no rule can be valid.
            parent = _parent_plan()
            variants = [breeding.new_variant(
                "V%03d" % (i + 1), parent, {"formula": f}, 700 + i,
                "independent recomputation contradicting the value",
                hypothesis_id="H-BREED-T7")
                for i, f in enumerate(["H2O", "CO2", "NaCl"])]
            results = [breeding.run_variant(v, ledger_path=led)
                       for v in variants]
            ad_hoc = {"threshold": 20.0, "direction": ">="}
            with self.assertRaises(ValueError):
                breeding.select_survivor(results, ad_hoc)
            fake_filed = {"kind": "preregistration",
                          "threshold": 20.0, "direction": ">=",
                          "entry_hash": "bogus" * 12}
            with self.assertRaises(ValueError):
                breeding.select_survivor(results, fake_filed,
                                         ledger_path=led)

    def test_selection_before_results_refused(self):
        with tempfile.TemporaryDirectory() as td:
            led = os.path.join(td, "ledger.jsonl")
            rule = _registered_rule(led)
            with self.assertRaises(ValueError):
                breeding.select_survivor(
                    [{"variant_id": "V001"}], rule)

    def test_selection_picks_extreme_pass(self):
        with tempfile.TemporaryDirectory() as td:
            led = os.path.join(td, "ledger.jsonl")
            _, _, results, rule = _setup(led)
            selection = breeding.select_survivor(
                results, rule, ledger_path=led)
            # H2O ~18.01 fails >= 20; CO2 ~43.99, NaCl ~57.96 pass;
            # survivor is the max (NaCl / V003).
            self.assertEqual(selection["survivor_id"], "V003")
            self.assertGreaterEqual(selection["survivor_measured"], 20.0)
            self.assertEqual(selection["rule_entry_hash"],
                             rule["entry_hash"])
            verdicts = {c["variant_id"]: c["verdict"]
                        for c in selection["candidates"]}
            self.assertEqual(verdicts["V001"], "no-match")
            self.assertEqual(verdicts["V003"], "match")


class TestLineage(unittest.TestCase):
    def test_lineage_verifies(self):
        with tempfile.TemporaryDirectory() as td:
            led = os.path.join(td, "ledger.jsonl")
            parent, variants, results, rule = _setup(led)
            selection = breeding.select_survivor(results, rule)
            lineage = breeding.build_lineage(parent, variants,
                                             selection)
            ok, msg = breeding.verify_lineage(
                lineage, parent, variants)
            self.assertTrue(ok, msg)
            self.assertEqual(lineage["survivor_id"], "V003")
            self.assertEqual(len(lineage["variants"]), 3)

    def test_lineage_tamper_detected(self):
        with tempfile.TemporaryDirectory() as td:
            led = os.path.join(td, "ledger.jsonl")
            parent, variants, results, rule = _setup(led)
            selection = breeding.select_survivor(results, rule)
            lineage = breeding.build_lineage(parent, variants,
                                             selection)
            tampered = dict(lineage, survivor_id="V001")
            ok, _ = breeding.verify_lineage(tampered, parent,
                                            variants)
            self.assertFalse(ok)
            wrong_parent = dict(parent, id="P-OTHER")
            ok, _ = breeding.verify_lineage(lineage, wrong_parent,
                                            variants)
            self.assertFalse(ok)


class TestDeadEnds(unittest.TestCase):
    def test_dead_ends_filed_at_true_level(self):
        with tempfile.TemporaryDirectory() as td:
            led = os.path.join(td, "ledger.jsonl")
            repo = os.path.join(td, "repository")
            _, _, results, rule = _setup(led)
            selection = breeding.select_survivor(results, rule)
            filed = breeding.preserve_dead_ends(
                results, selection["survivor_id"], base=repo)
            self.assertTrue(filed)
            negs = repository.query(kind="claims", level=2, base=repo)
            neg_ids = {c["claim_id"] for c in negs}
            self.assertIn("NEG-V001", neg_ids)
            self.assertNotIn("NEG-V003", neg_ids)
            exps = repository.query(kind="experiments", base=repo)
            self.assertEqual(len(exps), 3)
            for exp in exps:
                self.assertLessEqual(exp["level"], 2)


class TestHortusAudit(unittest.TestCase):
    def test_audit_exists_and_honest(self):
        path = os.path.join(_LAB, "hortus_audit.md")
        self.assertTrue(os.path.exists(path), "hortus_audit.md missing")
        text = open(path, encoding="utf-8").read()
        for token in ("engine.py", "model.py", "verifier.py",
                      "records.py", "run_evolution", "verify_champion",
                      "EVIDENCE_LEVEL_CAP", "UNIMPLEMENTED",
                      "analytic", "ladder"):
            self.assertIn(token.lower(), text.lower(),
                          "audit missing %r" % (token,))

    def test_hortus_status_callable(self):
        st = breeding.hortus_status()
        self.assertIn("available", st)
        self.assertIn("note", st)
        if not st["available"]:
            self.assertEqual(st["marker"], breeding.UNIMPLEMENTED)


class TestBreedingExample(unittest.TestCase):
    def test_example_honest(self):
        path = os.path.join(_LAB, "records", "examples",
                            "breeding_example.json")
        self.assertTrue(os.path.exists(path),
                        "breeding_example.json missing")
        doc = json.load(open(path, encoding="utf-8"))
        self.assertEqual(len(doc["variants"]), 3)
        self.assertTrue(doc["selection"]["survivor_id"])
        ok, msg = breeding.verify_lineage(
            doc["lineage"], doc["parent_plan"], doc["variants"])
        self.assertTrue(ok, msg)
        entries = ledger.read_all(
            os.path.join(_LAB, "records", "ledger.jsonl"))
        hashes = {e.get("entry_hash") for e in entries}
        for key in ("selection_entry_hash", "lineage_entry_hash"):
            self.assertIn(doc[key], hashes)
        for item in doc["variant_results"]:
            self.assertIn(item["experiment_id"],
                          {e.get("id") for e in entries})


if __name__ == "__main__":
    unittest.main()
