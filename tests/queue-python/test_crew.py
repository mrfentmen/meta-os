"""Tests for the Meta Imperium agent crew (patrol -> review ->
investigation -> records -> response). See docs/AGENT_CREW.md.

Run from the repo root (same command as the queue suite):

    python3 -m unittest discover -s tests/queue-python -v

Everything here is offline: the assess/fetch/dispatch seams are
stubbed, NO live Spark call and NO live camera fetch is ever made.
Where the crew must agree with the rest of the stack, the REAL
artefacts are used: the envelope is compared to the real
buildQueueJob (node), the flag tables come from the real
js/command-flag.js, and the incident brief is run through the real
validateAssessment (js/schema.js) via the resident agent's validator.
"""
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock
import urllib.error
import urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")
SCHEMA = os.path.join(REPO, "js", "schema.js")

_TMP = tempfile.mkdtemp(prefix="trio-crew-tests-")
os.environ["TRIO_STORE"] = "local"
os.environ["TRIO_LOCAL_DB"] = os.path.join(_TMP, "crew-local.db")
os.environ["TRIO_JOB_NS"] = "trio-test"
os.environ.pop("SPARK_API_KEY", None)
os.environ.pop("TRIO_SPARK_VIA_HELPER", None)

sys.path.insert(0, QUEUE_DIR)

import crew  # noqa: E402
import crew_common  # noqa: E402
import crew_records  # noqa: E402
import patrol as patrol_mod  # noqa: E402
import queue_service  # noqa: E402
import trio_store  # noqa: E402
from trio_agent import Agent  # noqa: E402

FRAME = b"\xff\xd8" + bytes(range(256)) * 4  # JPEG magic + payload
TIMESTAMP = "2026-10-30T06:00:00.000Z"

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
NEIGHBOURS = [
    {"id": f"cam-n{i}", "name": f"Neighbour {i}",
     "latitude": 40.7755 + 0.001 * (i + 1),
     "longitude": -73.9502 - 0.001 * (i + 1), "area": "Manhattan",
     "isOnline": "true",
     "imageUrl": f"https://example.invalid/cam-n{i}/image"}
    for i in range(5)
]
ALL_CAMS = [CAM_A, CAM_B, CAM_C] + NEIGHBOURS


def build_job_via_node(frame=FRAME, product="vigiles",
                       timestamp=TIMESTAMP):
    with tempfile.TemporaryDirectory() as td:
        frame_path = os.path.join(td, "frame.bin")
        job_path = os.path.join(td, "job.json")
        script = os.path.join(td, "build.mjs")
        with open(frame_path, "wb") as f:
            f.write(frame)
        with open(script, "w") as f:
            f.write(
                'import { readFileSync, writeFileSync } from "node:fs";\n'
                f'import {{ buildQueueJob }} from '
                f'"file://{REPO}/server/queue.mjs";\n'
                "const job = buildQueueJob({ product: process.argv[3], "
                "timestamp: process.argv[4], "
                "imageBytes: readFileSync(process.argv[2]) });\n"
                "writeFileSync(process.argv[5], JSON.stringify(job));\n")
        p = subprocess.run(
            ["node", script, frame_path, product, timestamp, job_path],
            capture_output=True, text=True, timeout=60)
        if p.returncode != 0:
            raise RuntimeError(f"buildQueueJob failed: {p.stderr[:300]}")
        with open(job_path) as f:
            return json.load(f)


def canned_result(product, timestamp, frame, category, status="ok"):
    assessment = None
    if status == "ok":
        assessment = {
            "product": product,
            "timestamp": timestamp,
            "observations": [{
                "category": category,
                "description": f"stubbed reading: {category}",
                "evidence": "center of frame",
                "confidence": 0.8,
            }],
            "assessment": {
                "category": category,
                "summary": f"stubbed summary: {category}",
                "uncertainty": ["stubbed uncertainty"],
                "requires_human_review": True,
            },
            "processing": {"model": "muse-spark-1.3", "latency_ms": None},
        }
    return {
        "job_id": crew_common.job_id_for(product, timestamp, frame),
        "status": status, "assessment": assessment,
        "error": None if status == "ok" else "stubbed failure",
        "model": "muse-spark-1.3", "latency_ms": 7,
        "completed_at": timestamp,
    }


