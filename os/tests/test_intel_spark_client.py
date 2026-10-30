"""intel/spark_client.py: transports, retries, budget, ledger (FND-005/6/7).

HTTP tests simulate responses at the urllib boundary (the shipped
client code is all real). Agent tests run the full dispatch -> claim
-> complete cycle through the REAL jobs machinery on FakeUpstash,
with a scripted test-harness agent working the queue — the transport
code under test is the shipped code; no live crew agent exists yet,
so live end-to-end remains NOT YET VERIFIED (see spark_client docs).
"""
import contextlib
import hashlib
import io
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
from unittest import mock

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
import relay_common as rc  # noqa: E402
import jobs  # noqa: E402
from intel import spark_client as sc  # noqa: E402
from intel import store as istore  # noqa: E402
from mos import capabilities  # noqa: E402


def _ok_body(text="hello", usage=True):
    body = {"choices": [{"message": {"content": text}}]}
    if usage:
        body["usage"] = {"prompt_tokens": 1000, "completion_tokens": 1000}
    return body


class _FakeResp:
    def __init__(self, body):
        self._body = body

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _scripted_urlopen(script, calls):
    def fake_urlopen(req, timeout=None):
        calls.append(req)
        item = script.pop(0)
        if isinstance(item, int):
            raise urllib.error.HTTPError(
                req.full_url, item, "err", {}, io.BytesIO(b"nope"))
        return _FakeResp(json.dumps(item).encode())
    return fake_urlopen


class HttpTransportTest(RelayTestCase):
    def _client(self, **kw):
        kw.setdefault("transport", "http")
        kw.setdefault("endpoint", "https://api.example.invalid/v1/chat")
        kw.setdefault("api_key", "test-key")
        kw.setdefault("backoff_base", 0)
        return sc.SparkClient(**kw)

    def _patch_http(self, script):
        calls = []
        p = mock.patch.object(
            urllib.request, "urlopen", _scripted_urlopen(script, calls))
        p.start()
        self.addCleanup(p.stop)
        return calls

    def test_unconfigured_http_raises_and_sends_nothing(self):
        calls = self._patch_http([_ok_body()])
        client = sc.SparkClient(transport="http", endpoint="", api_key="")
        self.assertFalse(client.configured)
        with self.assertRaises(sc.SparkNotConfigured):
            client.complete("hi")
        self.assertEqual(calls, [])

    def test_429_then_200(self):
        calls = self._patch_http([429, _ok_body("recovered")])
        client = self._client()
        self.assertEqual(client.complete("hi", lane_feature="brief"),
                         "recovered")
        self.assertEqual(len(calls), 2)
        auth = calls[0].get_header("Authorization")
        self.assertEqual(auth, "Bearer test-key")
        entries = istore.spend_entries()
        self.assertEqual(len(entries), 1)
        e = entries[0]
        self.assertEqual(e["lane_feature"], "brief")
        self.assertEqual(e["tokens_in"], 1000)
        self.assertEqual(e["tokens_out"], 1000)
        self.assertEqual(e["usage"], "reported")
        self.assertAlmostEqual(e["est_cost"], 0.018, places=6)
        self.assertAlmostEqual(istore.spend_total(), 0.018, places=6)

    def test_permanent_500_exhausts_retries(self):
        calls = self._patch_http([500, 500, 500, 500])
        client = self._client()
        with self.assertRaises(sc.SparkHTTPError) as cm:
            client.complete("hi")
        self.assertEqual(cm.exception.status, 500)
        self.assertEqual(len(calls), 3)  # 1 attempt + 2 retries
        self.assertEqual(istore.spend_entries(), [])

    def test_400_is_not_retried(self):
        calls = self._patch_http([400, _ok_body()])
        client = self._client()
        with self.assertRaises(sc.SparkHTTPError):
            client.complete("hi")
        self.assertEqual(len(calls), 1)

    def test_session_budget_cap_stops_third_call(self):
        calls = self._patch_http(
            [_ok_body(), _ok_body(), _ok_body(), _ok_body()])
        client = self._client(max_spend_usd=0.03)
        client.complete("one")   # est 0.018
        client.complete("two")   # est 0.018 -> spent 0.036 >= cap
        with self.assertRaises(sc.SparkBudgetError):
            client.complete("three")
        self.assertEqual(len(calls), 2)

    def test_per_call_cap_blocks_before_network(self):
        calls = self._patch_http([_ok_body()])
        client = self._client(per_call_cap_usd=0.01)
        with self.assertRaises(sc.SparkBudgetError):
            client.complete("hi", max_tokens=1000)
        self.assertEqual(calls, [])

    def test_missing_usage_is_flagged_estimated(self):
        self._patch_http([_ok_body("no usage", usage=False)])
        client = self._client()
        self.assertEqual(client.complete("hello there"), "no usage")
        e = istore.spend_entries()[0]
        self.assertEqual(e["usage"], "estimated")
        self.assertGreater(e["tokens_in"], 0)
        self.assertGreater(e["est_cost"], 0)


