"""intel/spark_client.py — the one Spark gateway (FND-005/006/007).

A completion here is always a real Muse Spark generation. There is
no fake, canned, or fallback output anywhere in this module (Del's
ruling, 2026-10-26: no mock or fake code in the build). Two real
transports can serve a call; SPARK_TRANSPORT selects between them:

  agent (DEFAULT) — AgentTransport: an agent goes in the API key's
      place. The prompt is dispatched as a job through the existing
      job queue (jobs.py, the mos/overseer dispatch pattern) to a
      resident crew agent running Muse Spark, and that agent's
      completion comes back through the queue. See the completion
      contract below.
  http — HttpTransport: a direct chat-completions POST to a Meta
      Model API endpoint. Inert until an endpoint/key is named
      (GOV-001); kept for if/when a key exists.

With neither transport available, complete() raises
SparkNotConfigured before anything is sent — the honest state of the
system, never a silent substitute.

AgentTransport completion contract (the queue's own semantics — post,
atomic claim with lease, done/blocked — plus one result channel,
because jobs.py's done carries a commit hash, not a text payload):

  * The job's spec is a JSON envelope {"kind": "spark-complete",
    "v": 1, "lane_feature", "system", "prompt", "max_tokens",
    "job_ns", "result_key_pattern": "{job_ns}:{jid}:result"}.
  * The job is announced on its room by jobs.py itself, and DM'd to
    every registered agent whose capabilities cover
    SPARK_AGENT_CAPABILITY (default "spark") — the overseer dispatch
    pattern (mos/overseer.dispatch). A resident agent watches either
    channel, claims the job atomically, and heartbeats its lease
    while it generates.
  * The agent writes the completion to the result key
    <job_ns>:<jid>:result with api_post — the same body channel
    jobs.py uses for specs — either as a JSON envelope
    {"text": ..., "tokens_in": ..., "tokens_out": ...} or as plain
    text, then finishes with:
        jobs.py done <jid> --commit sha256:<sha256 of the result body>
    The dispatcher verifies that digest when present.
  * blocked means the agent refused or failed: complete() raises
    SparkAgentError with the agent's reason. A claim whose lease
    expires (agent died) is an abandoned attempt: the call
    re-dispatches as a fresh job, up to the retry budget.
  * Token counts are recorded exactly as the completing agent
    reports them. If the completion carries no counts, the ledger
    entry records null counts with usage "unreported" — counts are
    never fabricated.

Spending (FND-006/007): every served call appends one entry to the
spend ledger via intel.store.record_spend:
{ts, lane_feature, tokens_in, tokens_out, est_cost, usage} with usage
"reported" | "estimated" | "unreported". Budget caps price API spend
at the configured estimate rates, so they gate the HTTP transport;
agent calls carry no API cost (est_cost is computed only when the
agent reports counts, and is null otherwise).

Configuration (environment only; a key is never printed or logged):
  SPARK_TRANSPORT        "agent" (default) | "http"
  SPARK_AGENT_CAPABILITY Capability the resident Spark agent registers
                         (default "spark")
  SPARK_AGENT_ROOM       Room for Spark job announcements (default:
                         the default room)
  SPARK_AGENT_TIMEOUT    Seconds to wait for a completion (default 900)
  SPARK_AGENT_LEASE      Job lease seconds (default 1800, jobs.py's)
  SPARK_AGENT_POLL       Poll interval seconds (default 2)
  META_MODEL_API_URL     HTTP transport: full endpoint URL
  META_MODEL_API_KEY     HTTP transport: bearer key
  META_MODEL_API_MODEL   HTTP transport: model id (default "muse-spark")
  META_MODEL_API_TIMEOUT HTTP per-attempt timeout seconds (default 60)
  META_MODEL_API_MAX_SPEND_USD / META_MODEL_API_PER_CALL_USD
                         Optional budget caps (HTTP transport)
  META_MODEL_API_INPUT_USD_PER_MTOK / META_MODEL_API_OUTPUT_USD_PER_MTOK
                         Rates for cost ESTIMATES; defaults are
                         planning placeholders, not pricing facts.

Live verification: NOT YET VERIFIED end to end for either transport.
HTTP has no endpoint/key (GOV-001 BLOCKED). AgentTransport needs a
resident crew agent process polling the queue with the "spark"
capability; the agent side now exists (intel/spark_agent.py) but no
resident process is standing by on the live queue yet. The unit
tests exercise the full dispatch/claim/complete cycle against the
real jobs machinery on the test Redis fake.
"""
import contextlib
import hashlib
import io
import json
import math
import os
import sys
import time
import urllib.error
import urllib.request