class ScriptedAssessor:
    """assess(product, frame, timestamp) answered per product from a
    {product: [category, ...]} script, consumed in call order per
    product; the last entry repeats. Records every call."""

    def __init__(self, script):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls = []

    def __call__(self, product, frame, timestamp):
        self.calls.append({"product": product, "timestamp": timestamp})
        entries = self.script[product]
        entry = entries.pop(0) if len(entries) > 1 else entries[0]
        if entry == "FAILED":
            return canned_result(product, timestamp, frame, None,
                                 status="failed")
        return canned_result(product, timestamp, frame, entry)


def make_crew(tmp, assessor, cameras=ALL_CAMS, dispatch=None):
    records = crew_records.CrewRecords(
        directory=os.path.join(tmp, "crew-data"))
    dispatched = []
    if dispatch is None:
        def dispatch(package):
            dispatched.append(package)
            return {"receipt_id": "sim-test123", "simulated": True}
    crew_obj = crew.Crew(records, assessor,
                         lambda camera: FRAME, dispatch,
                         cameras=cameras)
    return crew_obj, records, dispatched


class EnvelopeIdentityTests(unittest.TestCase):
    def test_crew_envelope_matches_real_build_queue_job(self):
        mine = crew_common.build_job_envelope("vigiles", TIMESTAMP, FRAME)
        theirs = build_job_via_node()
        self.assertEqual(mine, theirs)
        self.assertIsNone(queue_service.validate_envelope(mine))
        self.assertIsNone(crew_common.envelope_error(mine))

    def test_fallback_cameras_load_from_real_js(self):
        cameras, source = crew_common.load_cameras(
            fetch=lambda url: (_ for _ in ()).throw(OSError("blocked")))
        self.assertEqual(source, "fallback-subset")
        self.assertEqual(len(cameras), 60)


class FlagTableTests(unittest.TestCase):
    """The crew's flag rule IS js/command-flag.js's — loaded, not copied."""

    def test_baselines_and_priorities_from_js(self):
        self.assertFalse(
            crew_common.is_flagged_category("ignis", "steam or fog"))
        self.assertFalse(
            crew_common.is_flagged_category("ignis", "flame-like lighting"))
        self.assertTrue(
            crew_common.is_flagged_category("ignis", "visible smoke"))
        self.assertTrue(
            crew_common.is_flagged_category("vigiles", "person down"))
        self.assertFalse(
            crew_common.is_flagged_category("vigiles", "normal activity"))
        self.assertFalse(crew_common.is_flagged_category("nope", "x"))
        self.assertFalse(crew_common.is_flagged_category("vigiles", ""))
        self.assertEqual(
            crew_common.priority_for_category("medicus",
                                              "person on ground"), "high")
        self.assertEqual(
            crew_common.priority_for_category("ignis", "visible flame"),
            "high")
        self.assertIsNone(
            crew_common.priority_for_category("ignis", "steam or fog"))

    def test_distance_meters_known_pair(self):
        d = crew_common.distance_meters(CAM_A, CAM_B)
        self.assertTrue(2300 < d < 2650, d)  # ~2.47 km across the park

    def test_nearest_cameras_excludes_self_and_orders(self):
        near = crew_common.nearest_cameras(ALL_CAMS, CAM_A, limit=3,
                                           exclude_id="cam-a")
        self.assertEqual(len(near), 3)
        self.assertNotIn("cam-a", [e["camera"]["id"] for e in near])
        dists = [e["distance_m"] for e in near]
        self.assertEqual(dists, sorted(dists))


class RecordsTests(unittest.TestCase):
    def test_append_only_timeline_and_duplicate_refusal(self):
        records = crew_records.CrewRecords(
            directory=os.path.join(_TMP, "records-1"))
        rec = {"id": "incident-x", "status": "flagged",
               "created_at": TIMESTAMP, "timeline": []}
        records.create_incident(rec)
        with self.assertRaises(ValueError):
            records.create_incident(rec)
        records.append_timeline("incident-x",
                                {"step": "flag", "category": "person down"})
        records.append_timeline("incident-x",
                                {"step": "reported", "status": "reported"})
        got = records.get_incident("incident-x")
        self.assertEqual([s["step"] for s in got["timeline"]],
                         ["flag", "reported"])
        self.assertEqual(got["timeline"][0]["category"], "person down")
        self.assertEqual(got["status"], "reported")
        with self.assertRaises(KeyError):
            records.append_timeline("incident-missing", {"step": "flag"})

    def test_events_and_status_round_trip(self):
        records = crew_records.CrewRecords(
            directory=os.path.join(_TMP, "records-2"))
        records.append_event({"type": "flag", "camera_id": "cam-a"})
        records.append_event({"type": "review", "verdict": "confirmed"})
        events = records.recent_events(10)
        self.assertEqual([e["type"] for e in events], ["flag", "review"])
        records.write_status({"state": "running"})
        self.assertEqual(records.read_status()["state"], "running")


class CrewPipelineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=_TMP)

    def test_baseline_check_creates_no_incident(self):
        assessor = ScriptedAssessor({"vigiles": ["normal activity"]})
        crew_obj, records, dispatched = make_crew(self.tmp, assessor)
        out = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(out["outcome"], "baseline")
        self.assertEqual(records.list_incidents(), [])
        self.assertEqual(dispatched, [])
        events = records.recent_events(10)
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["outcome"], "baseline")

    def test_feed_error_is_recorded_not_hidden(self):
        records = crew_records.CrewRecords(
            directory=os.path.join(self.tmp, "crew-data"))
        crew_obj = crew.Crew(
            records, ScriptedAssessor({"vigiles": ["normal activity"]}),
            lambda camera: (_ for _ in ()).throw(OSError("egress blocked")),
            lambda package: {"receipt_id": "sim-x"}, cameras=ALL_CAMS)
        out = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(out["outcome"], "feed-error")
        events = records.recent_events(10)
        self.assertEqual(events[0]["outcome"], "feed-error")
        self.assertIn("egress blocked", events[0]["error"])

    def test_review_clears_lookalike_flag(self):
        assessor = ScriptedAssessor(
            {"vigiles": ["possible altercation", "normal activity"]})
        crew_obj, records, dispatched = make_crew(self.tmp, assessor)
        out = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(out["outcome"], "cleared-by-review")
        self.assertEqual(len(assessor.calls), 2)  # patrol + review only
        self.assertEqual(dispatched, [])
        incident = records.list_incidents()[0]
        # Orchestrator lifecycle: the review's look-alike verdict
        # earns a close_candidate decision, recorded on the
        # timeline; the incident closes as a false positive (the
        # record is kept, not erased).
        self.assertEqual(incident["status"], "closed-false-positive")
        steps = [s["step"] for s in incident["timeline"]]
        # The evidence-purged step is the false-positive close's
        # audit of its evidence deletion (evidence.py, 2026-10-31).
        self.assertEqual(steps, ["flag", "decision", "review",
                                 "decision", "evidence-purged"])
        decisions = [s["decision"] for s in incident["timeline"]
                     if s["step"] == "decision"]
        self.assertEqual(decisions, ["investigate", "close_candidate"])
        review_step = [s for s in incident["timeline"]
                       if s["step"] == "review"][0]
        self.assertEqual(review_step["verdict"], "cleared")
        self.assertEqual(review_step["category"], "normal activity")

    def test_review_inconclusive_holds_flag_without_spend(self):
        assessor = ScriptedAssessor(
            {"vigiles": ["person down", "FAILED"]})
        crew_obj, records, dispatched = make_crew(self.tmp, assessor)
        out = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(out["outcome"], "flagged-unconfirmed")
        self.assertEqual(len(assessor.calls), 2)
        self.assertEqual(dispatched, [])
        incident = records.list_incidents()[0]
        # Orchestrator lifecycle: an inconclusive review earns a
        # continue_monitoring decision — the incident stays open
        # in monitoring, unconfirmed, with no further spend.
        self.assertEqual(incident["status"], "monitoring")
        review_step = [s for s in incident["timeline"]
                       if s["step"] == "review"][0]
        self.assertEqual(review_step["verdict"], "inconclusive")
        decisions = [s["decision"] for s in incident["timeline"]
                     if s["step"] == "decision"]
        self.assertEqual(decisions,
                         ["investigate", "continue_monitoring"])

    def test_confirmed_flag_full_pipeline_and_bound(self):
        assessor = ScriptedAssessor({
            # patrol flag, review confirms, neighbours baseline
            "vigiles": ["person down", "person down", "normal activity"],
            "ignis": ["no hazard visible"],
            "medicus": ["normal activity"],
        })
        crew_obj, records, dispatched = make_crew(self.tmp, assessor)
        out = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(out["outcome"], "dispatched-simulated")
        incident = records.list_incidents()[0]
        self.assertEqual(incident["status"], "dispatched-simulated")
        steps = [s["step"] for s in incident["timeline"]]
        # Orchestrator decisions interleave the work steps: the
        # sequence of work is the one the fixed pipeline ran, but
        # each stage was chosen by a recorded decision.
        work = [s for s in steps if s != "decision"]
        self.assertEqual(work[0], "flag")
        self.assertEqual(work[1], "review")
        self.assertEqual(work[2], "reported")
        decisions = [s["decision"] for s in incident["timeline"]
                     if s["step"] == "decision"]
        self.assertEqual(decisions, ["investigate", "investigate",
                                     "prepare_response"])
        inv = [s for s in incident["timeline"]
               if s["step"] == "investigation"]
        # 2 cross-lens + 3 neighbours = 5, under the stated cap of 6.
        self.assertEqual(len(inv), 5)
        self.assertLessEqual(len(inv), crew.MAX_INVESTIGATION_CALLS)
        self.assertEqual(work[-3:], ["brief", "bolo", "dispatch"])
        # Total model calls: patrol + review + investigation.
        self.assertEqual(len(assessor.calls), 2 + 5)
        # Review used a DISTINCT timestamp (a distinct job), or the
        # second reading would be the first one's stored result.
        self.assertNotEqual(assessor.calls[0]["timestamp"],
                            assessor.calls[1]["timestamp"])
        # The dispatch package: simulated, briefed, human-review.
        self.assertEqual(len(dispatched), 1)
        package = dispatched[0]
        self.assertIs(package["simulated"], True)
        self.assertIs(package["requires_human_review"], True)
        self.assertIs(
            package["brief"]["assessment"]["requires_human_review"], True)
        self.assertEqual(package["brief"]["assessment"]["category"],
                         "person down")
        for text in package["recommended_actions"].values():
            self.assertIn("For human review", text)
            self.assertNotIn("dispatch", text.lower())

    def test_brief_passes_real_validate_assessment(self):
        assessor = ScriptedAssessor({
            "vigiles": ["person down", "person down", "normal activity"],
            "ignis": ["no hazard visible"],
            "medicus": ["normal activity"],
        })
        crew_obj, records, _ = make_crew(self.tmp, assessor)
        crew_obj.check_camera(CAM_A, "vigiles")
        incident = records.list_incidents()[0]
        brief = [s["brief"] for s in incident["timeline"]
                 if s["step"] == "brief"][0]
        agent = Agent("crew-test", 60, SCHEMA,
                      jobs=trio_store.JobStore(
                          trio_store.LocalSqliteStore(
                              os.path.join(self.tmp, "brief.db"))))
        ok, errors = agent.validate(brief, "vigiles")
        self.assertTrue(ok, errors)


