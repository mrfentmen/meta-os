#!/usr/bin/env python3
"""hosted_imperium.py — the hosted Imperium queue-stack pass (R12-008).

One pass, three real stages, one receipt:

  1. the real queue service (`queue_service.py`) starts on loopback with the labelled SQLite
     fallback (no Upstash credential is read);
  2. the real resident agent (`trio_agent.py --once`) runs against that same store — zero jobs,
     because this pass files none, and it says so rather than inventing an assessment;
  3. a package labelled `simulated: true` is POSTed to the service's real
     `/dispatch-simulated` route, which appends it to the crew dispatch log and returns a
     receipt.

No model call is made and no assessment is claimed: the direct Spark transport has no key on
this host. What this proves is the stack's wiring and the loopback dispatch boundary — the one
thing the task says must be proven or the run does not count.

Run: python3 server/queue/hosted_imperium.py
Exit 0 only when all three stages answered.
"""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(ROOT, "os-build", "layer1", "r12", "IMPERIUM_RECEIPT.json")
TMP = tempfile.mkdtemp(prefix="imperium-hosted-")

ENV = dict(os.environ)
ENV.update({
    "TRIO_STORE": "local",
    "TRIO_LOCAL_DB": os.path.join(TMP, "queue.db"),
    "TRIO_JOB_NS": "hosted-r12",
    "TRIO_CREW_DATA_DIR": os.path.join(TMP, "crew-data"),
    # No key, no helper: a model call must fail rather than reach a provider silently.
    "SPARK_API_KEY": "",
    "TRIO_SPARK_VIA_HELPER": "",
})


def now():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def free_port():
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


def request(port, path, method="GET", body=None, timeout=10):
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:%d%s" % (port, path), data=data, method=method,
        headers={"Content-Type": "application/json", "User-Agent": "meta-imperium-hosted/1"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as res:
        return res.status, json.loads(res.read().decode() or "{}")


def main():
    port = free_port()
    started = now()
    stages = {"queue_service": {"state": "starting", "port": port},
              "agent_once": {"state": "not-run"},
              "dispatch": {"state": "not-run"}}

    service = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "queue_service.py"), "--port", str(port)],
        cwd=HERE, env=ENV, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        healthy = False
        for _ in range(100):
            if service.poll() is not None:
                break
            try:
                status, doc = request(port, "/health", timeout=1)
                if status == 200:
                    healthy = doc.get("ok") is True
                    stages["queue_service"].update({"state": "up", "health": doc})
                    break
            except Exception:
                time.sleep(0.1)
        if not healthy:
            err = ""
            try:
                service.terminate()
                err = (service.stderr.read() or "")[-400:]
            except Exception:
                pass
            stages["queue_service"].update({"state": "failed", "error": err})
            return finish(False, stages, started)

        agent = subprocess.run(
            [sys.executable, os.path.join(HERE, "trio_agent.py"), "--once"],
            cwd=HERE, env=ENV, capture_output=True, text=True, timeout=90,
        )
        report = None
        if agent.stdout.strip():
            try:
                report = json.loads(agent.stdout.strip().splitlines()[-1])
            except Exception:
                report = {"unparsed_stdout": agent.stdout.strip()[-300:]}
        stages["agent_once"] = {
            "state": "ran" if agent.returncode == 0 else "failed",
            "exit": agent.returncode,
            "report": report,
            "stderr": (agent.stderr or "").strip()[-400:],
            "note": "zero jobs filed by this pass; no assessment and no model call is claimed",
        }

        package = {
            "simulated": True,
            "kind": "imperium-dispatch-package",
            "incident_id": "hosted-r12-drill",
            "created_at": now(),
            "destination": "SIMULATED dispatch endpoint (local stack route) — no real "
                           "emergency service is contacted by this system",
            "crew": "hosted-r12-one-pass",
            "note": "drill package: proves the loopback route and receipt; carries no assessment",
        }
        status, receipt = request(port, "/dispatch-simulated", method="POST", body=package)
        stages["dispatch"] = {
            "state": "accepted" if status == 201 and receipt.get("simulated") is True else "failed",
            "http_status": status,
            "receipt": receipt,
            "route": "http://127.0.0.1:%d/dispatch-simulated" % port,
        }
    finally:
        service.terminate()
        try:
            service.wait(timeout=5)
        except Exception:
            service.kill()

    ok = (stages["queue_service"]["state"] == "up"
          and stages["agent_once"]["state"] == "ran"
          and stages["dispatch"]["state"] == "accepted")
    return finish(ok, stages, started)


def finish(ok, stages, started):
    receipt = {
        "at": now(), "started": started, "ok": ok, "stages": stages,
        "claims": {
            "proven": "queue service answered; resident agent one-pass exited 0; "
                      "/dispatch-simulated accepted a simulated package on loopback and returned a receipt",
            "not_proven": "no assessment, no model call, no patrol cycle; no real emergency service was contacted",
        },
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as f:
        json.dump(receipt, f, indent=2)
        f.write("\n")
    print("imperium hosted: " + ("PASS" if ok else "FAIL") + " -> " + OUT)
    for name, stage in stages.items():
        print("  " + name + ": " + stage.get("state", "?"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
