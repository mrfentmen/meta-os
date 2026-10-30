"""tests/test_intel_dispatch_worker.py — DSP-019: a dispatched job is
claimable by the mos worker loop unchanged.

The chain under test is exactly the production path, with no
worker change: intel.dispatch.post_plan posts a validated plan
through jobs.main, the JOB announcement reaches the worker through
the same DM dead-drop overseer.dispatch uses, the unchanged
mos.worker.Worker.run_once claims it, works it, and marks it done,
and mos.overseer.verify_done verifies the acceptance line. The
worker module is not modified by this batch: these tests import it
as shipped.

Everything runs on RelayTestCase (FakeUpstash): no network, no live
bus, nothing posted to the real bus. The DM secret below is a
throwaway test secret, never a real credential.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel.dispatch import post_plan, validated_plan  # noqa: E402
import jobs  # noqa: E402
import send  # noqa: E402
from helpers import RelayTestCase  # noqa: E402
from mos import capabilities, overseer, worker  # noqa: E402


def _plan():
    # Two-job chain: implement writes work.txt, review (dep on
    # implement) writes review.txt. Distinct files, so the DSP-003
    # overlap guard passes; the dep is plan-local, so DSP-004
    # posts implement first.
    return {
        "summary": "Write the work file, then review it.",
        "jobs": [
            {
                "key": "implement",
                "title": "Do implement",
                "spec": "Goal, context, files, steps, out of scope.",
                "files": ["work.txt"],
                "deps": [],
                "max_attempts": 3,
                "accept": ["file-exists: work.txt"],
            },
            {
                "key": "review",
                "title": "Do review",
                "spec": "Goal, context, files, steps, out of scope.",
                "files": ["review.txt"],
                "deps": ["implement"],
                "max_attempts": 3,
                "accept": ["file-exists: review.txt"],
            },
        ],
    }


def _handler(jid, title, spec, workdir):
    # A real worker reads the job to decide the work: the file it
    # writes is the one its own job owns, named by its title.
    if "implement" in title:
        name = "work.txt"
    elif "review" in title:
        name = "review.txt"
    else:
        raise AssertionError(f"unexpected dispatched title: {title!r}")
    with open(os.path.join(workdir, name), "w") as handle:
        handle.write("work product")
    return "deadbee", f"wrote {name}"


class DispatchedWorkerClaimTest(RelayTestCase):
    """DSP-019: post_plan -> DM -> worker.run_once -> verify_done."""

    def setUp(self):
        super().setUp()
        capabilities.CAPNS = "muse-bus:tcap"
        capabilities.register("w1", ["python"], dm_secret="s3cret")
        self.set_nick("poster", "host-p")

    def _post(self):
        plan, order, _clamps = validated_plan(json.dumps(_plan()))
        record = post_plan(plan, order=order)
        mapping = {entry["key"]: entry["id"]
                   for entry in record["jobs"]}
        return record, mapping

    def _dm(self, jid, title):
        self.run_cli(send.main,
                     ["--dm", "s3cret", f"JOB:{jid} {title}"])

    def _as_w1(self):
        self.set_nick("w1", "host-w")
        return worker.Worker(dm_secret="s3cret", caps=["python"],
                             workdir=self.tmp)

    def test_dispatched_chain_flows_through_worker_loop(self):
        record, mapping = self._post()
        self.assertEqual(record["order"], ["implement", "review"])
        # Plan fields survive posting: real dep ids, files, budgets.
        by_id = {}
        _rc, out, _err = self.run_cli(jobs.main, ["list", "--json"])
        for row in json.loads(out):
            by_id[row["id"]] = row
        self.assertEqual(by_id[mapping["review"]]["deps"],
                         mapping["implement"])
        self.assertEqual(by_id[mapping["implement"]]["files"],
                         "work.txt")
        # max_attempts is not a list --json field (FND-013 list);
        # it lives on the job hash, checked here.
        h_impl, _ = jobs.job_get(mapping["implement"])
        self.assertEqual(h_impl["max_attempts"], "3")

        # First job only: DM it, run the unchanged loop once.
        self._dm(mapping["implement"], "Do implement")
        rep = self._as_w1().run_once(_handler)
        self.assertEqual(rep["claimed"], [mapping["implement"]])
        self.assertEqual(rep["done"], [mapping["implement"]])
        self.assertEqual(rep["blocked"], [])
        self.assertEqual(rep["errors"], [])
        h, _ = jobs.job_get(mapping["implement"])
        self.assertEqual(h["status"], "done")
        # jobs.done releases the claim fields on completion; the
        # worker's claim is proven by the run_once report above
        # and by the heartbeat test below, which reads the claim
        # while it is still held.
        self.assertNotIn("claim", h)
        self.assertEqual(h["result_commit"], "deadbee")
        # The dependent job was never DM'd, so the loop never
        # touches it: still open, still waiting on its dep.
        h2, _ = jobs.job_get(mapping["review"])
        self.assertEqual(h2["status"], "open")

        # Acceptance verification runs on the dispatched job.
        self.set_nick("poster", "host-p")
        ok, report = overseer.verify_done(mapping["implement"],
                                          repo=self.tmp)
        self.assertTrue(ok, report)
        h, _ = jobs.job_get(mapping["implement"])
        self.assertEqual(h["verified"], "1")

        # Second job, after its dep is done: same loop, same result.
        self._dm(mapping["review"], "Do review")
        rep = self._as_w1().run_once(_handler)
        self.assertEqual(rep["claimed"], [mapping["review"]])
        self.assertEqual(rep["done"], [mapping["review"]])
        self.set_nick("poster", "host-p")
        ok, report = overseer.verify_done(mapping["review"],
                                          repo=self.tmp)
        self.assertTrue(ok, report)

    def test_worker_heartbeat_renews_dispatched_claim(self):
        _record, mapping = self._post()
        self._dm(mapping["implement"], "Do implement")
        w = self._as_w1()
        # Claim through the worker's own path, then heartbeat:
        # the lease renewal covers the dispatched claim.
        ok, _detail = w._claim(mapping["implement"])
        self.assertTrue(ok)
        self.assertEqual(w.heartbeat(), [mapping["implement"]])
        h, _ = jobs.job_get(mapping["implement"])
        self.assertEqual(h["status"], "claimed")
        self.assertEqual(h["claim"], "w1")

    def test_undelivered_dispatched_job_stays_open(self):
        _record, mapping = self._post()
        # No DM is ever sent: the loop must not invent work.
        rep = self._as_w1().run_once(_handler)
        self.assertEqual(rep["claimed"], [])
        self.assertEqual(rep["done"], [])
        for jid in mapping.values():
            h, _ = jobs.job_get(jid)
            self.assertEqual(h["status"], "open")


if __name__ == "__main__":
    unittest.main()
