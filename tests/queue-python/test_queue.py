"""Standalone tests for the Trio queue service + resident agent.

Run from the repo root (single documented command, see
server/queue/README.md):

    python3 -m unittest discover -s tests/queue-python -v

Everything here is offline: the store is the local SQLite fallback in
a temp file, the generation transport is a stub, and NO live Spark
call is ever made. The job envelope is built by the REAL
server/queue.mjs buildQueueJob (node subprocess) so the Python side
is tested against the actual Trio-side builder, not a copy of it.
"""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.request

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")
SCHEMA = os.path.join(REPO, "js", "schema.js")

# Force the honest local fallback before any queue module is imported.
_TMP = tempfile.mkdtemp(prefix="trio-queue-tests-")
os.environ["TRIO_STORE"] = "local"
os.environ["TRIO_LOCAL_DB"] = os.path.join(_TMP, "test-local.db")
os.environ["TRIO_JOB_NS"] = "trio-test"
os.environ.pop("SPARK_API_KEY", None)
os.environ.pop("TRIO_SPARK_VIA_HELPER", None)

sys.path.insert(0, QUEUE_DIR)

import queue_service  # noqa: E402
import spark_gen  # noqa: E402
import spark_guardrail  # noqa: E402
import trio_store  # noqa: E402
from trio_agent import Agent  # noqa: E402

FRAME = bytes(range(256)) * 4  # arbitrary bytes; buildQueueJob takes any
PRODUCT = "ignis"
TIMESTAMP = "2026-10-30T06:00:00.000Z"


def build_job_via_node(frame=FRAME, product=PRODUCT, timestamp=TIMESTAMP):
    """The real buildQueueJob from server/queue.mjs."""
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


def python_job_id(product, timestamp, frame):
    """buildQueueJob's deterministic id, mirrored."""
    digest = hashlib.sha256(
        f"{product}\0{timestamp}\0".encode() + frame).hexdigest()
    return f"trio-{digest[:32]}"


class EnvelopeTests(unittest.TestCase):
    def test_node_built_envelope_verifies(self):
        env = build_job_via_node()
        self.assertIsNone(queue_service.validate_envelope(env))
        # The Python mirror of the deterministic id matches node's.
        self.assertEqual(env["id"], python_job_id(PRODUCT, TIMESTAMP, FRAME))
        self.assertEqual(env["image"]["byteLength"], len(FRAME))
        self.assertEqual(env["image"]["sha256"],
                         hashlib.sha256(FRAME).hexdigest())

    def test_tampered_byte_length_refused(self):
        env = build_job_via_node()
        env["image"]["byteLength"] += 1
        self.assertIn("byteLength", queue_service.validate_envelope(env))

    def test_tampered_sha256_refused(self):
        env = build_job_via_node()
        env["image"]["sha256"] = "0" * 64
        self.assertIn("sha256", queue_service.validate_envelope(env))

    def test_unknown_product_refused(self):
        env = build_job_via_node()
        env["product"] = "nope"
        self.assertIn("unknown product",
                      queue_service.validate_envelope(env))

    def test_wrong_kind_refused(self):
        env = build_job_via_node()
        env["kind"] = "something-else"
        self.assertIsNotNone(queue_service.validate_envelope(env))


