"""intel/push.py: the two pushes (Hana lane, OS-097).

Pure-function tests: no network, no Redis, no Spark, no push
sent. Fixtures here are hand-written job and verification
records in the shapes jobs.py, mos/overseer.py, and
mos/acceptance.py produce. The firing from a real overseer
close and a real escalation-gate park is not wired yet (Milo
OS-096 still open), so these tests prove the builder gates
and the exactly-one ledger on planted data, not a live ring.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import push  # noqa: E402


def _done_job(**over):
    job = {"id": "7", "title": "brief panel stub",
           "status": "done", "verified": "1"}
    job.update(over)
    return job


def _verification(**over):
    ver = {"ok": True,
           "checks": [{"check": "file-exists: intel/push.py",
                       "ok": True},
                      {"check": "tests-pass: tests.test_intel_push",
                       "ok": True}],
           "artifacts": ["intel/push.py", "tests/test_intel_push.py"]}
    ver.update(over)
    return ver


class DonePushTest(unittest.TestCase):
    def test_verified_close_yields_all_done_with_summary(self):
        got = push.build_done_push(_done_job(), _verification())
        self.assertIsNotNone(got)
        self.assertEqual(got["type"], "done")
        self.assertEqual(got["job_id"], "7")
        self.assertTrue(got["body"].startswith("All done: "))
        self.assertIn("brief panel stub", got["body"])
        self.assertIn("intel/push.py", got["body"])
        self.assertIn("tests.test_intel_push", got["body"])
        self.assertTrue(push.validate_push(got))

    def test_done_without_verified_stamp_yields_no_push(self):
        job = _done_job(verified="0")
        self.assertIsNone(push.build_done_push(job, _verification()))
        job = _done_job()
        del job["verified"]
        self.assertIsNone(push.build_done_push(job, _verification()))

    def test_done_with_a_failed_check_yields_no_push(self):
        ver = _verification(checks=[
            {"check": "file-exists: intel/push.py", "ok": True},
            {"check": "tests-pass: tests.test_intel_push",
             "ok": False}])
        self.assertIsNone(push.build_done_push(_done_job(), ver))

    def test_job_closed_without_passing_yields_no_push(self):
        # The acceptance case in OS-097: a close that did not
        # pass its checks must never ring as done.
        ver = _verification(ok=False, checks=[])
        self.assertIsNone(push.build_done_push(_done_job(), ver))
        self.assertIsNone(push.build_done_push(_done_job(), None))

    def test_not_done_status_yields_no_push(self):
        for status in ("open", "claimed", "blocked"):
            job = _done_job(status=status)
            self.assertIsNone(
                push.build_done_push(job, _verification()),
                msg=status)

    def test_no_artifacts_says_not_reported_not_a_file(self):
        ver = _verification(artifacts=[])
        got = push.build_done_push(_done_job(), ver)
        self.assertIn("not reported in the artifact record",
                      got["body"])
        self.assertEqual(got["artifacts"], [])

    def test_no_checks_says_no_criteria_recorded(self):
        ver = _verification(checks=[])
        got = push.build_done_push(_done_job(), ver)
        self.assertIn("no acceptance criteria were recorded",
                      got["body"])


class BlockedPushTest(unittest.TestCase):
    def test_blocked_job_with_question_names_it_verbatim(self):
        job = {"id": "9", "title": "dispatch poster",
               "status": "blocked",
               "note": "waiting on the Spark endpoint decision"}
        got = push.build_blocked_push(job)
        self.assertIsNotNone(got)
        self.assertEqual(got["type"], "blocked")
        self.assertIn("dispatch poster", got["body"])
        self.assertIn("waiting on the Spark endpoint decision",
                      got["body"])
        self.assertEqual(got["question"],
                         "waiting on the Spark endpoint decision")

    def test_explicit_question_wins_over_stored_note(self):
        job = {"id": "9", "title": "dispatch poster",
               "status": "blocked", "note": "old note"}
        got = push.build_blocked_push(
            job, "may I spend the remaining budget?")
        self.assertEqual(got["question"],
                         "may I spend the remaining budget?")

    def test_blocked_without_any_question_yields_no_push(self):
        job = {"id": "9", "title": "dispatch poster",
               "status": "blocked"}
        self.assertIsNone(push.build_blocked_push(job))
        self.assertIsNone(push.build_blocked_push(job, "   "))

    def test_non_blocked_status_yields_no_push(self):
        job = {"id": "9", "title": "dispatch poster",
               "status": "open",
               "note": "waiting on the Spark endpoint decision"}
        self.assertIsNone(push.build_blocked_push(job))


class TwoPushesOnlyTest(unittest.TestCase):
    def test_third_type_raises(self):
        with self.assertRaises(ValueError):
            push.build_push("alert", _done_job(),
                            _verification())
        with self.assertRaises(ValueError):
            push.build_push("watchdog", _done_job())

    def test_validate_rejects_unknown_type_and_empty_body(self):
        self.assertFalse(push.validate_push(
            {"type": "alert", "job_id": "7", "body": "x"}))
        self.assertFalse(push.validate_push(
            {"type": "done", "job_id": "7", "body": "   "}))
        self.assertFalse(push.validate_push(
            {"type": "done", "job_id": "", "body": "All done."}))

    def test_decide_picks_by_status(self):
        self.assertEqual(
            push.decide_push(_done_job(), _verification())["type"],
            "done")
        blocked = {"id": "9", "title": "dispatch poster",
                   "status": "blocked",
                   "note": "waiting on the Spark endpoint decision"}
        self.assertEqual(push.decide_push(blocked)["type"],
                         "blocked")
        self.assertIsNone(push.decide_push(
            {"id": "3", "title": "x", "status": "open"}))

    def test_ledger_emits_each_job_and_kind_exactly_once(self):
        ledger = push.PushLedger()
        job = _done_job()
        first = push.decide_push(job, _verification(),
                                 ledger=ledger)
        self.assertIsNotNone(first)
        second = push.decide_push(job, _verification(),
                                  ledger=ledger)
        self.assertIsNone(second)
        # A different job still rings once.
        other = push.decide_push(_done_job(id="8"),
                                 _verification(), ledger=ledger)
        self.assertIsNotNone(other)
        self.assertTrue(ledger.has("7", "done"))
        self.assertTrue(ledger.has("8", "done"))
        self.assertFalse(ledger.has("7", "blocked"))


if __name__ == "__main__":
    unittest.main()