import relay_common as rc

from . import store as _store

ENV_TRANSPORT = "SPARK_TRANSPORT"
ENV_AGENT_CAPABILITY = "SPARK_AGENT_CAPABILITY"
ENV_AGENT_ROOM = "SPARK_AGENT_ROOM"
ENV_AGENT_TIMEOUT = "SPARK_AGENT_TIMEOUT"
ENV_AGENT_LEASE = "SPARK_AGENT_LEASE"
ENV_AGENT_POLL = "SPARK_AGENT_POLL"
ENV_URL = "META_MODEL_API_URL"
ENV_KEY = "META_MODEL_API_KEY"
ENV_MODEL = "META_MODEL_API_MODEL"
ENV_TIMEOUT = "META_MODEL_API_TIMEOUT"
ENV_MAX_SPEND = "META_MODEL_API_MAX_SPEND_USD"
ENV_PER_CALL = "META_MODEL_API_PER_CALL_USD"
ENV_RATE_IN = "META_MODEL_API_INPUT_USD_PER_MTOK"
ENV_RATE_OUT = "META_MODEL_API_OUTPUT_USD_PER_MTOK"

DEFAULT_MODEL = "muse-spark"
DEFAULT_TIMEOUT = 60.0
MAX_RETRIES = 2  # retries after the first attempt (FND-006)
BACKOFF_BASE = 0.5  # seconds; doubles each retry

DEFAULT_AGENT_CAPABILITY = "spark"
DEFAULT_AGENT_TIMEOUT = 900.0
DEFAULT_AGENT_LEASE = 1800  # jobs.py LEASE_DEFAULT
DEFAULT_AGENT_POLL = 2.0

# Planning placeholders for cost estimates only — NOT pricing facts.
DEFAULT_RATE_IN_PER_MTOK = 3.0
DEFAULT_RATE_OUT_PER_MTOK = 15.0


class SparkError(Exception):
    """Base class for Spark client failures."""


class SparkNotConfigured(SparkError):
    """No transport is available; no call was attempted."""


class SparkHTTPError(SparkError):
    """The HTTP endpoint answered with a non-success status."""

    def __init__(self, status, body=""):
        self.status = status
        super().__init__(f"Spark endpoint returned HTTP {status}")
        self.body = body


class SparkBudgetError(SparkError):
    """A budget cap refused the call before it was sent."""


class SparkResponseError(SparkError):
    """A completion arrived but was unusable (bad body, bad digest)."""


class SparkAgentError(SparkError):
    """The agent transport failed: blocked, vanished, or abandoned."""


class SparkTimeoutError(SparkAgentError):
    """No completion arrived within the agent transport deadline."""


def _log(msg):
    print(f"spark_client: {msg}", file=sys.stderr)


def _env_float(name, default=None):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        raise SparkNotConfigured(f"{name} is not a number: {raw!r}")


def _env_int(name, default=None):
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        raise SparkNotConfigured(f"{name} is not an integer: {raw!r}")


def _estimate_tokens(text):
    """Rough token estimate (~4 chars/token) for pre-call costing."""
    if not text:
        return 0
    return max(1, math.ceil(len(text) / 4))


class _Outcome:
    """One served completion: text plus honest usage accounting."""

    __slots__ = ("text", "tokens_in", "tokens_out", "usage")

    def __init__(self, text, tokens_in, tokens_out, usage):
        self.text = text
        self.tokens_in = tokens_in
        self.tokens_out = tokens_out
        self.usage = usage  # "reported" | "estimated" | "unreported"


# --- HTTP transport -------------------------------------------------------