class GuardrailTests(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(_TMP, f"guardrail-{self._testMethodName}"
                                       ".json")

    def test_estimate_math(self):
        est = spark_guardrail.estimate(
            {"prompt_tokens": 1_000_000, "completion_tokens": 1_000_000})
        self.assertAlmostEqual(est, 1.25 + 4.25)

    def test_record_counts_and_cumulates(self):
        spark_guardrail.record("assess:ignis", "muse-spark-1.3",
                               {"prompt_tokens": 1000,
                                "completion_tokens": 1000}, 42,
                               path=self.path)
        st = spark_guardrail.status(self.path)
        self.assertEqual(st["calls"], 1)
        self.assertGreater(st["est_cost_usd"], 0)
        self.assertLess(st["est_cost_usd"], 0.01)

    def test_stop_at_budget(self):
        with open(self.path, "w") as f:
            json.dump({"calls": 999, "est_cost_usd":
                       spark_guardrail.TEST_BUDGET_USD, "log": []}, f)
        with self.assertRaises(spark_guardrail.GuardrailStop):
            spark_guardrail.check(path=self.path)

    def test_check_passes_under_budget(self):
        spark_guardrail.check(path=self.path)  # no state file yet: fine


class ResultShapeTests(unittest.TestCase):
    def test_result_round_trip_exact_keys(self):
        store = trio_store.LocalSqliteStore(
            os.path.join(_TMP, "shape.db"))
        jobs = trio_store.JobStore(store)
        result = {
            "job_id": "trio-abc", "status": "ok", "assessment": {"x": 1},
            "error": None, "model": "muse-spark-1.3", "latency_ms": 12,
            "completed_at": "2026-10-30T06:01:00.000Z",
        }
        jobs.put_result(result)
        got = jobs.get_result("trio-abc")
        self.assertEqual(set(got.keys()),
                         {"job_id", "status", "assessment", "error",
                          "model", "latency_ms", "completed_at"})
        self.assertEqual(got, result)
        # Result keys live at trio:{jid}:result regardless of namespace.
        self.assertEqual(trio_store.result_key("trio-abc"),
                         "trio:trio-abc:result")


def canned_assessment(product, timestamp):
    return {
        "product": product,
        "timestamp": timestamp,
        "observations": [{
            "category": "steam or fog",
            "description": "dense white vapor",
            "evidence": "center of frame",
            "confidence": None,
        }],
        "assessment": {
            "category": "steam or fog",
            "summary": "white vapor visible",
            "uncertainty": ["cannot distinguish steam from fog"],
            "requires_human_review": True,
        },
        "processing": {"model": "muse-spark-1.3", "latency_ms": None},
    }


class StubbedRoundTripTests(unittest.TestCase):
    def test_submit_serve_result_and_idempotent_skip(self):
        store = trio_store.LocalSqliteStore(
            os.path.join(_TMP, "roundtrip.db"))
        jobs = trio_store.JobStore(store)
        env = build_job_via_node()
        jid, created = jobs.submit(env)
        self.assertTrue(created)
        jid2, created2 = jobs.submit(env)
        self.assertEqual((jid2, created2), (jid, False))  # idempotent

        calls = []

        def stub_generate(product, image_path, timestamp):
            calls.append(product)
            return canned_assessment(product, timestamp), \
                "muse-spark-1.3", 123

        agent = Agent("test-agent", 60, SCHEMA, jobs=jobs)
        agent.generate = stub_generate
        report = agent.serve_once()
        self.assertEqual(report["done"], [jid])
        self.assertEqual(calls, [PRODUCT])  # exactly one generation

        result = jobs.get_result(jid)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["job_id"], jid)
        self.assertEqual(
            result["assessment"]["assessment"]["category"], "steam or fog")
        self.assertEqual(result["model"], "muse-spark-1.3")
        self.assertEqual(result["latency_ms"], 123)
        self.assertIsNone(result["error"])

        # Reopen the job by hand: the agent must skip, never re-bill.
        store.hset(trio_store.job_key(jid), {"status": "open"})
        report2 = agent.serve_once()
        self.assertEqual(report2["skipped"], [jid])
        self.assertEqual(calls, [PRODUCT])  # still exactly one

    def test_invalid_model_output_becomes_failed_never_written(self):
        store = trio_store.LocalSqliteStore(
            os.path.join(_TMP, "invalid.db"))
        jobs = trio_store.JobStore(store)
        env = build_job_via_node()
        jid, _ = jobs.submit(env)
        agent = Agent("test-agent", 60, SCHEMA, jobs=jobs)
        agent.generate = lambda p, i, t: ({"not": "a contract"}, "m", 1)
        report = agent.serve_once()
        self.assertEqual(report["failed"], [jid])
        result = jobs.get_result(jid)
        self.assertEqual(result["status"], "failed")
        self.assertIsNone(result["assessment"])
        self.assertIn("validateAssessment", result["error"])


