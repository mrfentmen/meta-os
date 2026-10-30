"""intel/spark_agent.py — the resident-agent side of the Spark contract.

This is the other half of intel/spark_client.py's AgentTransport (see
that module's docstring for the full contract). spark_client
dispatches a completion as a job through the queue; THIS module is
the agent that works it:

  * registers the SPARK_AGENT_CAPABILITY (default "spark") through
    mos.capabilities.register — the same registry and pattern every
    crew agent uses — and heartbeats the registration each cycle, so
    the dispatcher's capability DMs (overseer pattern) find it fresh;
  * scans the job index for open jobs whose spec is a spark-complete
    envelope ({"kind": "spark-complete", "v": 1, ...}) — the queue is
    the source of truth, so a completion is served whether the agent
    saw the room announcement, the capability DM, or neither;
  * claims the job atomically through jobs.py (first claim wins,
    lease held), and heartbeats the lease while it generates;
  * writes the completion to the result key from the envelope's
    result_key_pattern ("{job_ns}:{jid}:result") with api_post — the
    same body channel jobs.py uses for specs — as a JSON envelope
    {"text": ..., "tokens_in": ..., "tokens_out": ...} (token fields
    only when the generation actually reported them; counts are never
    fabricated), then finishes with
        jobs.py done <jid> --commit sha256:<sha256 of the result body>
    so the dispatcher can verify the digest;
  * marks the job blocked with a reason when generation is refused
    or fails, so the dispatcher raises with that reason instead of
    waiting out a timeout. A claim whose agent dies mid-generation
    is abandoned by lease expiry and re-dispatched by the CLIENT as
    a fresh job (spark_client owns re-dispatch); this handler then
    serves the fresh job like any other.

Generation is caller-supplied. The interface is:

    generate(prompt, system=None, max_tokens=1024)
        -> {"text": str,
            "tokens_in": int | None,
            "tokens_out": int | None}
    (a plain str return is accepted and recorded as unreported usage)

The real generation is a resident Muse Spark crew agent: its
process constructs SparkAgent with its own model callable bound as
`generate`. No generation implementation exists in this repo, and
none is faked here (Del's ruling, 2026-10-26: no mock or fake code
in the build): with no callable bound, `generate` is
unconfigured_generate, which raises GenerationNotConfigured. In the
serve loop that becomes a blocked job whose reason says exactly
that — the honest state of the system, never a silent substitute.

Live verification: NOT YET VERIFIED against the live bus. The unit
tests exercise the full dispatch -> claim -> generate -> result ->
done cycle with this handler against the real jobs machinery on the
test Redis fake; no resident Spark agent process is standing by on
the live queue yet.
"""
import contextlib
import hashlib
import io
import json
import os
import sys
import threading
import time

import relay_common as rc

import jobs

from mos import capabilities

from .spark_client import DEFAULT_AGENT_CAPABILITY, ENV_AGENT_CAPABILITY

SPEC_KIND = "spark-complete"
SPEC_VERSION = 1
DEFAULT_POLL_INTERVAL = 5.0


class GenerationNotConfigured(Exception):
    """No generation function is bound; no completion was produced."""


def unconfigured_generate(prompt, system=None, max_tokens=1024):
    """The default `generate`: fail loudly, produce nothing."""
    raise GenerationNotConfigured(
        "spark generation not configured: this agent has no "
        "generation function bound; a resident Muse Spark agent "
        "process must supply generate(prompt) — no completion "
        "was produced")


def parse_spark_spec(spec):
    """Return the envelope dict of a spark-complete spec, else None."""
    try:
        env = json.loads(spec or "")
    except ValueError:
        return None
    if not isinstance(env, dict):
        return None
    if env.get("kind") != SPEC_KIND or env.get("v") != SPEC_VERSION:
        return None
    if not isinstance(env.get("prompt"), str):
        return None
    return env


def result_key_for(env, jid):
    """The result key the dispatcher reads, from the envelope itself."""
    pattern = env.get("result_key_pattern") or "{job_ns}:{jid}:result"
    job_ns = env.get("job_ns") or jobs.NS
    try:
        return pattern.format(job_ns=job_ns, jid=jid)
    except (KeyError, IndexError, ValueError):
        return f"{job_ns}:{jid}:result"


def result_body_for(generation):
    """Normalize a generation result into the exact result body.

    A dict with both token counts reported becomes the JSON envelope
    {"text", "tokens_in", "tokens_out"}; a dict without counts (or a
    plain string) is served so the client records the completion as
    unreported usage. Raises ValueError on an unusable result.
    """
    if isinstance(generation, str):
        return generation
    if not isinstance(generation, dict):
        raise ValueError(
            f"generation returned {type(generation).__name__}, "
            f"expected a dict or str")
    text = generation.get("text")
    if not isinstance(text, str):
        raise ValueError("generation returned no completion text")
    tokens_in = generation.get("tokens_in")
    tokens_out = generation.get("tokens_out")
    if isinstance(tokens_in, int) and isinstance(tokens_out, int):
        return json.dumps(
            {"text": text, "tokens_in": tokens_in,
             "tokens_out": tokens_out}, sort_keys=True)
    return json.dumps({"text": text}, sort_keys=True)


def _log(msg):
    print(f"spark_agent: {msg}", file=sys.stderr)


