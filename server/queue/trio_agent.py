#!/usr/bin/env python3
"""trio_agent.py — the resident agent for trio-assessment jobs.

This process stands on the OS jobs store (trio_store.py, same
semantics as meta-os jobs.py), claims trio-assessment v1 jobs, and
answers each with a REAL Muse Spark assessment produced by
spark_gen.py — the pluggable generation transport (direct
SPARK_API_KEY path in production; the connector-helper DEV path when
TRIO_SPARK_VIA_HELPER=1). Nothing here invents an assessment:

  * poll the namespace index for open jobs;
  * IDEMPOTENCY FIRST: if trio:{jid}:result already exists, the job is
    finished as done and generation is SKIPPED — a resubmitted frame
    is never re-billed (checked before claiming and again after);
  * claim atomically (SET NX claim mutex + lease, renewed by a
    heartbeat thread while generating, exactly like jobs.py);
  * decode the frame from the envelope's dataUrl, verify its SHA-256
    against the envelope, and hand the JPEG to spark_gen.generate for
    the job's product and timestamp;
  * validate the model's output with the repo's own
    validateAssessment (node, ../../js/schema.js) — an invalid
    assessment is NEVER written as a result;
  * write the ruled result envelope to trio:{jid}:result:
        {job_id, status: "ok"|"failed", assessment|null, error,
         model, latency_ms, completed_at}
    where latency_ms is the model call latency the transport measured
    (null when no call completed) and model is the model the API
    reported. A failed generation or a failed validation lands as
    status "failed" with the reason in `error`.

Run: python3 trio_agent.py [--once] [--lease 300]
     [--nick trio-agent] [--schema <path to js/schema.js>]
Stdlib only.
"""
import argparse
import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import threading
import time
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spark_gen  # noqa: E402
import trio_repo  # noqa: E402
import trio_store  # noqa: E402

