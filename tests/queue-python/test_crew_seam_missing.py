"""Missing-case tests for the Python crew seam (B230).

Cases test_crew.py does not cover: the dispatch boundary's empty and
env-override paths, the review-timestamp bump, QueueAssessor's polling
and timeout, build_brief's cross-division filter, and the evidence
cap's refusal.

Offline only: every external seam is a local fake; no network call is
made.
"""
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")

_TMP = tempfile.mkdtemp(prefix="trio-crew-missing-")
os.environ["TRIO_STORE"] = "local"
os.environ["TRIO_LOCAL_DB"] = os.path.join(_TMP, "crew.db")
os.environ.pop("TRIO_CREW_DISPATCH_URL", None)

sys.path.insert(0, QUEUE_DIR)

import crew  # noqa: E402


class DispatchBoundaryTests(unittest.TestCase):
    def test_empty_url_is_refused(self):
        with self.assertRaises(crew.DispatchBoundaryError):
            crew.check_dispatch_url("not a url")

    def test_loopback_names_are_accepted(self):
        self.assertEqual(
            crew.check_dispatch_url("http://localhost:8935/d"),
            "http://localhost:8935/d")
        self.assertEqual(
            crew.check_dispatch_url("http://[::1]:8935/d"),
            "http://[::1]:8935/d")

    def test_env_override_is_still_checked(self):
        with unittest.mock.patch.dict(
                os.environ,
                {crew.DISPATCH_URL_ENV: "https://example.com/dispatch"}):
            with self.assertRaises(crew.DispatchBoundaryError):
                crew.dispatch_url()


class DistinctTimestampTests(unittest.TestCase):
    def test_different_timestamp_is_unchanged(self):
        self.assertEqual(
            crew._distinct_timestamp(
                "2026-11-02T00:00:01.000Z",
                "2026-11-02T00:00:00.000Z"),
            "2026-11-02T00:00:01.000Z")

    def test_equal_timestamp_bumps_one_millisecond(self):
        self.assertEqual(
            crew._distinct_timestamp(
                "2026-11-02T00:00:00.000Z",
                "2026-11-02T00:00:00.000Z"),
            "2026-11-02T00:00:00.001Z")


class FakeJobs:
    def __init__(self, results):
        self.results = list(results)
        self.submitted = []
        self.gets = 0

    def submit(self, envelope):
        self.submitted.append(envelope)
        return envelope["id"], True

    def get_result(self, job_id):
        self.gets += 1
        return self.results.pop(0) if self.results else None


class QueueAssessorTests(unittest.TestCase):
    def test_polls_until_a_result_arrives(self):
        result = {"status": "ok", "job_id": "j", "assessment": {}}
        jobs = FakeJobs([None, result])
        assessor = crew.QueueAssessor(
            jobs, poll_attempts=3, poll_interval=0,
            sleep=lambda _s: None)
        got = assessor("vigiles", b"frame", "2026-11-02T00:00:00.000Z")
        self.assertIs(got, result)
        self.assertEqual(jobs.gets, 2)
        self.assertEqual(len(jobs.submitted), 1)

    def test_timeout_is_an_error_not_a_fabricated_result(self):
        jobs = FakeJobs([])
        assessor = crew.QueueAssessor(
            jobs, poll_attempts=2, poll_interval=0,
            sleep=lambda _s: None)
        with self.assertRaises(TimeoutError):
            assessor("vigiles", b"frame", "2026-11-02T00:00:00.000Z")
        self.assertEqual(jobs.gets, 2)
        self.assertEqual(len(jobs.submitted), 1)


class BuildBriefTests(unittest.TestCase):
    RECORD = {"division": "vigiles", "category": "person down"}

    @staticmethod
    def result(product, summary, uncertainty, latency, model,
               observations):
        return {
            "status": "ok", "model": model, "latency_ms": latency,
            "assessment": {
                "product": product,
                "observations": observations,
                "assessment": {"summary": summary,
                               "uncertainty": uncertainty},
            },
        }

    def test_cross_division_observations_are_excluded(self):
        brief = crew.build_brief(self.RECORD, [
            self.result("vigiles", "s1", ["u1"], 10, "m1",
                        [{"description": "origin"}]),
            self.result("ignis", None, ["u1", "u2"], 5, "m2",
                        [{"description": "other lens"}]),
        ])
        self.assertEqual(brief["observations"],
                         [{"description": "origin"}])
        self.assertEqual(brief["assessment"]["uncertainty"],
                         ["u1", "u2"])
        self.assertEqual(brief["assessment"]["summary"], "s1")
        self.assertTrue(brief["assessment"]["requires_human_review"])
        self.assertEqual(brief["processing"]["latency_ms"], 15)
        self.assertEqual(brief["processing"]["model"], "m2")

    def test_missing_summary_has_the_honest_fallback(self):
        brief = crew.build_brief(self.RECORD, [
            self.result("vigiles", None, [], None, "m1", []),
        ])
        self.assertEqual(
            brief["assessment"]["summary"],
            "Recorded assessments are on the incident timeline.")
        self.assertIsNone(brief["processing"]["latency_ms"])


class EvidenceCapTests(unittest.TestCase):
    def test_capture_refuses_at_the_cap_before_touching_the_store(self):
        obj = crew.Crew(records=object(), assess=None,
                        fetch_snapshot=None, dispatch=None)
        entries, detector, error = obj._capture_evidence(
            "incident-x", "flag-frame", b"frame", "cam",
            crew.MAX_EVIDENCE_FILES)
        self.assertEqual(entries, [])
        self.assertIsNone(detector)
        self.assertEqual(error, "evidence file cap reached")


if __name__ == "__main__":
    unittest.main()
