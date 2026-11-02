"""Section 6 Tasks 51-60: independent verification, repository, write gate.

stdlib unittest only. Run from repo root:
    python3 -m unittest discover -s tests/science-lab -v
"""
import hashlib
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
import verify  # noqa: E402
import repository  # noqa: E402


def _synthetic_record(agent="computational-runner", output_hash=None,
                      outcome="match"):
    payload = {"input_hash": "abc123", "random_seed": 7,
               "parameters": {"op": "sum"}}
    good = verify.deterministic_hash(payload)
    return {
        "id": "EXP-T6-001",
        "input_hash": "abc123",
        "random_seed": 7,
        "parameters": {"op": "sum"},
        "output_hash": good if output_hash is None else output_hash,
        "outcome": outcome,
        "evidence_level": 2,
        "agent": agent,
    }


class TestVerifierIsolation(unittest.TestCase):
    def test_reasoning_key_refused(self):
        with self.assertRaises(ValueError):
            verify.verify({"op": "sum"},
                          {"input_hash": "h", "reasoning": "because..."})
        with self.assertRaises(ValueError):
            verify.verify({"op": "sum"},
                          {"input_hash": "h", "narrative": "story"})

    def test_generator_narrative_arg_refused(self):
        with self.assertRaises(ValueError):
            verify.verify({"op": "sum"}, {"input_hash": "h"},
                          generator_narrative="the generator thought...")

    def test_bundle_carries_no_narrative(self):
        bundle = verify.verify({"op": "sum"},
                               {"input_hash": "h", "random_seed": 1})
        blob = json.dumps(bundle)
        self.assertNotIn("reasoning", blob)
        self.assertNotIn("narrative", blob)
        self.assertNotIn("output_hash", blob)


class TestBlindRerunAndCompare(unittest.TestCase):
    def test_rerun_reproduces_without_reading_output(self):
        rec = _synthetic_record()
        rerun = verify.reexecute(rec)
        self.assertEqual(rerun["re_hash"], rec["output_hash"])
        self.assertNotIn("output_hash", json.dumps(rerun["archived_inputs"]))

    def test_agree(self):
        rec = _synthetic_record()
        rerun = verify.reexecute(rec)
        comp = verify.compare(rec["output_hash"], rerun["re_hash"])
        self.assertEqual(comp["verdict"], "agree")
        self.assertIn("match", comp["diff"])

    def test_missing_hash_indeterminate(self):
        comp = verify.compare(None, "deadbeef")
        self.assertEqual(comp["verdict"], "indeterminate")


class TestDisagreementPath(unittest.TestCase):
    def test_disagree_caps_level_and_opens_dispute(self):
        rec = _synthetic_record()
        before = dict(rec)
        comp = verify.compare(rec["output_hash"], "tampered-hash",
                              (rec["outcome"], "match"))
        self.assertEqual(comp["verdict"], "disagree")
        handled = verify.handle_disagreement(rec, comp)
        self.assertEqual(handled["capped_level"],
                         ladder.cap_for_experiment("mismatch"))
        self.assertEqual(handled["capped_level"], 2)
        dispute = handled["dispute"]
        self.assertEqual(dispute["original_id"], rec["id"])
        self.assertIn("reason", dispute)
        self.assertIn("dispute_id", dispute)
        self.assertEqual(rec, before)  # original never edited

    def test_rotation_refuses_same_agent(self):
        rec = _synthetic_record(agent="computational-runner")
        with self.assertRaises(ValueError):
            verify.check_rotation(rec, "computational-runner")
        self.assertEqual(
            verify.check_rotation(rec, "independent-verifier"),
            "independent-verifier")

    def test_unconfirmed_write_carries_cap(self):
        comp = {"verdict": "disagree", "diff": "hashes differ"}
        gate = verify.gate_write({"evidence_level": 3}, comp)
        self.assertEqual(gate["decision"], "unconfirmed")
        self.assertLessEqual(gate["level"], 2)
        gate_ok = verify.gate_write({"evidence_level": 2},
                                    {"verdict": "agree"})
        self.assertEqual(gate_ok["decision"], "confirmed")


class TestRepository(unittest.TestCase):
    def test_file_and_query_by_level(self):
        with tempfile.TemporaryDirectory() as td:
            repository.file_claim({"claim_id": "C1", "statement": "s1",
                                   "level": 2, "department": "chem",
                                   "agent": "archivist"}, base=td)
            repository.file_claim({"claim_id": "C2", "statement": "s2",
                                   "level": 3, "department": "bio",
                                   "agent": "verifier"}, base=td)
            repository.file_experiment({"experiment_id": "E1", "level": 2},
                                       base=td)
            got = repository.query_by_level(2, base=td)
            self.assertEqual([c["claim_id"] for c in got], ["C1"])
            got_bio = repository.query(department="bio", base=td)
            self.assertEqual(len(got_bio), 1)
            got_agent = repository.query(agent="verifier", base=td)
            self.assertEqual(len(got_agent), 1)

    def test_provenance_chain(self):
        with tempfile.TemporaryDirectory() as td:
            repository.file_claim({"claim_id": "C9", "statement": "s",
                                   "level": 2, "experiment_ids": ["E9"],
                                   "source_ids": ["S9"]}, base=td)
            repository.file_experiment({"experiment_id": "E9", "level": 2},
                                       base=td)
            chain = repository.provenance("C9", base=td)
            self.assertEqual(len(chain["experiments"]), 1)
            self.assertEqual(chain["gaps"],
                             ["source 'S9' linked but not filed"])
            with self.assertRaises(LookupError):
                repository.show_claim("NOPE", base=td)


class TestVerificationExample(unittest.TestCase):
    def test_example_honest(self):
        d = json.load(open(os.path.join(
            _LAB, "records", "examples", "verification_example.json")))
        comp = d["comparison"]
        self.assertIn(comp["verdict"], ("agree", "disagree"))
        if comp["verdict"] == "agree":
            self.assertEqual(comp["original_hash"], comp["re_hash"])
            self.assertIsNone(d["dispute"])
            self.assertEqual(d["gate"]["decision"], "confirmed")
        else:
            self.assertIsNotNone(d["dispute"])
            self.assertEqual(d["gate"]["decision"], "unconfirmed")
        # ledger filing is real: entry hash resolves in the ledger
        entries = ledger.read_all(
            os.path.join(_LAB, "records", "ledger.jsonl"))
        hashes = {e.get("entry_hash") for e in entries}
        self.assertIn(d["ledger_entry_hash"], hashes)

    def test_repository_schema_loads(self):
        d = json.load(open(os.path.join(
            _LAB, "schemas", "repository.schema.json")))
        for k in ("claims", "experiments", "cycles", "sources"):
            self.assertIn(k, d["properties"])


if __name__ == "__main__":
    unittest.main()
