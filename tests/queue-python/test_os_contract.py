"""The contract crosses the Node/Python boundary, and a job is done only when it finishes.

Run from the repo root:

    python3 -m unittest discover -s tests/queue-python -p "test_os_contract.py" -v

The verifier is userspace and offline; the job tests spawn a real Python child that writes a
real contract.json. No kernel, no Redis, no model call.
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os"))

from mos import contract, contract_job  # noqa: E402

FIXTURE = os.path.join(REPO, "tests", "fixtures", "contract-done.json")


def fixture():
    with open(FIXTURE, "r", encoding="utf-8") as handle:
        return json.load(handle)


class ContractValidationTests(unittest.TestCase):
    def test_shared_fixture_is_valid_and_finished(self):
        document = fixture()
        self.assertEqual(contract.validate_contract(document), [])
        self.assertEqual(contract.can_finish(document)["code"], "already-done")
        self.assertTrue(contract.is_done(FIXTURE))

    def test_loaded_fixture_passes_the_finish_gate(self):
        document = contract.load_contract(FIXTURE)
        verdict = contract.can_finish(dict(document, status="open"))
        self.assertEqual(verdict, {"ok": True, "code": "done", "reason": None})

    def test_uncited_decision_is_rejected(self):
        document = copy.deepcopy(fixture())
        document["steps"][0]["chose"]["because"] = "obs-9"
        errors = contract.validate_contract(document)
        self.assertTrue(any("because" in error["path"] for error in errors), errors)
        with self.assertRaises(contract.ContractError) as caught:
            contract.assert_contract(document)
        self.assertEqual(caught.exception.code, "invalid-contract")

    def test_a_done_check_that_never_ran_is_not_done(self):
        document = copy.deepcopy(fixture())
        document["status"] = "open"
        document.pop("finished_at")
        document["done_checks"] = []
        verdict = contract.can_finish(document)
        self.assertEqual(verdict["code"], "done-not-run")

    def test_a_stale_done_check_cannot_finish(self):
        document = copy.deepcopy(fixture())
        document["status"] = "open"
        document["done_checks"][0]["seq"] = 1
        verdict = contract.can_finish(document)
        self.assertEqual(verdict["code"], "done-stale")

    def test_a_failed_done_check_cannot_finish(self):
        document = copy.deepcopy(fixture())
        document["status"] = "open"
        document["done_checks"][0]["exit"] = 1
        verdict = contract.can_finish(document)
        self.assertEqual(verdict["code"], "done-failed")

    def test_boolean_exit_is_not_an_exit_code(self):
        document = copy.deepcopy(fixture())
        document["steps"][0]["result"]["exit"] = True
        errors = contract.validate_contract(document)
        self.assertTrue(any("result.exit" in error["path"] for error in errors), errors)

    def test_missing_contract_file_is_named(self):
        with self.assertRaises(contract.ContractError) as caught:
            contract.load_contract(os.path.join(REPO, "no-such-contract.json"))
        self.assertEqual(caught.exception.code, "contract-unreadable")


class ContractJobTests(unittest.TestCase):
    def run_script(self, script, run_dir, timeout=20):
        with tempfile.TemporaryDirectory() as workdir:
            return contract_job.run_contract_job(
                [sys.executable, "-c", script],
                workdir=workdir,
                run_dir=run_dir,
                timeout=timeout,
            )

    def test_a_done_contract_is_accepted(self):
        with tempfile.TemporaryDirectory() as run_dir:
            script = (
                "import os, shutil\n"
                "shutil.copyfile(%r, os.environ['CONTRACT_PATH'])\n" % FIXTURE
            )
            verdict = self.run_script(script, run_dir)
            self.assertTrue(verdict.ok, verdict.as_dict())
            self.assertEqual(verdict.code, "done")
            self.assertEqual(verdict.exit_code, 0)
            self.assertEqual(len(verdict.digest), 16)
            self.assertTrue(os.path.exists(os.path.join(run_dir, "output.log")))

    def test_a_missing_contract_is_not_done(self):
        with tempfile.TemporaryDirectory() as run_dir:
            verdict = self.run_script("pass\n", run_dir)
            self.assertFalse(verdict.ok)
            self.assertEqual(verdict.code, "contract-missing")

    def test_an_invalid_contract_is_not_done(self):
        with tempfile.TemporaryDirectory() as run_dir:
            script = (
                "import os\n"
                "open(os.environ['CONTRACT_PATH'], 'w').write('{}')\n"
            )
            verdict = self.run_script(script, run_dir)
            self.assertFalse(verdict.ok)
            self.assertEqual(verdict.code, "contract-invalid")

    def test_an_unfinished_contract_is_not_done(self):
        with tempfile.TemporaryDirectory() as run_dir:
            script = (
                "import json, os, shutil\n"
                "shutil.copyfile(%r, os.environ['CONTRACT_PATH'])\n"
                "p = os.environ['CONTRACT_PATH']\n"
                "c = json.load(open(p))\n"
                "c['status'] = 'open'\n"
                "c.pop('finished_at', None)\n"
                "c['done_checks'] = []\n"
                "json.dump(c, open(p, 'w'))\n" % FIXTURE
            )
            verdict = self.run_script(script, run_dir)
            self.assertFalse(verdict.ok)
            self.assertEqual(verdict.code, "contract-not-finished")
            self.assertIn("done-not-run", verdict.reason)

    def test_a_nonzero_exit_is_not_done_even_with_a_done_contract(self):
        with tempfile.TemporaryDirectory() as run_dir:
            script = (
                "import os, shutil, sys\n"
                "shutil.copyfile(%r, os.environ['CONTRACT_PATH'])\n"
                "sys.exit(3)\n" % FIXTURE
            )
            verdict = self.run_script(script, run_dir)
            self.assertFalse(verdict.ok)
            self.assertEqual(verdict.code, "nonzero-exit")
            self.assertEqual(verdict.exit_code, 3)

    def test_a_timeout_is_not_done_and_does_not_hang(self):
        with tempfile.TemporaryDirectory() as run_dir:
            started = time.time()
            verdict = self.run_script("import time; time.sleep(5)\n", run_dir, timeout=0.3)
            elapsed = time.time() - started
            self.assertFalse(verdict.ok)
            self.assertEqual(verdict.code, "timeout")
            self.assertEqual(verdict.exit_code, 124)
            self.assertLess(elapsed, 3.0, "the child was not stopped promptly")

    def test_verify_contract_reads_an_existing_run(self):
        with tempfile.TemporaryDirectory() as run_dir:
            with open(os.path.join(run_dir, "contract.json"), "w", encoding="utf-8") as handle:
                json.dump(fixture(), handle)
            verdict = contract_job.verify_contract(run_dir)
            self.assertTrue(verdict.ok)
            self.assertEqual(verdict.code, "done")

    def test_contract_digest_is_stable_and_not_order_dependent(self):
        first = fixture()
        second = dict(reversed(list(first.items())))
        self.assertEqual(contract.contract_digest(first), contract.contract_digest(second))


if __name__ == "__main__":
    unittest.main()
