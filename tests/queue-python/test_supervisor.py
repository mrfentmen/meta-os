"""Tests for the autonomous supervisor (server/queue/supervisor.py).

Run from the repo root (same command as the queue suite):

    python3 -m unittest discover -s tests/queue-python -v

Everything here is offline and deterministic: records are fixtures
in a temp dir, the guardrail status is a stub, and the supervisor's
clock is fixed. The supervisor must never spend, never file an
assessment, and never dispatch — the last test class pins that
invariant both in the source and in observed behaviour.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest
import unittest.mock
from datetime import datetime, timezone

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")

_TMP = tempfile.mkdtemp(prefix="trio-supervisor-tests-")
os.environ["TRIO_STORE"] = "local"
os.environ["TRIO_LOCAL_DB"] = os.path.join(_TMP, "supervisor-local.db")
os.environ["TRIO_JOB_NS"] = "trio-test"
os.environ.pop("SPARK_API_KEY", None)
os.environ.pop("TRIO_SPARK_VIA_HELPER", None)

sys.path.insert(0, QUEUE_DIR)

import crew_records  # noqa: E402
import patrol as patrol_mod  # noqa: E402
import supervisor as supervisor_mod  # noqa: E402

NOW = datetime(2026, 10, 30, 12, 0, 0,
               tzinfo=timezone.utc).timestamp()
CAM_A = {"id": "cam-a", "name": "1 Ave @ 84 St", "latitude": 40.7755,
         "longitude": -73.9502, "area": "Manhattan", "isOnline": "true",
         "imageUrl": "https://example.invalid/cam-a/image"}
CAM_B = {"id": "cam-b", "name": "Central Park West @ 65 St",
         "latitude": 40.771797, "longitude": -73.979217,
         "area": "Manhattan", "isOnline": "true",
         "imageUrl": "https://example.invalid/cam-b/image"}
CAM_C = {"id": "cam-c", "name": "Broadway @ 45 St",
         "latitude": 40.757953, "longitude": -73.98549,
         "area": "Manhattan", "isOnline": "true",
         "imageUrl": "https://example.invalid/cam-c/image"}
CAMS = [CAM_A, CAM_B, CAM_C]


def iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def guardrail(spent=0.0, cap=75.0):
    return lambda: {"calls": 0, "est_cost_usd": spent,
                    "test_budget_usd": cap,
                    "remaining_usd": round(cap - spent, 4)}


class SupervisorFixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=_TMP)
        self.records = crew_records.CrewRecords(
            directory=os.path.join(self.tmp, "crew-data"))

    def make_supervisor(self, spent=0.0, **kwargs):
        return supervisor_mod.Supervisor(
            records=self.records,
            guardrail_status=guardrail(spent),
            now_epoch=lambda: NOW, **kwargs)

    def fresh_patrol(self, age_s=60):
        self.records.write_status(
            {"service": "imperium-patrol", "state": "running",
             "at": iso(NOW - age_s)})

    def supervisor_events(self):
        return [e for e in self.records.recent_events(500)
                if e.get("type") == "supervisor"]

    def detectors(self, result):
        return {f["detector"] for f in result["findings"]}


class PatrolStaleTests(SupervisorFixture):
    def test_stale_patrol_fires_requeue_and_resume_event(self):
        self.fresh_patrol(age_s=3600)  # 1h old, threshold 15 min
        result = self.make_supervisor().run()
        self.assertIn("patrol_stale", self.detectors(result))
        finding = [f for f in result["findings"]
                   if f["detector"] == "patrol_stale"][0]
        self.assertEqual(finding["action"], "requeue_stalled_patrol")
        events = self.records.recent_events(500)
        resumes = [e for e in events
                   if e.get("type") == "patrol-resume"]
        self.assertEqual(len(resumes), 1)
        self.assertEqual(resumes[0]["agent"], "supervisor")
        sup = self.supervisor_events()
        self.assertEqual(len(sup), 1)
        self.assertEqual(sup[0]["agent"], "supervisor")
        self.assertEqual(sup[0]["action"], "requeue_stalled_patrol")

    def test_no_records_at_all_is_stale(self):
        result = self.make_supervisor().run()
        self.assertIn("patrol_stale", self.detectors(result))

    def test_fresh_patrol_does_not_fire(self):
        self.fresh_patrol(age_s=60)
        result = self.make_supervisor().run()
        self.assertNotIn("patrol_stale", self.detectors(result))
        self.assertEqual(result["findings"], [])

    def test_recent_patrol_check_event_counts_as_activity(self):
        self.records.write_status(
            {"state": "running", "at": iso(NOW - 7200)})
        self.records.append_event(
            {"at": iso(NOW - 30), "type": "patrol-check",
             "camera_id": "cam-a", "outcome": "baseline"})
        result = self.make_supervisor().run()
        self.assertNotIn("patrol_stale", self.detectors(result))

    def test_paused_budget_heartbeat_is_not_stale(self):
        self.records.write_status(
            {"state": "paused-budget", "at": iso(NOW - 7200)})
        result = self.make_supervisor().run()
        self.assertNotIn("patrol_stale", self.detectors(result))

    def test_stale_finding_is_not_respammed_next_pass(self):
        self.fresh_patrol(age_s=3600)
        sup = self.make_supervisor()
        first = sup.run()
        second = sup.run()
        self.assertIn("patrol_stale", self.detectors(first))
        self.assertNotIn("patrol_stale", self.detectors(second))
        self.assertEqual(len(self.supervisor_events()), 1)


class IncidentStuckTests(SupervisorFixture):
    def _incident(self, status, age_s, steps=()):
        incident_id = f"incident-{status}-{age_s}"
        self.records.create_incident({
            "id": incident_id, "status": status,
            "created_at": iso(NOW - age_s), "timeline": []})
        for step in steps:
            self.records.append_timeline(incident_id, step)
        return incident_id

    def test_stuck_reported_incident_is_flagged_on_timeline(self):
        self.fresh_patrol()
        incident_id = self._incident("reported", 7200, steps=[
            {"at": iso(NOW - 7200), "step": "flag"}])
        result = self.make_supervisor().run()
        self.assertIn("incident_stuck", self.detectors(result))
        record = self.records.get_incident(incident_id)
        self.assertEqual(record["status"], "reported")  # not moved
        sup_steps = [s for s in record["timeline"]
                     if s.get("step") == "supervisor"]
        self.assertEqual(len(sup_steps), 1)
        self.assertEqual(sup_steps[0]["detector"], "incident_stuck")

    def test_stuck_investigating_incident_is_stopped(self):
        self.fresh_patrol()
        incident_id = self._incident("investigating", 7200, steps=[
            {"at": iso(NOW - 7200), "step": "investigation"}])
        result = self.make_supervisor().run()
        finding = [f for f in result["findings"]
                   if f["detector"] == "incident_stuck"][0]
        self.assertEqual(finding["action"], "stop_investigation")
        self.assertEqual(
            self.records.get_incident(incident_id)["status"],
            "investigation-stopped")

    def test_recently_active_incident_does_not_fire(self):
        self.fresh_patrol()
        self._incident("reported", 60)
        result = self.make_supervisor().run()
        self.assertNotIn("incident_stuck", self.detectors(result))

    def test_terminal_incident_never_fires(self):
        self.fresh_patrol()
        self._incident("dispatched-simulated", 86400)
        self._incident("cleared-by-review", 86400)
        # The orchestrator lifecycle's terminal values (Lane B).
        self._incident("closed-false-positive", 86400)
        self._incident("stopped", 86400)
        result = self.make_supervisor().run()
        self.assertNotIn("incident_stuck", self.detectors(result))


class DisagreementTests(SupervisorFixture):
    def _reviews(self, division, verdict, count):
        for _ in range(count):
            self.records.append_event(
                {"at": iso(NOW - 120), "type": "review",
                 "division": division, "verdict": verdict,
                 "incident_id": "incident-x", "camera_id": "cam-a"})

    def test_three_clears_for_one_division_fire(self):
        self.fresh_patrol()
        self._reviews("ignis", "cleared", 3)
        self._reviews("vigiles", "cleared", 2)  # below threshold
        result = self.make_supervisor().run()
        findings = [f for f in result["findings"]
                    if f["detector"] == "repeated_disagreement"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["scope"], "division:ignis")

    def test_confirmed_verdicts_do_not_count(self):
        self.fresh_patrol()
        self._reviews("ignis", "confirmed", 4)
        self._reviews("ignis", "cleared", 2)
        result = self.make_supervisor().run()
        self.assertNotIn("repeated_disagreement",
                         self.detectors(result))


class JobFailureTests(SupervisorFixture):
    def _failures(self, outcome, camera_id, count):
        for _ in range(count):
            self.records.append_event(
                {"at": iso(NOW - 120), "type": "patrol-check",
                 "camera_id": camera_id, "outcome": outcome,
                 "error": "stubbed failure"})

    def test_repeated_feed_errors_pause_the_feed(self):
        self.fresh_patrol()
        self._failures("feed-error", "cam-x", 3)
        self._failures("feed-error", "cam-y", 2)  # below threshold
        result = self.make_supervisor().run()
        findings = [f for f in result["findings"]
                    if f["detector"] == "repeated_job_failure"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["action"], "pause_feed")
        paused = supervisor_mod.load_paused_feeds(self.records.dir)
        self.assertEqual(paused, ["cam-x"])

    def test_repeated_job_errors_warn_without_pausing(self):
        self.fresh_patrol()
        self._failures("job-error", "cam-x", 3)
        result = self.make_supervisor().run()
        findings = [f for f in result["findings"]
                    if f["detector"] == "repeated_job_failure"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["action"], "job_failure_warning")
        self.assertEqual(
            supervisor_mod.load_paused_feeds(self.records.dir), [])


class PauseFeedPatrolIntegrationTests(SupervisorFixture):
    def test_paused_camera_is_excluded_from_patrol_cycle(self):
        self.fresh_patrol()
        for _ in range(3):
            self.records.append_event(
                {"at": iso(NOW - 120), "type": "patrol-check",
                 "camera_id": "cam-a", "outcome": "feed-error",
                 "error": "stubbed failure"})
        result = self.make_supervisor().run()
        self.assertIn("pause_feed",
                      [f["action"] for f in result["findings"]])

        seen = []

        class FakeCrew:
            def check_camera(self, camera, division):
                seen.append(camera["id"])
                return {"outcome": "baseline",
                        "camera_id": camera["id"],
                        "division": division}

        with unittest.mock.patch.object(
                patrol_mod.spark_guardrail, "check", lambda: None):
            patrol_obj = patrol_mod.Patrol(
                FakeCrew(), CAMS, "fallback-subset", self.records,
                interval_s=0,
                guardrail_status=lambda: {
                    "calls": 0, "est_cost_usd": 0.0,
                    "test_budget_usd": 75.0, "remaining_usd": 70.0},
                sleep=lambda s: None)
            for _ in range(4):
                patrol_obj.run_cycle()
        self.assertNotIn("cam-a", seen)
        self.assertEqual(set(seen), {"cam-b", "cam-c"})


class BudgetTests(SupervisorFixture):
    def test_spend_at_eighty_percent_warns(self):
        self.fresh_patrol()
        result = self.make_supervisor(spent=60.0).run()  # 80% of 75
        findings = [f for f in result["findings"]
                    if f["detector"] == "spend_approaching_limit"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["action"], "budget_warning")

    def test_spend_below_threshold_does_not_warn(self):
        self.fresh_patrol()
        result = self.make_supervisor(spent=50.0).run()
        self.assertNotIn("spend_approaching_limit",
                         self.detectors(result))


class OrchestratorLoopTests(SupervisorFixture):
    def _incident_with_investigations(self, incident_id, steps):
        self.records.create_incident({
            "id": incident_id, "status": "reported",
            "created_at": iso(NOW - 300), "timeline": []})
        for step in steps:
            self.records.append_timeline(incident_id, step)
        return incident_id

    def test_same_camera_and_lens_twice_is_a_loop(self):
        self.fresh_patrol()
        step = {"at": iso(NOW - 200), "step": "investigation",
                "camera_id": "cam-a", "division": "ignis"}
        incident_id = self._incident_with_investigations(
            "incident-loop", [dict(step), dict(step)])
        result = self.make_supervisor().run()
        findings = [f for f in result["findings"]
                    if f["detector"] == "orchestrator_loop"]
        self.assertEqual(len(findings), 1)
        self.assertEqual(findings[0]["action"], "stop_investigation")
        self.assertEqual(
            self.records.get_incident(incident_id)["status"],
            "investigation-stopped")

    def test_single_investigation_is_not_a_loop(self):
        self.fresh_patrol()
        self._incident_with_investigations("incident-once", [
            {"at": iso(NOW - 200), "step": "investigation",
             "camera_id": "cam-a", "division": "ignis"},
            {"at": iso(NOW - 190), "step": "investigation",
             "camera_id": "cam-a", "division": "medicus"},
            {"at": iso(NOW - 180), "step": "investigation",
             "camera_id": "cam-b", "division": "vigiles"},
        ])
        result = self.make_supervisor().run()
        self.assertNotIn("orchestrator_loop", self.detectors(result))

    def test_orchestrator_decisions_without_hash_are_not_a_loop(self):
        # Orchestrator decision events carry the incident camera +
        # division on EVERY decision; two decisions about one
        # incident are normal operation. Only a repeated evidence
        # hash may count as a loop for these events.
        self.fresh_patrol()
        self._incident_with_investigations("incident-decisions", [])
        for decision in ("review", "investigate"):
            self.records.append_event(
                {"at": iso(NOW - 100), "type": "orchestrator",
                 "agent": "orchestrator",
                 "incident_id": "incident-decisions",
                 "camera_id": "cam-a", "division": "vigiles",
                 "decision": decision})
        result = self.make_supervisor().run()
        self.assertNotIn("orchestrator_loop", self.detectors(result))

    def test_same_evidence_hash_in_orchestrator_events_is_a_loop(self):
        self.fresh_patrol()
        self._incident_with_investigations("incident-hash", [])
        for _ in range(2):
            self.records.append_event(
                {"at": iso(NOW - 100), "type": "orchestrator",
                 "incident_id": "incident-hash",
                 "evidence_hash": "abc123", "action": "investigate"})
        result = self.make_supervisor().run()
        self.assertIn("orchestrator_loop", self.detectors(result))


class NoSpendInvariantTests(SupervisorFixture):
    def test_supervisor_source_has_no_generation_or_dispatch_path(self):
        with open(os.path.join(QUEUE_DIR, "supervisor.py")) as f:
            source = f.read()
        for token in ("spark_gen", "QueueAssessor",
                      "build_job_envelope", "http_dispatch",
                      "trio_agent", "urllib"):
            self.assertNotIn(token, source)

    def test_run_creates_no_incidents_and_no_dispatch_log(self):
        self.fresh_patrol(age_s=3600)
        for _ in range(3):
            self.records.append_event(
                {"at": iso(NOW - 120), "type": "review",
                 "division": "ignis", "verdict": "cleared"})
        spent_before = 12.0
        result = self.make_supervisor(spent=spent_before).run()
        self.assertTrue(result["findings"])  # it did evaluate
        self.assertEqual(self.records.list_incidents(), [])
        self.assertFalse(os.path.exists(
            os.path.join(self.records.dir, "dispatches.jsonl")))
        # The guardrail stub was only ever READ: nothing recorded
        # a call, so spend is exactly where the fixture left it.
        self.assertEqual(guardrail(spent_before)()["est_cost_usd"],
                         spent_before)


class CliTests(unittest.TestCase):
    def test_once_cli_prints_one_line_summary(self):
        data_dir = os.path.join(_TMP, "cli-crew-data")
        records = crew_records.CrewRecords(directory=data_dir)
        records.write_status(
            {"state": "running", "at": iso(NOW - 7200)})
        env = dict(os.environ)
        env["TRIO_CREW_DATA_DIR"] = data_dir
        p = subprocess.run(
            [sys.executable,
             os.path.join(QUEUE_DIR, "supervisor.py"), "--once"],
            capture_output=True, text=True, timeout=60, env=env,
            cwd=REPO)
        self.assertEqual(p.returncode, 0, p.stderr)
        lines = [l for l in p.stdout.strip().splitlines() if l.strip()]
        self.assertEqual(len(lines), 1)
        self.assertTrue(lines[0].startswith("supervisor:"))
        self.assertIn("patrol_stale", lines[0])


if __name__ == "__main__":
    unittest.main()
