"""The MOS queue gate: a job with a contract is done only when the contract is.

Run from the repo root:

    python3 -m unittest discover -s tests/queue-python -p "test_worker_contract.py" -v

Everything here is offline. No Redis, no relay, no model call: the worker
methods that would touch the bus are replaced with stubs, and the contract
fixture is the same JSON the Node and Python suites already share.
"""
import copy
import json
import os
import shutil
import sys
import tempfile
import types
import unittest
from types import SimpleNamespace
from unittest import mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "os"))


def _offline_relay():
    """The transport names jobs.py/capabilities.py import at module load.

    relay_common lives with the live muse-relay install, not this checkout.
    The gate under test never calls the bus; this stub keeps the import
    surface honest without inventing a fake job store.
    """
    module = types.ModuleType("relay_common")
    module.NICK = "tester"
    module.INSTANCE_ID = "test-host"
    module.CAPNS = "test:cap"
    module.api_get = lambda *a, **k: (_ for _ in ()).throw(
        RuntimeError("offline: no relay"))
    module.api_post = module.api_get
    module.bus_key = lambda room: f"bus:{room}"
    module.dm_room = lambda secret: f"dm:{secret}"
    module.bus_get = lambda *a, **k: []
    module.bus_push = lambda *a, **k: None
    module.bus_trim = lambda *a, **k: None
    module.presence_beat = lambda *a, **k: None
    module.clean_room = lambda room: room or ""
    module.nick_holder = lambda nick: None
    return module


sys.modules.setdefault("relay_common", _offline_relay())

import jobs  # noqa: E402
from mos import contract_job, worker  # noqa: E402

FIXTURE = os.path.join(REPO, "tests", "fixtures", "contract-done.json")


def write_contract(run_dir, document):
    os.makedirs(run_dir, exist_ok=True)
    with open(os.path.join(run_dir, "contract.json"), "w", encoding="utf-8") as handle:
        json.dump(document, handle)


def fixture():
    with open(FIXTURE, encoding="utf-8") as handle:
        return json.load(handle)


def unfinished():
    document = copy.deepcopy(fixture())
    document["status"] = "open"
    document.pop("finished_at", None)
    document["done_checks"] = []
    return document


class ContractGateTests(unittest.TestCase):
    def test_a_job_without_a_contract_has_no_gate(self):
        self.assertIsNone(worker.contract_gate({}))
        self.assertIsNone(worker.contract_gate({"contract": "  "}))

    def test_a_finished_contract_passes(self):
        with tempfile.TemporaryDirectory() as run_dir:
            write_contract(run_dir, fixture())
            verdict = worker.contract_gate({"contract": run_dir})
            self.assertTrue(verdict.ok, verdict.as_dict())
            self.assertEqual(verdict.code, "done")

    def test_a_missing_contract_is_not_done(self):
        with tempfile.TemporaryDirectory() as run_dir:
            verdict = worker.contract_gate({"contract": run_dir})
            self.assertFalse(verdict.ok)
            self.assertEqual(verdict.code, "contract-missing")

    def test_an_unfinished_contract_is_not_done(self):
        with tempfile.TemporaryDirectory() as run_dir:
            write_contract(run_dir, unfinished())
            verdict = worker.contract_gate({"contract": run_dir})
            self.assertFalse(verdict.ok)
            self.assertEqual(verdict.code, "contract-not-finished")
            self.assertIn("done-not-run", verdict.reason)


class WorkerRunOnceTests(unittest.TestCase):
    def setUp(self):
        self.w = worker.Worker(nick="tester", caps={"python"})
        self.w.register = lambda: None
        self.w.heartbeat = lambda: None
        self.w.poll_dms = lambda: [("7", "task", set())]
        self.w._claim = lambda jid: (True, "")
        self.w._finish = mock.Mock(return_value=True)
        self.w._block = mock.Mock(return_value=True)

    def run_with(self, fields):
        with mock.patch.object(worker.jobs, "job_get",
                               return_value=(fields, "spec")):
            return self.w.run_once(
                lambda jid, title, spec, workdir: ("abc123", "work done"))

    def test_done_contract_finishes_the_job(self):
        with tempfile.TemporaryDirectory() as run_dir:
            write_contract(run_dir, fixture())
            report = self.run_with({"contract": run_dir})
        self.assertEqual(report["done"], ["7"])
        self.assertEqual(report["blocked"], [])
        self.assertTrue(self.w._finish.called)
        self.assertFalse(self.w._block.called)
        self.assertIn("[contract ", self.w._finish.call_args[0][2])

    def test_unfinished_contract_blocks_instead_of_done(self):
        with tempfile.TemporaryDirectory() as run_dir:
            write_contract(run_dir, unfinished())
            report = self.run_with({"contract": run_dir})
        self.assertEqual(report["blocked"], ["7"])
        self.assertEqual(report["done"], [])
        self.assertFalse(self.w._finish.called)
        reason = self.w._block.call_args[0][1]
        self.assertIn("contract-not-finished", reason)
        self.assertIn("done-not-run", reason)

    def test_no_contract_keeps_the_old_path(self):
        report = self.run_with({})
        self.assertEqual(report["done"], ["7"])
        self.assertTrue(self.w._finish.called)
        self.assertFalse(self.w._block.called)


class QueueDoneGateTests(unittest.TestCase):
    def test_done_refuses_an_unfinished_contract_before_writing_state(self):
        with tempfile.TemporaryDirectory() as run_dir:
            write_contract(run_dir, unfinished())
            fields = {"status": "claimed", "claim": jobs.NICK,
                      "contract": run_dir}
            args = SimpleNamespace(id="7", commit="abc123", note="",
                                   room="")
            with mock.patch.object(jobs, "job_get",
                                   return_value=(fields, "spec")), \
                    mock.patch.object(jobs, "_hset") as hset, \
                    mock.patch.object(jobs, "_announce") as announce:
                code = jobs.cmd_done(args)
            self.assertEqual(code, 2)
            hset.assert_not_called()
            announce.assert_not_called()


if __name__ == "__main__":
    unittest.main()
