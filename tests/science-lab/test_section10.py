"""Section 10 (tasks 91-100): demo cycle + truth pass.

stdlib unittest only. Run from repo root:
    python3 -m unittest discover -s tests/science-lab -v

The sweep test re-runs this whole suite in a subprocess; the child
sets SCIENCE_LAB_SWEEP_CHILD=1 so the sweep test skips itself there
(no infinite recursion).
"""
import json
import os
import subprocess
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import export  # noqa: E402
import ledger  # noqa: E402
import repository  # noqa: E402


def _read_json(path):
    with open(str(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


class TestDressRehearsal(unittest.TestCase):
    def test_rehearsal_honest(self):
        doc = _read_json(os.path.join(
            _LAB, "records", "examples", "dress_rehearsal.json"))
        self.assertEqual(doc["question"], export.DRESS_QUESTION)
        self.assertIn(doc["scientific_verdict"],
                      ("match", "no-match", "indeterminate"))
        # Pre-registered threshold vs observed numbers, no adjectives.
        self.assertLessEqual(doc["held_out"]["rmse"], 1.5)
        self.assertEqual(doc["scientific_verdict"], "match")
        self.assertEqual(doc["gate"]["decision"], "confirmed")
        self.assertLessEqual(int(doc["filed_level"]), 2)
        # Timing: wall-clock measured, model spend 0 (no model calls).
        self.assertGreaterEqual(doc["timing"]["wall_clock_s"], 0)
        self.assertEqual(doc["timing"]["model_spend"], 0)
        self.assertIn("no model calls",
                      doc["timing"]["model_spend_note"])
        # Levels 4-6 never claimed.
        self.assertLess(int(doc["filed_level"]), 4)
        # Filed rows are real: ledger entry resolves, repo claim loads.
        entries = ledger.read_all(
            os.path.join(_LAB, "records", "ledger.jsonl"))
        hashes = {e.get("entry_hash") for e in entries}
        self.assertIn(doc["filed"]["experiment_entry"], hashes)
        claim = repository.show_claim("CLAIM-DRESS-REHEARSAL-001")
        self.assertEqual(int(claim["level"]), int(doc["filed_level"]))


class TestFailureDrill(unittest.TestCase):
    def test_refused_never_faked(self):
        doc = _read_json(os.path.join(
            _LAB, "records", "examples", "failure_drill.json"))
        self.assertTrue(doc["refused"])
        self.assertEqual(doc["behaviour"], "refused")
        self.assertFalse(doc["fake_success"])
        self.assertIn("hypotheses", doc["broken_input"])
        self.assertIn("requires inputs", doc["refusal_message"])


class TestClaimAudit(unittest.TestCase):
    def test_own_claims_backed(self):
        result = export.audit_own_claims()
        self.assertGreater(result["checked"], 0)
        accounted = len(result["backed"]) + len(result["cut_or_levelled"])
        self.assertEqual(accounted, result["checked"],
                         "every checked claim must be backed or listed cut")
        self.assertEqual(result["cut_or_levelled"], [],
                         "unbacked claims remain: %r"
                         % (result["cut_or_levelled"],))


class TestStatusAndReadme(unittest.TestCase):
    def test_status_and_readme_exist(self):
        for name in ("SCIENCE_LAB_STATUS.md", "README.md"):
            path = os.path.join(_LAB, name)
            self.assertTrue(os.path.exists(path), path)
            text = open(path, encoding="utf-8").read()
            self.assertTrue(text.strip())
        status = open(os.path.join(_LAB, "SCIENCE_LAB_STATUS.md"),
                      encoding="utf-8").read()
        for word in ("Built", "Unimplemented", "UNIMPLEMENTED"):
            self.assertIn(word, status)


class TestSweepGreen(unittest.TestCase):
    def test_suite_green_from_clean_checkout(self):
        if os.environ.get("SCIENCE_LAB_SWEEP_CHILD"):
            self.skipTest("sweep child: recursion guard")
        env = dict(os.environ)
        env["SCIENCE_LAB_SWEEP_CHILD"] = "1"
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover",
             "-s", "tests/science-lab"],
            cwd=_REPO, capture_output=True, text=True, timeout=600,
            env=env)
        tail = (proc.stderr or "").strip().splitlines()
        line = tail[-1] if tail else ""
        self.assertEqual(proc.returncode, 0,
                         "suite not green:\n%s" % (proc.stderr[-3000:],))
        self.assertIn("OK", line, "unittest final line: %r" % (line,))

    def test_existing_suites_untouched(self):
        proc = subprocess.run(
            [sys.executable, "-m", "unittest", "discover",
             "-s", "os/tests", "-p", "test_hortus_engine.py"],
            cwd=_REPO, capture_output=True, text=True, timeout=600)
        tail = (proc.stderr or "").strip().splitlines()
        self.assertEqual(proc.returncode, 0, proc.stderr[-2000:])
        self.assertTrue(any("Ran 9 tests" in line for line in tail),
                        tail[-3:])
        self.assertIn("OK", tail[-1])
        registry = _read_json(os.path.join(_REPO, "agents",
                                           "registry.json"))
        self.assertIn("agents", registry)


if __name__ == "__main__":
    unittest.main()