class SparkAgent:
    """A resident agent that serves spark-complete jobs off the queue.

    One agent is one nick in one process (the repo convention): the
    nick comes from MUSE_RELAY_NICK via relay_common unless given.
    """

    def __init__(self, generate=None, nick=None, capability=None,
                 dm_secret="", lease=None, poll_interval=None,
                 roles="spark-agent"):
        self.generate = generate or unconfigured_generate
        self.generation_configured = generate is not None
        self.nick = nick or rc.NICK
        self.capability = (
            capability or os.environ.get(ENV_AGENT_CAPABILITY, "")
            or DEFAULT_AGENT_CAPABILITY)
        self.dm_secret = dm_secret
        self.lease = int(lease) if lease else jobs.LEASE_DEFAULT
        self.poll_interval = (
            DEFAULT_POLL_INTERVAL if poll_interval is None
            else float(poll_interval))
        self.roles = roles
        # Claiming/finishing through jobs.py checks the claimer nick
        # against jobs.NICK; take over the module nicks like
        # mos.worker.Worker does.
        if self.nick != rc.NICK:
            rc.NICK = self.nick
            jobs.NICK = self.nick

    # -- registration ---------------------------------------------------

    def register(self):
        """Register (or refresh) the spark capability; returns True."""
        capabilities.register(
            self.nick, [self.capability], roles=self.roles,
            max_jobs=1, dm_secret=self.dm_secret)
        return True

    def heartbeat(self):
        """Touch the capability registration; False if unknown."""
        try:
            return capabilities.touch(self.nick)
        except Exception:
            return False

    # -- queue plumbing (jobs.py CLI semantics, output captured) --------

    @staticmethod
    def _jobs_main(argv):
        buf, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(buf), \
                contextlib.redirect_stderr(err):
            code = jobs.main(argv)
        return code, (buf.getvalue() + err.getvalue()).strip()

    def _block(self, jid, reason):
        code, _ = self._jobs_main(
            ["blocked", jid, "--reason", str(reason)[:500]])
        return code == 0

    # -- finding work -----------------------------------------------------

    def open_spark_jobs(self):
        """[(jid, envelope)] for open spark-complete jobs, post order."""
        try:
            raw = rc.api_get(f"zrange/{jobs._index_key()}/0/-1")
            ids = json.loads(raw)["result"] or []
        except Exception:
            return []
        out = []
        for jid in ids:
            h, spec = jobs.job_get(jid)
            if not h or h.get("status") != "open":
                continue
            env = parse_spark_spec(spec)
            if env is not None:
                out.append((jid, env))
        return out

    # -- serving ----------------------------------------------------------

    def _heartbeat_loop(self, jid, lease, stop):
        """Renew the claim lease until `stop` is set or the lease is lost."""
        interval = max(5.0, min(60.0, lease / 3))
        while not stop.wait(interval):
            code, _ = self._jobs_main(["heartbeat", jid])
            if code != 0:
                return

    def serve_job(self, jid, env=None):
        """Claim and serve one spark job.

        Returns "done", "blocked", "skipped" (not an open spark job),
        or "lost" (claim race lost, or the finish could not land).
        """
        jobs.NICK = self.nick
        h, spec = jobs.job_get(jid)
        if h is None or h.get("status") != "open":
            return "skipped"
        if env is None:
            env = parse_spark_spec(spec)
        if env is None:
            return "skipped"
        try:
            lease = int(h.get("lease") or self.lease)
        except (TypeError, ValueError):
            lease = self.lease
        code, out = self._jobs_main(["claim", jid, "--lease", str(lease)])
        if code != 0:
            _log(f"claim {jid} failed: {out[-200:]}")
            return "lost"
        stop = threading.Event()
        hb = threading.Thread(
            target=self._heartbeat_loop, args=(jid, lease, stop),
            daemon=True)
        hb.start()
        try:
            generation = self.generate(
                env["prompt"], system=env.get("system"),
                max_tokens=int(env.get("max_tokens") or 1024))
            body = result_body_for(generation)
        except GenerationNotConfigured as e:
            self._block(jid, str(e))
            return "blocked"
        except Exception as e:
            self._block(jid, f"spark generation failed: {e}")
            return "blocked"
        finally:
            stop.set()
            hb.join(timeout=2)
        try:
            key = result_key_for(env, jid)
            rc.api_post(f"set/{key}", body)
            digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
            code, out = self._jobs_main(
                ["done", jid, "--commit", f"sha256:{digest}",
                 "--note", f"spark completion by {self.nick}"])
        except Exception as e:
            # The completion exists but could not be delivered: say so
            # on the job instead of leaving the dispatcher to time out.
            if self._block(jid, f"spark result delivery failed: {e}"):
                return "blocked"
            return "lost"
        if code != 0:
            _log(f"done {jid} failed: {out[-200:]}")
            return "lost"
        return "done"

    def serve_once(self):
        """One register/heartbeat/serve cycle. Returns a report dict."""
        report = {"done": [], "blocked": [], "skipped": [],
                  "errors": []}
        self.register()
        self.heartbeat()
        for jid, env in self.open_spark_jobs():
            try:
                outcome = self.serve_job(jid, env)
            except Exception as e:
                report["errors"].append(f"serve {jid}: {e}")
                continue
            if outcome in ("done", "blocked"):
                report[outcome].append(jid)
            elif outcome == "skipped":
                report["skipped"].append(jid)
            else:
                report["errors"].append(f"serve {jid}: {outcome}")
        return report

    def run_loop(self, interval=None):
        """Serve forever until interrupted (the resident process)."""
        interval = self.poll_interval if interval is None else interval
        try:
            while True:
                try:
                    self.serve_once()
                except Exception as e:
                    _log(f"serve cycle failed: {e}")
                time.sleep(interval)
        except KeyboardInterrupt:
            _log("stopping")
