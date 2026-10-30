"""intel/spark_agent.py: the resident-agent side of the Spark contract.

The shipped handler binds no generation of its own. The `generate`
callables below are test doubles supplied by the tests as the
caller — in production that caller is the resident Muse Spark crew
agent process. Everything else here is the real machinery: jobs.py
claim/lease/done/blocked and mos.capabilities on FakeUpstash, with
the real spark_client AgentTransport as the dispatcher in the cycle
tests. A live end-to-end Spark call against the real bus remains
NOT YET VERIFIED (see spark_agent docs).
"""
import contextlib
import hashlib
import io
import json
import sys
import threading
import time
from unittest import mock

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
import relay_common as rc  # noqa: E402
import jobs  # noqa: E402
from intel import spark_agent as sa  # noqa: E402
from intel import spark_client as sc  # noqa: E402
from intel import store as istore  # noqa: E402
from mos import capabilities  # noqa: E402


def _gen(text, tokens_in=11, tokens_out=7):
    def generate(prompt, system=None, max_tokens=1024):
        return {"text": text, "tokens_in": tokens_in,
                "tokens_out": tokens_out}
    return generate


def _post_spark_job(prompt="say it", lease=1800):
    """Post a spark job exactly the way AgentTransport._dispatch does."""
    spec = json.dumps({
        "kind": "spark-complete",
        "v": 1,
        "lane_feature": "test",
        "system": None,
        "prompt": prompt,
        "max_tokens": 1024,
        "job_ns": jobs.NS,
        "result_key_pattern": "{job_ns}:{jid}:result",
    }, sort_keys=True)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = jobs.main(["post", "--title", "SPARK:test",
                          "--spec", spec, "--lease", str(lease)])
    assert code == 0, buf.getvalue()
    for line in buf.getvalue().splitlines():
        if line.startswith("JOB "):
            return line.split()[1]
    raise AssertionError("no job id in post output")


def _result_body(jid):
    raw = json.loads(
        rc.api_get(f"get/{jobs.NS}:{jid}:result"))["result"]
    return raw


class _Serving(threading.Thread):
    """Run a SparkAgent's serve_once loop until stopped."""

    def __init__(self, agent, gate=None):
        super().__init__(daemon=True)
        self.agent = agent
        self.gate = gate
        self.stop_event = threading.Event()

    def run(self):
        if self.gate is not None:
            self.gate.wait(timeout=10)
        while not self.stop_event.is_set():
            try:
                self.agent.serve_once()
            except Exception:
                pass
            time.sleep(0.01)


class HelperTest(RelayTestCase):
    def test_parse_spark_spec(self):
        env = sa.parse_spark_spec(json.dumps(
            {"kind": "spark-complete", "v": 1, "prompt": "p"}))
        self.assertEqual(env["prompt"], "p")
        self.assertIsNone(sa.parse_spark_spec("plain spec"))
        self.assertIsNone(sa.parse_spark_spec(json.dumps(
            {"kind": "other", "v": 1, "prompt": "p"})))
        self.assertIsNone(sa.parse_spark_spec(json.dumps(
            {"kind": "spark-complete", "v": 2, "prompt": "p"})))
        self.assertIsNone(sa.parse_spark_spec(json.dumps(
            {"kind": "spark-complete", "v": 1})))

    def test_result_body_shapes(self):
        body = sa.result_body_for(
            {"text": "hi", "tokens_in": 3, "tokens_out": 4})
        self.assertEqual(json.loads(body),
                         {"text": "hi", "tokens_in": 3,
                          "tokens_out": 4})
        body = sa.result_body_for({"text": "hi"})
        self.assertEqual(json.loads(body), {"text": "hi"})
        self.assertEqual(sa.result_body_for("raw text"), "raw text")
        with self.assertRaises(ValueError):
            sa.result_body_for({"tokens_in": 1})
        with self.assertRaises(ValueError):
            sa.result_body_for(42)

    def test_result_key_from_envelope(self):
        env = {"job_ns": "muse-bus:job",
               "result_key_pattern": "{job_ns}:{jid}:result"}
        self.assertEqual(sa.result_key_for(env, "7"),
                         "muse-bus:job:7:result")
        self.assertEqual(sa.result_key_for({}, "7"),
                         f"{jobs.NS}:7:result")

    def test_unconfigured_generate_fails_loudly(self):
        with self.assertRaises(sa.GenerationNotConfigured):
            sa.unconfigured_generate("anything")
        agent = sa.SparkAgent(nick="sparkagent")
        self.assertFalse(agent.generation_configured)