class _ScriptedAgent(threading.Thread):
    """Test-harness resident agent working SPARK jobs off the queue.

    behavior(n, jid, spec) decides the n-th (1-based) SPARK job:
      ("done", body, commit)  write result body, finish with commit
      ("blocked", reason)     mark the job blocked
      ("die",)                claim, then never finish (dead agent)
    Claims/finishes go through jobs.main — the real queue machinery.
    """

    def __init__(self, behavior, nick="sparkagent", claim_lease=1800):
        super().__init__(daemon=True)
        self.behavior = behavior
        self.nick = nick
        self.claim_lease = claim_lease
        self.stop_event = threading.Event()
        self.seen = set()
        self.worked = 0

    def run(self):
        while not self.stop_event.is_set():
            try:
                self._cycle()
            except Exception:
                pass
            time.sleep(0.01)

    def _cycle(self):
        ids = json.loads(
            rc.api_get(f"zrange/{jobs._index_key()}/0/-1"))["result"] or []
        for jid in ids:
            if jid in self.seen:
                continue
            h, spec = jobs.job_get(jid)
            if not h or h.get("status") != "open":
                continue
            try:
                env = json.loads(spec or "")
            except ValueError:
                continue
            if env.get("kind") != "spark-complete":
                continue
            self.seen.add(jid)
            self.worked += 1
            self._work(jid, env)

    def _work(self, jid, env):
        jobs.NICK = self.nick
        with contextlib.redirect_stdout(io.StringIO()):
            code = jobs.main(
                ["claim", jid, "--lease", str(self.claim_lease)])
        if code != 0:
            return
        action = self.behavior(self.worked, jid, env)
        if action[0] == "die":
            return
        if action[0] == "blocked":
            with contextlib.redirect_stdout(io.StringIO()):
                jobs.main(["blocked", jid, "--reason", action[1]])
            return
        _, body, commit = action
        rc.api_post(f"set/{env['job_ns']}:{jid}:result", body)
        with contextlib.redirect_stdout(io.StringIO()):
            jobs.main(["done", jid, "--commit", commit,
                       "--note", "spark completion"])


def _envelope_body(text, tokens_in=42, tokens_out=17):
    return json.dumps(
        {"text": text, "tokens_in": tokens_in, "tokens_out": tokens_out},
        sort_keys=True)


def _sha_commit(body):
    return "sha256:" + hashlib.sha256(body.encode()).hexdigest()


