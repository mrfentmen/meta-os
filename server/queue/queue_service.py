#!/usr/bin/env python3
"""queue_service.py — the Trio queue service (OS queue, service end).

The HTTP counterpart of server/queue.mjs's adapters: the Trio server
POSTs the envelope buildQueueJob() produces to /jobs here and polls
GET /jobs/<id>/result for the envelope the resident agent writes to
trio:{jid}:result (Pax's bus-424 ruling; job_id/status shape, NOT the
jobId/done variant queue.mjs's fetchQueueResult proposed — the
service's stored shape won that reconciliation on the 2026-10-30 live
proof, and queue.mjs normalizes client-side).

  POST /jobs               body: one trio-assessment v1 envelope (the
                           exact object buildQueueJob returns). The
                           frame's byteLength and SHA-256 are verified
                           against the decoded dataUrl before filing;
                           a mismatch is a 400, never a filed job.
                           Idempotent on the deterministic job id.
                           -> 201 (or 200 if already filed) {"jobId": id}
  GET /jobs/<id>/result    -> 200 with the stored result envelope
                           {job_id, status: ok|failed, assessment|null,
                            error, model, latency_ms, completed_at}
                           or 404 {"status": "pending", "job_id": id}
                           while the job is filed but unanswered, or
                           404 {"status": "unknown", ...} for no such job.
  GET /health              -> {"ok": true, "store": ..., ...}; when the
                           store is the local SQLite FALLBACK that fact
                           is stated in the response, not hidden.
  POST /dispatch-simulated the agent crew's SIMULATED dispatch endpoint
                           (docs/AGENT_CREW.md): accepts only packages
                           labelled "simulated": true, logs them to the
                           crew dispatch log, returns a receipt. It
                           contacts nothing outside this stack.

Storage: the OS jobs store semantics in trio_store.py (Upstash Redis
via the credential surrogate; namespace from TRIO_JOB_NS, default
"trio").

Run: python3 queue_service.py [--port 8935]
Stdlib only.
"""
import argparse
import base64
import hashlib
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_records  # noqa: E402
import trio_repo  # noqa: E402
import trio_store  # noqa: E402

PRODUCTS = trio_repo.product_ids()  # js/products.js is the source
LOCAL_DB = os.environ.get(
    "TRIO_LOCAL_DB",
    os.path.join(os.path.dirname(os.path.abspath(__file__)),
                 "trio-queue-local.db"))

STORE, FELL_BACK = trio_store.open_store(LOCAL_DB)
JOBS = trio_store.JobStore(STORE)


def validate_envelope(env):
    """Return an error string, or None when the envelope is fileable."""
    if not isinstance(env, dict):
        return "envelope is not a JSON object"
    if env.get("version") != 1 or env.get("kind") != "trio-assessment":
        return "not a trio-assessment v1 envelope"
    if not isinstance(env.get("id"), str) or not env["id"]:
        return "envelope has no job id"
    if env.get("product") not in PRODUCTS:
        return f"unknown product {env.get('product')!r}"
    if not isinstance(env.get("timestamp"), str) or not env["timestamp"]:
        return "envelope has no timestamp"
    image = env.get("image")
    if not isinstance(image, dict):
        return "envelope has no image object"
    data_url = image.get("dataUrl")
    if not isinstance(data_url, str) or \
            not data_url.startswith("data:image/jpeg;base64,"):
        return "image.dataUrl is not a JPEG data URL"
    try:
        raw = base64.b64decode(data_url.split(",", 1)[1], validate=True)
    except Exception:
        return "image.dataUrl does not base64-decode"
    if image.get("byteLength") != len(raw):
        return "image.byteLength does not match the decoded frame"
    if image.get("sha256") != hashlib.sha256(raw).hexdigest():
        return "image.sha256 does not match the decoded frame"
    return None


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt, *args):  # keep stdout clean; log to stderr
        print(f"queue_service: {fmt % args}", file=sys.stderr)

    def _send(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send(200, {
                "ok": True,
                "service": "trio-queue",
                "store": STORE.name,
                "store_fallback": FELL_BACK,
                "namespace": trio_store.NS,
                "result_prefix": trio_store.RESULT_PREFIX,
            })
            return
        prefix = "/jobs/"
        if self.path.startswith(prefix) and self.path.endswith("/result"):
            jid = self.path[len(prefix):-len("/result")]
            result = JOBS.get_result(jid)
            if result is not None:
                self._send(200, result)
            elif JOBS.job_fields(jid):
                self._send(404, {"status": "pending", "job_id": jid})
            else:
                self._send(404, {"status": "unknown", "job_id": jid,
                                 "error": "no such job in the store"})
            return
        self._send(404, {"error": "not found"})

    def _dispatch_simulated(self):
        """POST /dispatch-simulated — the agent crew's SIMULATED
        dispatch endpoint (docs/AGENT_CREW.md). It accepts ONLY a
        package that labels itself simulated, appends it to the
        crew's dispatch log (crew_records), and returns a receipt.
        It contacts nothing: no real emergency service, no external
        system — the route exists so the response pipeline can be
        exercised end to end inside this stack, and its name, its
        log, and its receipt all say SIMULATED."""
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            package = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send(400, {"error": "request body is not JSON"})
            return
        if not isinstance(package, dict) or \
                package.get("simulated") is not True:
            self._send(400, {
                "error": "refused: this endpoint accepts only "
                         "packages labelled \"simulated\": true"})
            return
        from datetime import datetime, timezone
        received_at = datetime.now(timezone.utc).isoformat(
            timespec="milliseconds").replace("+00:00", "Z")
        receipt_id = "sim-" + hashlib.sha256(
            json.dumps(package, sort_keys=True).encode()
        ).hexdigest()[:16]
        record = dict(package)
        record["receipt_id"] = receipt_id
        record["received_at"] = received_at
        crew_records.CrewRecords().append_dispatch(record)
        self._send(201, {
            "receipt_id": receipt_id,
            "simulated": True,
            "received_at": received_at,
            "note": "SIMULATED dispatch endpoint — the package was "
                    "logged inside this stack; no real emergency "
                    "service or external system was contacted.",
        })

    def do_POST(self):
        if self.path == "/dispatch-simulated":
            self._dispatch_simulated()
            return
        if self.path != "/jobs":
            self._send(404, {"error": "not found"})
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        raw = self.rfile.read(length) if length > 0 else b""
        try:
            env = json.loads(raw.decode("utf-8"))
        except Exception:
            self._send(400, {"error": "request body is not JSON"})
            return
        err = validate_envelope(env)
        if err:
            self._send(400, {"error": f"refused job: {err}"})
            return
        jid, created = JOBS.submit(env)
        self._send(201 if created else 200, {"jobId": jid})


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8935)
    args = ap.parse_args()
    print(f"queue_service: store={STORE.name} fallback={FELL_BACK} "
          f"namespace={trio_store.NS}", file=sys.stderr)
    if FELL_BACK:
        print("queue_service: WARNING — local SQLite FALLBACK store; "
              "jobs live in a file on this machine only",
              file=sys.stderr)
    ThreadingHTTPServer(("127.0.0.1", args.port), Handler).serve_forever()


if __name__ == "__main__":
    main()