class HttpServiceTests(unittest.TestCase):
    PORT = 18935

    @classmethod
    def setUpClass(cls):
        env = dict(os.environ)
        env["TRIO_STORE"] = "local"
        env["TRIO_LOCAL_DB"] = os.path.join(_TMP, "http.db")
        env["TRIO_JOB_NS"] = "trio-test-http"
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

    def _req(self, method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(
            f"http://127.0.0.1:{self.PORT}{path}", data=data, method=method,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_health_names_fallback_store_honestly(self):
        self.assertTrue(self.health["ok"])
        self.assertEqual(self.health["store"], "local-sqlite-FALLBACK")
        self.assertTrue(self.health["store_fallback"])
        self.assertEqual(self.health["namespace"], "trio-test-http")

    def test_post_idempotent_and_result_pending_then_unknown(self):
        env = build_job_via_node()
        code, body = self._req("POST", "/jobs", env)
        self.assertEqual(code, 201)
        self.assertEqual(body["jobId"], env["id"])
        code2, _ = self._req("POST", "/jobs", env)
        self.assertEqual(code2, 200)  # already filed
        code3, body3 = self._req("GET", f"/jobs/{env['id']}/result")
        self.assertEqual(code3, 404)
        self.assertEqual(body3["status"], "pending")
        code4, body4 = self._req("GET", "/jobs/trio-nope/result")
        self.assertEqual(code4, 404)
        self.assertEqual(body4["status"], "unknown")

    def test_tampered_envelope_is_400_never_filed(self):
        env = build_job_via_node()
        env["image"]["byteLength"] += 5
        code, body = self._req("POST", "/jobs", env)
        self.assertEqual(code, 400)
        self.assertIn("byteLength", body["error"])


class DirectTransportStubTests(unittest.TestCase):
    """The production SPARK_API_KEY transport, with the HTTP layer
    stubbed: verifies the request shape Rowan's SPARK-TRANSPORT-1
    uses (endpoint, model, text + image_url data-URL parts, key only
    in the Authorization header) and that the guardrail counts the
    call. NO live call: the opener is fake and the key is a dummy."""

    def test_direct_request_shape_and_guardrail(self):
        import io
        import urllib.request
        from unittest import mock

        jpeg = os.path.join(_TMP, "frame.jpg")
        with open(jpeg, "wb") as f:
            f.write(b"\xff\xd8\xff\xe0" + b"\x00" * 64)
        payload = {
            "model": "muse-spark-1.3",
            "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            "choices": [{"message": {"content": json.dumps(
                canned_assessment(PRODUCT, TIMESTAMP))}}],
        }
        captured = {}

        class FakeResp:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def read(self):
                return json.dumps(payload).encode()

        class FakeOpener:
            def open(self, req, timeout=None):
                captured["req"] = req
                return FakeResp()

        state_path = os.path.join(_TMP, "direct-guardrail.json")
        self.addCleanup(os.environ.pop, "SPARK_API_KEY", None)
        os.environ["SPARK_API_KEY"] = "dummy-test-key-not-a-secret"
        with mock.patch.object(urllib.request, "build_opener",
                               lambda *a: FakeOpener()), \
                mock.patch.object(spark_guardrail, "STATE_PATH",
                                  state_path):
            assessment, model, latency = spark_gen.generate(
                PRODUCT, jpeg, TIMESTAMP)

        self.assertEqual(assessment["assessment"]["category"],
                         "steam or fog")
        self.assertEqual(model, "muse-spark-1.3")
        self.assertIsInstance(latency, int)
        req = captured["req"]
        self.assertEqual(req.full_url, spark_gen.SPARK_ENDPOINT)
        self.assertEqual(req.get_header("Authorization"),
                         "Bearer dummy-test-key-not-a-secret")
        body = json.loads(req.data)
        self.assertEqual(body["model"], "muse-spark-1.3")
        parts = body["messages"][0]["content"]
        self.assertEqual(parts[0]["type"], "text")
        self.assertIn("steam or fog", parts[0]["text"])
        self.assertEqual(parts[1]["type"], "image_url")
        self.assertTrue(parts[1]["image_url"]["url"].startswith(
            "data:image/jpeg;base64,"))
        st = spark_guardrail.status(state_path)
        self.assertEqual(st["calls"], 1)  # guardrail counted it

    def test_no_key_and_no_helper_is_a_clean_refusal(self):
        os.environ.pop("SPARK_API_KEY", None)
        jpeg = os.path.join(_TMP, "frame.jpg")
        with self.assertRaises(RuntimeError) as cm:
            spark_gen.generate(PRODUCT, jpeg, TIMESTAMP)
        self.assertIn("SPARK_API_KEY", str(cm.exception))