class ServeOnceTest(RelayTestCase):
    def _agent(self, **kw):
        kw.setdefault("nick", "sparkagent")
        kw.setdefault("dm_secret", "sparkdm")
        return sa.SparkAgent(**kw)

    def test_serve_once_completes_job_with_digest_commit(self):
        jid = _post_spark_job()
        agent = self._agent(generate=_gen("agent-side answer"))
        report = agent.serve_once()
        self.assertEqual(report["done"], [jid])
        self.assertEqual(report["blocked"], [])
        h, _ = jobs.job_get(jid)
        self.assertEqual(h["status"], "done")
        body = _result_body(jid)
        self.assertEqual(json.loads(body),
                         {"text": "agent-side answer",
                          "tokens_in": 11, "tokens_out": 7})
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.assertEqual(h["result_commit"], f"sha256:{digest}")

    def test_serve_once_registers_spark_capability(self):
        self._agent(generate=_gen("x")).serve_once()
        rec = capabilities.get("sparkagent")
        self.assertIsNotNone(rec)
        self.assertIn("spark", rec["caps"].split(","))
        self.assertIn("sparkagent", capabilities.find_for(["spark"]))

    def test_unreported_counts_when_generation_omits_them(self):
        jid = _post_spark_job()
        agent = self._agent(
            generate=lambda prompt, system=None, max_tokens=1024:
                {"text": "no counts"})
        report = agent.serve_once()
        self.assertEqual(report["done"], [jid])
        self.assertEqual(json.loads(_result_body(jid)),
                         {"text": "no counts"})

    def test_blocks_when_generation_not_configured(self):
        jid = _post_spark_job()
        agent = self._agent()
        report = agent.serve_once()
        self.assertEqual(report["blocked"], [jid])
        h, _ = jobs.job_get(jid)
        self.assertEqual(h["status"], "blocked")
        self.assertIn("not configured", h["note"])

    def test_blocks_with_reason_on_generation_failure(self):
        def boom(prompt, system=None, max_tokens=1024):
            raise RuntimeError("model exploded")

        jid = _post_spark_job()
        agent = self._agent(generate=boom)
        report = agent.serve_once()
        self.assertEqual(report["blocked"], [jid])
        h, _ = jobs.job_get(jid)
        self.assertEqual(h["status"], "blocked")
        self.assertIn("model exploded", h["note"])

    def test_ignores_non_spark_jobs(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            code = jobs.main(["post", "--title", "PLAIN",
                              "--spec", "do a thing"])
        self.assertEqual(code, 0)
        jid = [line.split()[1] for line in buf.getvalue().splitlines()
               if line.startswith("JOB ")][0]
        agent = self._agent(generate=_gen("x"))
        self.assertEqual(agent.open_spark_jobs(), [])
        report = agent.serve_once()
        self.assertEqual(report["done"], [])
        self.assertEqual(report["blocked"], [])
        h, _ = jobs.job_get(jid)
        self.assertEqual(h["status"], "open")


class _DoomedClaimer(threading.Thread):
    """Claim the first open spark job as another nick, then die:
    no finish, no heartbeat, lease left to expire."""

    def __init__(self, nick="deadagent", lease=60):
        super().__init__(daemon=True)
        self.nick = nick
        self.lease = lease
        self.claimed = threading.Event()

    def run(self):
        while not self.claimed.is_set():
            try:
                ids = json.loads(rc.api_get(
                    f"zrange/{jobs._index_key()}/0/-1"))["result"] or []
                for jid in ids:
                    h, spec = jobs.job_get(jid)
                    if not h or h.get("status") != "open":
                        continue
                    if sa.parse_spark_spec(spec) is None:
                        continue
                    jobs.NICK = self.nick
                    with contextlib.redirect_stdout(io.StringIO()):
                        code = jobs.main(
                            ["claim", jid, "--lease", str(self.lease)])
                    if code == 0:
                        self.claimed.set()
                    return
            except Exception:
                pass
            time.sleep(0.005)


class ClientCycleTest(RelayTestCase):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(rc, "RELAY_URL", "https://fake.invalid")
        p.start()
        self.addCleanup(p.stop)
        self.serving = None
        self.addCleanup(self._stop_serving)

    def _stop_serving(self):
        if self.serving:
            self.serving.stop_event.set()
            self.serving.join(timeout=2)

    def _start_serving(self, agent, gate=None):
        self.serving = _Serving(agent, gate=gate)
        self.serving.start()
        return self.serving

    def _client(self, **kw):
        kw.setdefault("agent_poll_interval", 0.02)
        kw.setdefault("agent_timeout", 120)
        return sc.SparkClient(**kw)

    def test_full_cycle_client_handler_result(self):
        agent = sa.SparkAgent(
            generate=_gen("the resident agent answered", 42, 17),
            nick="sparkagent", dm_secret="sparkdm")
        self._start_serving(agent)
        client = self._client()
        text = client.complete("say it", lane_feature="brief")
        self.assertEqual(text, "the resident agent answered")
        e = istore.spend_entries()[0]
        self.assertEqual(e["tokens_in"], 42)
        self.assertEqual(e["tokens_out"], 17)
        self.assertEqual(e["usage"], "reported")
        ids = json.loads(rc.api_get(
            f"zrange/{jobs._index_key()}/0/-1"))["result"]
        h, _ = jobs.job_get(ids[-1])
        self.assertEqual(h["status"], "done")
        body = _result_body(ids[-1])
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        self.assertEqual(h["result_commit"], f"sha256:{digest}")

    def test_full_cycle_unreported_usage(self):
        agent = sa.SparkAgent(
            generate=lambda prompt, system=None, max_tokens=1024:
                {"text": "plain-ish answer"},
            nick="sparkagent", dm_secret="sparkdm")
        self._start_serving(agent)
        client = self._client()
        self.assertEqual(client.complete("say it"), "plain-ish answer")
        e = istore.spend_entries()[0]
        self.assertEqual(e["usage"], "unreported")
        self.assertIsNone(e["tokens_in"])
        self.assertIsNone(e["tokens_out"])

    def test_full_cycle_blocked_when_unconfigured(self):
        agent = sa.SparkAgent(nick="sparkagent", dm_secret="sparkdm")
        self._start_serving(agent)
        client = self._client()
        with self.assertRaises(sc.SparkAgentError) as cm:
            client.complete("say it")
        self.assertIn("not configured", str(cm.exception))

    def _advance_and_yield(self, secs):
        self.fake.advance(secs)
        time.sleep(0.01)

    def test_abandoned_claim_redispatched_and_served(self):
        doomed = _DoomedClaimer()
        doomed.start()
        agent = sa.SparkAgent(
            generate=_gen("second agent answered"),
            nick="sparkagent", dm_secret="sparkdm")
        self._start_serving(agent, gate=doomed.claimed)
        transport = sc.AgentTransport(
            timeout=600, poll_interval=5,
            now_fn=self.fake.now, sleep_fn=self._advance_and_yield)
        outcome = transport.complete("say it", max_retries=2)
        self.assertEqual(outcome.text, "second agent answered")
        ids = json.loads(rc.api_get(
            f"zrange/{jobs._index_key()}/0/-1"))["result"]
        self.assertEqual(len(ids), 2)
        h1, _ = jobs.job_get(ids[0])
        self.assertEqual(h1["status"], "claimed")
        self.assertEqual(h1["claim"], "deadagent")
        h2, _ = jobs.job_get(ids[1])
        self.assertEqual(h2["status"], "done")