class AgentTransportTest(RelayTestCase):
    def setUp(self):
        super().setUp()
        p = mock.patch.object(rc, "RELAY_URL", "https://fake.invalid")
        p.start()
        self.addCleanup(p.stop)
        capabilities.register("sparkagent", ["spark"],
                              dm_secret="sparkdm")
        self.agent = None
        self.addCleanup(self._stop_agent)

    def _stop_agent(self):
        if self.agent:
            self.agent.stop_event.set()
            self.agent.join(timeout=2)

    def _start_agent(self, behavior, **kw):
        self.agent = _ScriptedAgent(behavior, **kw)
        self.agent.start()
        return self.agent

    def _client(self, **kw):
        kw.setdefault("agent_poll_interval", 0.02)
        kw.setdefault("agent_timeout", 120)
        return sc.SparkClient(**kw)

    def test_default_transport_is_agent(self):
        with mock.patch.dict(os.environ):
            os.environ.pop("SPARK_TRANSPORT", None)
            self.assertEqual(sc.SparkClient().transport_name, "agent")

    def test_unknown_transport_is_not_configured(self):
        client = sc.SparkClient(transport="carrier-pigeon")
        with self.assertRaises(sc.SparkNotConfigured):
            client.complete("hi")

    def test_agent_unavailable_without_bus_config(self):
        with mock.patch.object(rc, "RELAY_URL", ""):
            client = self._client()
            self.assertFalse(client.configured)
            with self.assertRaises(sc.SparkNotConfigured):
                client.complete("hi")

    def test_end_to_end_reported_usage(self):
        body = _envelope_body("the agent answered")
        self._start_agent(lambda n, jid, env: ("done", body,
                                               _sha_commit(body)))
        client = self._client()
        self.assertEqual(
            client.complete("say it", lane_feature="brief"),
            "the agent answered")
        e = istore.spend_entries()[0]
        self.assertEqual(e["tokens_in"], 42)
        self.assertEqual(e["tokens_out"], 17)
        self.assertEqual(e["usage"], "reported")
        self.assertAlmostEqual(e["est_cost"], 0.000381, places=6)
        ids = json.loads(
            rc.api_get(f"zrange/{jobs._index_key()}/0/-1"))["result"]
        h, spec = jobs.job_get(ids[-1])
        self.assertEqual(h["status"], "done")
        self.assertEqual(json.loads(spec)["kind"], "spark-complete")

    def test_plain_text_result_is_unreported(self):
        self._start_agent(
            lambda n, jid, env: ("done", "plain answer", "deadbeef"))
        client = self._client()
        self.assertEqual(client.complete("say it"), "plain answer")
        e = istore.spend_entries()[0]
        self.assertEqual(e["usage"], "unreported")
        self.assertIsNone(e["tokens_in"])
        self.assertIsNone(e["tokens_out"])
        self.assertIsNone(e["est_cost"])

    def test_digest_mismatch_is_rejected(self):
        body = _envelope_body("tampered")
        self._start_agent(
            lambda n, jid, env: ("done", body, "sha256:" + "0" * 64))
        client = self._client()
        with self.assertRaises(sc.SparkResponseError):
            client.complete("say it")

    def test_blocked_job_raises_with_reason(self):
        self._start_agent(
            lambda n, jid, env: ("blocked", "needs a human decision"))
        client = self._client()
        with self.assertRaises(sc.SparkAgentError) as cm:
            client.complete("say it")
        self.assertIn("needs a human decision", str(cm.exception))

    def _advance_and_yield(self, secs):
        # Advance the fake clock (drives lease TTLs + the transport
        # deadline) and yield real time so the agent thread can work.
        self.fake.advance(secs)
        time.sleep(0.01)

    def test_timeout_leaves_job_open(self):
        transport = sc.AgentTransport(
            timeout=30, poll_interval=5,
            now_fn=self.fake.now, sleep_fn=self._advance_and_yield)
        with self.assertRaises(sc.SparkTimeoutError):
            transport.complete("anyone there?")
        ids = json.loads(
            rc.api_get(f"zrange/{jobs._index_key()}/0/-1"))["result"]
        self.assertEqual(len(ids), 1)
        h, _ = jobs.job_get(ids[0])
        self.assertEqual(h["status"], "open")

    def test_abandoned_claim_is_redispatched(self):
        body = _envelope_body("second agent answered")

        def behavior(n, jid, env):
            if n == 1:
                return ("die",)
            return ("done", body, _sha_commit(body))

        self._start_agent(behavior, claim_lease=60)
        transport = sc.AgentTransport(
            timeout=600, poll_interval=5,
            now_fn=self.fake.now, sleep_fn=self._advance_and_yield)
        outcome = transport.complete("say it", max_retries=2)
        self.assertEqual(outcome.text, "second agent answered")
        ids = json.loads(
            rc.api_get(f"zrange/{jobs._index_key()}/0/-1"))["result"]
        self.assertEqual(len(ids), 2)
        h2, _ = jobs.job_get(ids[-1])
        self.assertEqual(h2["status"], "done")