class RelayNotifyHookTests(unittest.TestCase):
    """The OPTIONAL Meta Nuntius hook (TRIO_RELAY_URL): a finished
    job posts one NOTIFY line to a stub HTTP recorder on localhost;
    with the env unset nothing is posted; with the relay dead the
    job still completes. No real relay, no live calls."""

    def setUp(self):
        self._saved = os.environ.get("TRIO_RELAY_URL")
        self.addCleanup(self._restore_env)

    def _restore_env(self):
        if self._saved is None:
            os.environ.pop("TRIO_RELAY_URL", None)
        else:
            os.environ["TRIO_RELAY_URL"] = self._saved

    def _start_recorder(self):
        import threading
        from http.server import BaseHTTPRequestHandler, HTTPServer

        recorded = []

        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                length = int(self.headers.get("Content-Length") or 0)
                raw = self.rfile.read(length) if length else b"{}"
                recorded.append((self.path, json.loads(raw)))
                body = json.dumps(
                    {"index": 0, "id": "ntf-0123456789abcdef"}).encode()
                self.send_response(201)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        srv = HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        self.addCleanup(srv.shutdown)
        return srv, recorded

    def _serve_with_stub(self, db_name, generate):
        store = trio_store.LocalSqliteStore(os.path.join(_TMP, db_name))
        jobs = trio_store.JobStore(store)
        env = build_job_via_node()
        jid, _ = jobs.submit(env)
        agent = Agent("test-agent", 60, SCHEMA, jobs=jobs)
        agent.generate = generate
        return jid, jobs, agent.serve_once()

    def test_ok_result_posts_info_notify(self):
        srv, recorded = self._start_recorder()
        os.environ["TRIO_RELAY_URL"] = \
            f"http://127.0.0.1:{srv.server_address[1]}"
        jid, jobs, report = self._serve_with_stub(
            "notify-ok.db",
            lambda p, i, t: (canned_assessment(p, t), "muse-spark-1.3", 7))
        self.assertEqual(report["done"], [jid])
        self.assertEqual(len(recorded), 1)
        path, body = recorded[0]
        self.assertEqual(path, "/rooms/main/notify")
        self.assertEqual(body["topic"], "trio-result")
        self.assertEqual(body["severity"], "info")
        self.assertIn(jid, body["text"])
        self.assertIn("ignis", body["text"])
        self.assertIn("steam or fog", body["text"])

    def test_failed_result_posts_warning_notify(self):
        srv, recorded = self._start_recorder()
        os.environ["TRIO_RELAY_URL"] = \
            f"http://127.0.0.1:{srv.server_address[1]}"
        jid, jobs, report = self._serve_with_stub(
            "notify-failed.db",
            lambda p, i, t: ({"not": "a contract"}, "m", 1))
        self.assertEqual(report["failed"], [jid])
        self.assertEqual(len(recorded), 1)
        path, body = recorded[0]
        self.assertEqual(path, "/rooms/main/notify")
        self.assertEqual(body["severity"], "warning")
        self.assertIn(jid, body["text"])
        self.assertIn("failed:", body["text"])

    def test_unset_env_posts_nothing(self):
        srv, recorded = self._start_recorder()
        os.environ.pop("TRIO_RELAY_URL", None)
        jid, jobs, report = self._serve_with_stub(
            "notify-unset.db",
            lambda p, i, t: (canned_assessment(p, t), "muse-spark-1.3", 7))
        self.assertEqual(report["done"], [jid])
        self.assertEqual(recorded, [])

    def test_dead_relay_never_fails_the_job(self):
        os.environ["TRIO_RELAY_URL"] = "http://127.0.0.1:1"
        jid, jobs, report = self._serve_with_stub(
            "notify-dead.db",
            lambda p, i, t: (canned_assessment(p, t), "muse-spark-1.3", 7))
        self.assertEqual(report["done"], [jid])
        self.assertEqual(jobs.get_result(jid)["status"], "ok")


if __name__ == "__main__":
    unittest.main()