LOCAL_DB = os.environ.get(
    "TRIO_LOCAL_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "trio-queue-local.db"))
DEFAULT_SCHEMA = trio_repo.SCHEMA_PATH


def _log(msg):
    print(f"trio_agent: {msg}", file=sys.stderr)


def _now_iso():
    return datetime.now(timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


class Agent:
    def __init__(self, nick, lease, schema_path, jobs=None):
        self.nick = nick
        self.lease = int(lease)
        self.schema_path = schema_path
        if jobs is not None:
            self.jobs = jobs  # injected (tests)
            _log(f"store=injected namespace={trio_store.NS}")
            return
        store, fell_back = trio_store.open_store(LOCAL_DB)
        self.store = store
        self.jobs = trio_store.JobStore(store)
        if fell_back:
            _log("WARNING — local SQLite FALLBACK store; jobs live in "
                 "a file on this machine only")
        _log(f"store={store.name} namespace={trio_store.NS}")

    # -- validation via the repo's own contract validator ----------------

    def validate(self, assessment, product):
        """(ok, errors) from js/schema.js validateAssessment."""
        with tempfile.TemporaryDirectory() as td:
            data_path = os.path.join(td, "assessment.json")
            with open(data_path, "w") as f:
                json.dump(assessment, f)
            script = os.path.join(td, "validate.mjs")
            with open(script, "w") as f:
                f.write(
                    'import { readFileSync } from "node:fs";\n'
                    f'import {{ validateAssessment }} from '
                    f'"file://{self.schema_path}";\n'
                    "const value = JSON.parse("
                    "readFileSync(process.argv[2], 'utf8'));\n"
                    "const r = validateAssessment(value, process.argv[3]);\n"
                    "console.log(JSON.stringify(r.ok"
                    " ? { ok: true }"
                    " : { ok: false, errors: r.errors }));\n")
            p = subprocess.run(
                ["node", script, data_path, product],
                capture_output=True, text=True, timeout=60)
        if p.returncode != 0 and not p.stdout.strip():
            raise RuntimeError(
                f"validator invocation failed: {p.stderr.strip()[:300]}")
        out = json.loads(p.stdout.strip().splitlines()[-1])
        return bool(out.get("ok")), out.get("errors") or []

    # -- generation via the pluggable Spark transport --------------------

    def generate(self, product, image_path, timestamp):
        """(assessment_dict, model, latency_ms) from spark_gen.
        Raises on any failure; the caller turns that into a failed
        result envelope — never a written answer."""
        return spark_gen.generate(product, image_path, timestamp)

    # -- serving -----------------------------------------------------------

    def _finish_failed(self, jid, error, model=None, latency_ms=None):
        result = {
            "job_id": jid, "status": "failed", "assessment": None,
            "error": str(error)[:500], "model": model,
            "latency_ms": latency_ms, "completed_at": _now_iso(),
        }
        self.jobs.put_result(result)
        self.jobs.finish(jid, "failed", note=str(error)[:200])
        return "failed"

    def serve_job(self, jid):
        """Claim and serve one job. Returns an outcome string."""
        # Idempotency, before any claim or call: an existing result
        # means this deterministic job was already answered.
        if self.jobs.get_result(jid) is not None:
            self.jobs.finish(jid, "done", note="idempotent skip: "
                             "result already present, not re-billed")
            _log(f"{jid}: result already present — skipped, not re-billed")
            return "skipped"
        if not self.jobs.claim(jid, self.nick, self.lease):
            _log(f"{jid}: claim race lost")
            return "lost"
        stop = threading.Event()

        def heartbeat():
            interval = max(5.0, min(60.0, self.lease / 3))
            while not stop.wait(interval):
                if not self.jobs.renew_claim(jid, self.nick, self.lease):
                    return

        hb = threading.Thread(target=heartbeat, daemon=True)
        hb.start()
        try:
            # Idempotency again after the claim (the spark_agent rule:
            # the queue is the source of truth, re-check under lease).
            if self.jobs.get_result(jid) is not None:
                self.jobs.finish(jid, "done", note="idempotent skip: "
                                 "result already present, not re-billed")
                _log(f"{jid}: result appeared under claim — skipped")
                return "skipped"
            env = self.jobs.job_envelope(jid)
            if env is None:
                return self._finish_failed(jid, "job envelope missing "
                                           "or unparseable in the store")
            product = env.get("product")
            timestamp = env.get("timestamp")
            data_url = (env.get("image") or {}).get("dataUrl") or ""
            if not data_url.startswith("data:image/jpeg;base64,"):
                return self._finish_failed(jid, "envelope image is not "
                                           "a JPEG data URL")
            raw = base64.b64decode(data_url.split(",", 1)[1])
            digest = hashlib.sha256(raw).hexdigest()
            if (env.get("image") or {}).get("sha256") != digest:
                return self._finish_failed(jid, "frame sha256 mismatch "
                                           "against the envelope")
            with tempfile.NamedTemporaryFile(
                    suffix=".jpg", delete=False) as tf:
                tf.write(raw)
                image_path = tf.name
            try:
                assessment, model, latency_ms = self.generate(
                    product, image_path, timestamp)
            finally:
                os.unlink(image_path)
            ok, errors = self.validate(assessment, product)
            if not ok:
                return self._finish_failed(
                    jid, "model output failed validateAssessment: "
                    + "; ".join(errors[:5]),
                    model=model, latency_ms=latency_ms)
            result = {
                "job_id": jid, "status": "ok", "assessment": assessment,
                "error": None, "model": model, "latency_ms": latency_ms,
                "completed_at": _now_iso(),
            }
            self.jobs.put_result(result)
            self.jobs.finish(jid, "done",
                             note=f"assessment by {self.nick}")
            _log(f"{jid}: done — "
                 f"{assessment.get('assessment', {}).get('category')}")
            return "done"
        except Exception as e:
            try:
                return self._finish_failed(jid, f"generation failed: {e}")
            except Exception:
                return "lost"
        finally:
            stop.set()
            hb.join(timeout=2)

    def serve_once(self):
        report = {"done": [], "failed": [], "skipped": [], "lost": []}
        for jid in self.jobs.open_job_ids():
            try:
                outcome = self.serve_job(jid)
            except Exception as e:
                _log(f"serve {jid} raised: {e}")
                outcome = "lost"
            report[outcome if outcome in report else "lost"].append(jid)
        return report


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="one poll/serve pass, then exit")
    ap.add_argument("--lease", type=int, default=300)
    ap.add_argument("--nick", default="trio-agent")
    ap.add_argument("--schema", default=DEFAULT_SCHEMA)
    ap.add_argument("--poll-interval", type=float, default=5.0)
    args = ap.parse_args()
    agent = Agent(args.nick, args.lease, args.schema)
    if args.once:
        print(json.dumps(agent.serve_once()))
        return 0
    try:
        while True:
            agent.serve_once()
            time.sleep(args.poll_interval)
    except KeyboardInterrupt:
        _log("stopping")
    return 0


if __name__ == "__main__":
    sys.exit(main())