class HttpTransport:
    """Direct chat-completions POST to a Meta Model API endpoint."""

    name = "http"

    def __init__(self, endpoint="", api_key="", model=DEFAULT_MODEL,
                 timeout=DEFAULT_TIMEOUT, max_retries=MAX_RETRIES,
                 backoff_base=BACKOFF_BASE):
        self.endpoint = endpoint.strip()
        self.api_key = api_key.strip()
        self.model = model or DEFAULT_MODEL
        self.timeout = timeout
        self.max_retries = int(max_retries)
        self.backoff_base = float(backoff_base)

    def available(self):
        return bool(self.endpoint and self.api_key)

    def config_hint(self):
        return f"set {ENV_URL} and {ENV_KEY} (see GOV-001)"

    def _post_once(self, payload):
        """One HTTP attempt; returns the decoded JSON body.

        The key goes in the Authorization header and nowhere else.
        """
        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint, data=body, method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            })
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                raw = resp.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            detail = ""
            try:
                detail = e.read().decode("utf-8", "replace")[:200]
            except Exception:
                pass
            raise SparkHTTPError(e.code, detail) from e
        except urllib.error.URLError as e:
            raise SparkError(
                f"Spark endpoint unreachable: {e.reason}") from e
        try:
            return json.loads(raw)
        except ValueError as e:
            raise SparkResponseError(
                "Spark endpoint returned a non-JSON body") from e

    def _post_with_retries(self, payload):
        """FND-006: 429/5xx retried up to max_retries with backoff."""
        attempt = 0
        while True:
            try:
                return self._post_once(payload)
            except SparkHTTPError as e:
                retryable = e.status == 429 or 500 <= e.status < 600
                if not retryable or attempt >= self.max_retries:
                    raise
                delay = self.backoff_base * (2 ** attempt)
                _log(f"HTTP {e.status}; retry {attempt + 1}/"
                     f"{self.max_retries} in {delay:.1f}s")
                time.sleep(delay)
                attempt += 1

    @staticmethod
    def _extract_text(data):
        choices = data.get("choices") or []
        if choices:
            first = choices[0] or {}
            msg = first.get("message") or {}
            if isinstance(msg.get("content"), str):
                return msg["content"]
            if isinstance(first.get("text"), str):
                return first["text"]
        blocks = data.get("content") or []
        texts = [b.get("text") for b in blocks
                 if isinstance(b, dict) and b.get("type") == "text"]
        if texts:
            return "".join(t for t in texts if t)
        if isinstance(data.get("output_text"), str):
            return data["output_text"]
        raise SparkResponseError(
            "Spark response held no completion text "
            f"(keys: {sorted(data)[:8]})")

    def complete(self, prompt, system=None, max_tokens=1024,
                 lane_feature="unspecified"):
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": int(max_tokens),
        }
        data = self._post_with_retries(payload)
        text = self._extract_text(data)
        usage = data.get("usage") or {}
        tokens_in = usage.get("prompt_tokens", usage.get("input_tokens"))
        tokens_out = usage.get(
            "completion_tokens", usage.get("output_tokens"))
        if tokens_in is not None and tokens_out is not None:
            return _Outcome(text, int(tokens_in), int(tokens_out),
                            "reported")
        # The API answered without usage: estimate, and say so.
        full = (system or "") + "\n" + (prompt or "")
        return _Outcome(
            text,
            _estimate_tokens(full) if tokens_in is None
            else int(tokens_in),
            _estimate_tokens(text) if tokens_out is None
            else int(tokens_out),
            "estimated")


# --- Agent transport --------------------------------------------------------

class _Abandoned(Exception):
    """Internal: a claimed Spark job lost its lease (agent died)."""