class DispatchBoundaryTests(unittest.TestCase):
    def test_non_loopback_dispatch_urls_refused(self):
        for url in ("https://example.com/dispatch",
                    "http://192.168.1.5:8935/dispatch-simulated",
                    "https://api.emergency.example/911"):
            with self.assertRaises(crew.DispatchBoundaryError):
                crew.check_dispatch_url(url)
        for url in ("http://127.0.0.1:8935/dispatch-simulated",
                    "http://localhost:8935/dispatch-simulated"):
            self.assertEqual(crew.check_dispatch_url(url), url)


class QueueAssessorTests(unittest.TestCase):
    def test_files_exact_envelope_and_reads_result(self):
        store = trio_store.LocalSqliteStore(os.path.join(_TMP, "qa.db"))
        jobs = trio_store.JobStore(store)
        assessor = crew.QueueAssessor(jobs, poll_attempts=3,
                                      poll_interval=0.01,
                                      sleep=lambda s: None)
        expected = canned_result("vigiles", TIMESTAMP, FRAME,
                                 "normal activity")
        jobs.put_result(expected)  # as the resident agent would write
        got = assessor("vigiles", FRAME, TIMESTAMP)
        self.assertEqual(got["job_id"], expected["job_id"])
        env = jobs.job_envelope(expected["job_id"])
        self.assertIsNotNone(env)
        self.assertIsNone(queue_service.validate_envelope(env))


class PatrolTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=_TMP)
        self.records = crew_records.CrewRecords(
            directory=os.path.join(self.tmp, "crew-data"))
        patcher = unittest.mock.patch.object(
            patrol_mod.spark_guardrail, "check", lambda: None)
        patcher.start()
        self.addCleanup(patcher.stop)

    def _patrol(self, remaining=70.0, crew_obj=None):
        if crew_obj is None:
            class FakeCrew:
                def __init__(self):
                    self.seen = []

                def check_camera(self, camera, division):
                    self.seen.append((camera["id"], division))
                    return {"outcome": "baseline",
                            "camera_id": camera["id"],
                            "division": division}
            crew_obj = FakeCrew()
        return patrol_mod.Patrol(
            crew_obj, ALL_CAMS, "fallback-subset", self.records,
            interval_s=0,
            guardrail_status=lambda: {
                "calls": 0, "est_cost_usd": 0.0,
                "test_budget_usd": 75.0, "remaining_usd": remaining},
            sleep=lambda s: None), crew_obj

    def test_order_priority_first_then_round_robin(self):
        order = patrol_mod.patrol_order(ALL_CAMS, {"cam-c"},
                                        start_after_id="cam-a")
        self.assertEqual(order[0]["id"], "cam-c")
        rest = [c["id"] for c in order[1:]]
        self.assertEqual(rest[0], "cam-b")  # round-robin resumes after cam-a

    def test_priority_ids_from_incidents_and_recent_flags(self):
        incidents = [{"camera": CAM_A, "status": "reported"}]
        now = time.time()
        events = [{"type": "flag", "camera_id": "cam-c",
                   "at_epoch": now - 60},
                  {"type": "flag", "camera_id": "cam-b",
                   "at_epoch": now - 7200}]  # outside the 1h window
        priority = patrol_mod.compute_priority_ids(
            ALL_CAMS, incidents, events, now)
        self.assertIn("cam-a", priority)
        self.assertIn("cam-c", priority)
        self.assertNotIn("cam-b", priority)
        # Neighbours of cam-a within 1500 m are prioritized too.
        self.assertIn("cam-n0", priority)

    def test_rotation_cycles_lenses_and_cameras(self):
        patrol_obj, fake = self._patrol()
        for _ in range(4):
            patrol_obj.run_cycle()
        divisions = [d for _, d in fake.seen]
        self.assertEqual(divisions,
                         ["vigiles", "ignis", "medicus", "vigiles"])
        status = self.records.read_status()
        self.assertEqual(status["state"], "running")
        self.assertEqual(status["camera_source"], "fallback-subset")
        self.assertEqual(status["counts"]["checks"], 4)

    def test_budget_pause_files_nothing_and_says_so(self):
        patrol_obj, fake = self._patrol(remaining=1.0)
        out = patrol_obj.run_cycle()
        self.assertEqual(out["outcome"], "paused-budget")
        self.assertEqual(fake.seen, [])  # no check was filed
        status = self.records.read_status()
        self.assertEqual(status["state"], "paused-budget")
        events = self.records.recent_events(10)
        self.assertEqual(events[-1]["type"], "patrol-status")
        self.assertEqual(events[-1]["state"], "paused-budget")


class SimulatedDispatchHttpTests(unittest.TestCase):
    PORT = 18936

    @classmethod
    def setUpClass(cls):
        cls.data_dir = os.path.join(_TMP, "http-crew-data")
        env = dict(os.environ)
        env["TRIO_STORE"] = "local"
        env["TRIO_LOCAL_DB"] = os.path.join(_TMP, "http-crew.db")
        env["TRIO_JOB_NS"] = "trio-test-crew-http"
        env["TRIO_CREW_DATA_DIR"] = cls.data_dir
        cls.proc = subprocess.Popen(
            [sys.executable, os.path.join(QUEUE_DIR, "queue_service.py"),
             "--port", str(cls.PORT)],
            env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        deadline = time.time() + 30
        while time.time() < deadline:
            try:
                with urllib.request.urlopen(
                        f"http://127.0.0.1:{cls.PORT}/health",
                        timeout=2) as r:
                    cls.health = json.loads(r.read())
                return
            except Exception:
                time.sleep(0.25)
        raise RuntimeError("queue_service did not come up")

    @classmethod
    def tearDownClass(cls):
        cls.proc.terminate()
        cls.proc.wait(timeout=10)

    def _post(self, body):
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.PORT}/dispatch-simulated",
            data=json.dumps(body).encode(), method="POST",
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_unlabelled_package_refused(self):
        code, body = self._post({"kind": "imperium-dispatch-package"})
        self.assertEqual(code, 400)
        self.assertIn("simulated", body["error"])

    def test_simulated_package_logged_with_receipt(self):
        package = {"simulated": True,
                   "kind": "imperium-dispatch-package",
                   "incident_id": "incident-test",
                   "requires_human_review": True}
        code, body = self._post(package)
        self.assertEqual(code, 201)
        self.assertIs(body["simulated"], True)
        self.assertTrue(body["receipt_id"].startswith("sim-"))
        self.assertIn("no real emergency service", body["note"])
        with open(os.path.join(self.data_dir, "dispatches.jsonl")) as f:
            lines = [json.loads(line) for line in f if line.strip()]
        logged = [l for l in lines
                  if l.get("incident_id") == "incident-test"]
        self.assertEqual(len(logged), 1)
        self.assertEqual(logged[0]["receipt_id"], body["receipt_id"])


if __name__ == "__main__":
    unittest.main()