class AgentTransport:
    """Dispatch completions to a resident crew agent via the job queue.

    The agent is a real Muse Spark process working the queue like
    any crew member: it claims the job atomically, generates, writes
    the result key, and marks the job done. This transport is the
    dispatcher side of that contract (see the module docstring).
    """

    name = "agent"

    def __init__(self, capability=DEFAULT_AGENT_CAPABILITY, room="",
                 timeout=DEFAULT_AGENT_TIMEOUT,
                 lease=DEFAULT_AGENT_LEASE, poll_interval=DEFAULT_AGENT_POLL,
                 now_fn=None, sleep_fn=None):
        self.capability = (capability or DEFAULT_AGENT_CAPABILITY)
        self.room = room or ""
        self.timeout = float(timeout)
        self.lease = int(lease)
        self.poll_interval = float(poll_interval)
        self._now = now_fn or time.time
        self._sleep = sleep_fn or time.sleep

    def available(self):
        # Dispatch rides the relay bus config (relay_common): without
        # it there is no queue to dispatch into.
        return bool(rc.RELAY_URL)

    def config_hint(self):
        return ("the agent transport rides the relay bus: set "
                "MUSE_RELAY_URL + token file (relay_common config)")

    # -- dispatch ---------------------------------------------------------

    def _dispatch(self, jobs, prompt, system, max_tokens, lane_feature):
        """Post the Spark job; returns its job id.

        Follows mos/overseer.dispatch: post via jobs.main, then DM
        every capable agent. jobs.py itself announces the job on its
        room, so a resident agent watching the room or the job index
        also sees it; the DM is a nudge, never the only channel.
        """
        spec = json.dumps({
            "kind": "spark-complete",
            "v": 1,
            "lane_feature": lane_feature,
            "system": system,
            "prompt": prompt,
            "max_tokens": int(max_tokens),
            "job_ns": jobs.NS,
            "result_key_pattern": "{job_ns}:{jid}:result",
        }, sort_keys=True)
        accept = (
            "Write the completion to <job_ns>:<jid>:result via api_post "
            "(JSON {\"text\": ..., \"tokens_in\": ..., "
            "\"tokens_out\": ...} or plain text), then finish with: "
            "jobs.py done <jid> --commit sha256:<sha256 of the exact "
            "result body>")
        title = f"SPARK:{lane_feature}"
        argv = ["post", "--title", title, "--spec", spec,
                "--accept", accept, "--lease", str(self.lease)]
        if self.room:
            argv += ["--room", self.room]
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            rc_code = jobs.main(argv)
        if rc_code != 0:
            raise SparkAgentError(
                f"spark job post failed: {buf.getvalue().strip()}")
        jid = None
        for line in buf.getvalue().splitlines():
            if line.startswith("JOB "):
                jid = line.split()[1]
        if jid is None:
            raise SparkAgentError(
                f"could not parse job id from: {buf.getvalue()!r}")
        self._dm_capable(jobs, jid, title)
        return jid

    def _dm_capable(self, jobs, jid, title):
        """Best-effort DM to capable agents (overseer pattern).

        Never fails the dispatch: the job is already on the queue and
        announced on its room; a failed DM only loses a nudge.
        """
        try:
            import send
            from mos import capabilities
            for nick in capabilities.find_for([self.capability]):
                rec = capabilities.get(nick) or {}
                secret = rec.get("dm", "")
                if not secret:
                    continue
                text = f"JOB:{jid} {title} req={self.capability}"
                buf, err = io.StringIO(), io.StringIO()
                with contextlib.redirect_stdout(buf), \
                        contextlib.redirect_stderr(err):
                    send.main(["--dm", secret, text])
        except Exception as e:
            _log(f"spark job {jid}: capable-agent DM failed ({e})")

    # -- waiting ------------------------------------------------------------

    def _await_result(self, jobs, jid):
        """Poll the job hash until done/blocked/abandoned/timeout."""
        deadline = self._now() + self.timeout
        saw_claimed = False
        while True:
            h, _ = jobs.job_get(jid)
            if h is None:
                raise SparkAgentError(f"spark job {jid} vanished")
            status = h.get("status")
            if status == "done":
                return self._read_result(jobs, jid, h)
            if status == "blocked":
                raise SparkAgentError(
                    f"spark agent blocked job {jid}: "
                    f"{h.get('note', '')}".strip())
            if status == "claimed":
                saw_claimed = True
                if self._mutex_gone(jobs, jid):
                    raise _Abandoned(jid)
            elif status == "open" and saw_claimed:
                raise _Abandoned(jid)
            if self._now() >= deadline:
                raise SparkTimeoutError(
                    f"no completion for spark job {jid} within "
                    f"{self.timeout:.0f}s (status {status}); the job "
                    f"stays on the queue")
            self._sleep(self.poll_interval)

    @staticmethod
    def _mutex_gone(jobs, jid):
        """True when the claim mutex expired (jobs.py's own test for a
        dead lease — see jobs._claim_or_requeue). A read failure is
        not evidence of death, so it counts as still-held."""
        try:
            cur = json.loads(
                rc.api_get(f"get/{jobs._claim_key(jid)}"))["result"]
        except Exception:
            return False
        return cur is None

    def _read_result(self, jobs, jid, h):
        key = f"{jobs.NS}:{jid}:result"
        try:
            raw = json.loads(rc.api_get(f"get/{key}"))["result"]
        except Exception as e:
            raise SparkResponseError(
                f"spark job {jid} is done but its result at {key} "
                f"could not be read ({e})") from e
        if raw is None:
            raise SparkResponseError(
                f"spark job {jid} is done but no result at {key}")
        commit = h.get("result_commit", "")
        if commit.startswith("sha256:"):
            digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()
            if digest != commit[len("sha256:"):]:
                raise SparkResponseError(
                    f"spark job {jid}: result digest mismatch "
                    f"(commit {commit}, actual sha256:{digest})")
        try:
            env = json.loads(raw)
        except ValueError:
            env = None
        if isinstance(env, dict) and isinstance(env.get("text"), str):
            tokens_in = env.get("tokens_in")
            tokens_out = env.get("tokens_out")
            if isinstance(tokens_in, int) and isinstance(tokens_out, int):
                return _Outcome(env["text"], tokens_in, tokens_out,
                                "reported")
            return _Outcome(env["text"], None, None, "unreported")
        return _Outcome(raw, None, None, "unreported")

    # -- the call -----------------------------------------------------------

    def complete(self, prompt, system=None, max_tokens=1024,
                 lane_feature="unspecified", max_retries=MAX_RETRIES):
        import jobs  # lazy: keep package import side-effect free
        attempts = 0
        while True:
            attempts += 1
            jid = self._dispatch(
                jobs, prompt, system, max_tokens, lane_feature)
            try:
                return self._await_result(jobs, jid)
            except _Abandoned:
                if attempts > max_retries:
                    raise SparkAgentError(
                        f"spark completion abandoned by the agent "
                        f"{attempts} time(s); last job {jid}")
                _log(f"spark job {jid} abandoned (lease lost); "
                     f"re-dispatching (attempt {attempts + 1})")


# --- Client -----------------------------------------------------------------

class SparkClient:
    """The Spark gateway: one complete() over the selected transport."""

    def __init__(self, transport=None, endpoint=None, api_key=None,
                 model=None, timeout=None, max_retries=MAX_RETRIES,
                 backoff_base=BACKOFF_BASE, max_spend_usd=None,
                 per_call_cap_usd=None, input_rate=None, output_rate=None,
                 agent_capability=None, agent_room=None,
                 agent_timeout=None, agent_lease=None,
                 agent_poll_interval=None, ledger=True):
        self.transport_name = (
            transport or os.environ.get(ENV_TRANSPORT, "")
            or AgentTransport.name).strip().lower()
        self.max_retries = int(max_retries)
        self.max_spend_usd = (
            max_spend_usd if max_spend_usd is not None
            else _env_float(ENV_MAX_SPEND))
        self.per_call_cap_usd = (
            per_call_cap_usd if per_call_cap_usd is not None
            else _env_float(ENV_PER_CALL))
        self.input_rate = (
            input_rate if input_rate is not None
            else _env_float(ENV_RATE_IN, DEFAULT_RATE_IN_PER_MTOK))
        self.output_rate = (
            output_rate if output_rate is not None
            else _env_float(ENV_RATE_OUT, DEFAULT_RATE_OUT_PER_MTOK))
        self.ledger = ledger
        self._spent_usd = 0.0
        if self.transport_name == HttpTransport.name:
            self._transport = HttpTransport(
                endpoint=(endpoint if endpoint is not None
                          else os.environ.get(ENV_URL, "")),
                api_key=(api_key if api_key is not None
                         else os.environ.get(ENV_KEY, "")),
                model=model or os.environ.get(ENV_MODEL, "")
                or DEFAULT_MODEL,
                timeout=(timeout if timeout is not None
                         else _env_float(ENV_TIMEOUT, DEFAULT_TIMEOUT)),
                max_retries=self.max_retries,
                backoff_base=backoff_base)
        elif self.transport_name == AgentTransport.name:
            self._transport = AgentTransport(
                capability=(agent_capability
                            or os.environ.get(ENV_AGENT_CAPABILITY, "")
                            or DEFAULT_AGENT_CAPABILITY),
                room=(agent_room if agent_room is not None
                      else os.environ.get(ENV_AGENT_ROOM, "")),
                timeout=(agent_timeout if agent_timeout is not None
                         else _env_float(ENV_AGENT_TIMEOUT,
                                         DEFAULT_AGENT_TIMEOUT)),
                lease=(agent_lease if agent_lease is not None
                       else _env_int(ENV_AGENT_LEASE,
                                    DEFAULT_AGENT_LEASE)),
                poll_interval=(
                    agent_poll_interval if agent_poll_interval is not None
                    else _env_float(ENV_AGENT_POLL, DEFAULT_AGENT_POLL)))
        else:
            self._transport = None

    @property
    def configured(self):
        return self._transport is not None and self._transport.available()

    @property
    def spent_usd(self):
        """Estimated API spend accumulated through this client."""
        return self._spent_usd

    def _est_cost(self, tokens_in, tokens_out):
        return round(
            tokens_in * self.input_rate / 1_000_000
            + tokens_out * self.output_rate / 1_000_000, 6)

    def _check_budget(self, prompt, system, max_tokens, lane_feature):
        """Budget caps gate API spend (the HTTP transport)."""
        worst_case = self._est_cost(
            _estimate_tokens((system or "") + "\n" + (prompt or "")),
            int(max_tokens))
        if (self.per_call_cap_usd is not None
                and worst_case > self.per_call_cap_usd):
            _log(f"budget: per-call cap ${self.per_call_cap_usd:.4f} "
                 f"refused call estimated at ${worst_case:.4f} "
                 f"({lane_feature})")
            raise SparkBudgetError(
                f"per-call budget cap ${self.per_call_cap_usd} would be "
                f"exceeded (worst case ${worst_case})")
        if (self.max_spend_usd is not None
                and self._spent_usd >= self.max_spend_usd):
            _log(f"budget: session cap ${self.max_spend_usd:.4f} reached "
                 f"(spent ${self._spent_usd:.4f}); call refused "
                 f"({lane_feature})")
            raise SparkBudgetError(
                f"session budget cap ${self.max_spend_usd} reached "
                f"(spent ${self._spent_usd})")

    def complete(self, prompt, system=None, max_tokens=1024,
                 lane_feature="unspecified"):
        """Run one completion; returns the completion text.

        Raises SparkNotConfigured (no transport available),
        SparkBudgetError (a cap refused an HTTP call; nothing sent),
        SparkHTTPError / SparkResponseError / SparkError (HTTP path),
        SparkAgentError / SparkTimeoutError (agent path).
        """
        if self._transport is None:
            raise SparkNotConfigured(
                f"{ENV_TRANSPORT}={self.transport_name!r} is not a "
                f"transport: use 'agent' or 'http'")
        if not self._transport.available():
            raise SparkNotConfigured(
                f"Spark transport '{self.transport_name}' not "
                f"configured: {self._transport.config_hint()}")
        if isinstance(self._transport, HttpTransport):
            self._check_budget(prompt, system, max_tokens, lane_feature)
            outcome = self._transport.complete(
                prompt, system=system, max_tokens=max_tokens,
                lane_feature=lane_feature)
        else:
            outcome = self._transport.complete(
                prompt, system=system, max_tokens=max_tokens,
                lane_feature=lane_feature, max_retries=self.max_retries)

        est_cost = None
        if outcome.tokens_in is not None and outcome.tokens_out is not None:
            est_cost = self._est_cost(outcome.tokens_in, outcome.tokens_out)
            self._spent_usd += est_cost
        if self.ledger:
            entry = {
                "ts": int(time.time()),
                "lane_feature": lane_feature,
                "tokens_in": outcome.tokens_in,
                "tokens_out": outcome.tokens_out,
                "est_cost": est_cost,
                "usage": outcome.usage,
            }
            try:
                _store.record_spend(entry)
            except Exception as e:  # ledger is observability; the call
                _log(f"spend ledger write failed: {e}")  # already happened
        return outcome.text


_default_client = None


def default_client():
    """The process-wide client, built from env on first use."""
    global _default_client
    if _default_client is None:
        _default_client = SparkClient()
    return _default_client


def complete(prompt, system=None, max_tokens=1024,
             lane_feature="unspecified"):
    """Module-level convenience: complete() on the default client."""
    return default_client().complete(
        prompt, system=system, max_tokens=max_tokens,
        lane_feature=lane_feature)
