#!/usr/bin/env python3
"""meta-agent-health — one scheduled look at the OC2 agent layer.

The units are enabled at build time without a daemon, so an installed image
has no regular check that the layer is still whole. This probe looks at the
staged tree, the queue's loopback port and the watchman heartbeat, writes a
verdict to ~/.local/state/oc2-agent/health.json plus one jsonl line, and exits
1 on a failed row so systemd marks the oneshot failed and the journal carries
the alarm.

No restart is built in. A restart needs a command, and no lane has supplied
one; META_AGENT_RESTART, when set, is run once after a failed queue row and
its exit code is recorded as a row of its own.

An absent watchman heartbeat is not a failure: an image without the relay
watchman has none, and calling that broken would alarm on every clean install.

Usage:
    meta-agent-health.py [--root DIR] [--home DIR] [--port N] [--json]
                         [--no-write] [--stale-after SECONDS]
"""
from __future__ import annotations

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

UNITS = (
    "oc2-queue.service",
    "oc2-trio.service",
    "oc2-patrol.service",
    "oc2-patrol.timer",
    "oc2-health.service",
    "oc2-health.timer",
)
SESSION_SERVICES = ("oc2-queue.service", "oc2-trio.service", "oc2-patrol.service")
TIMERS = ("oc2-patrol.timer", "oc2-health.timer")
BEAT_REL = Path(".local/state/oc2-agent/watchman.heartbeat.json")


def row(name, state, detail):
    return {"name": name, "state": state, "detail": detail}


def check_units(root):
    missing = [u for u in UNITS if not (root / "usr/lib/systemd/user" / u).is_file()]
    if missing:
        return row("units", "fail", "missing " + ", ".join(missing))
    return row("units", "pass", "%d units" % len(UNITS))


def check_enabled(root):
    wants = root / "etc/systemd/user"
    expect = (
        [(wants / "default.target.wants" / u, u) for u in SESSION_SERVICES]
        + [(wants / "timers.target.wants" / u, u) for u in TIMERS]
    )
    torn = [name for link, name in expect if not link.is_symlink() and not link.is_file()]
    if torn:
        return row("enabled", "fail", "not enabled: " + ", ".join(torn))
    return row("enabled", "pass", "%d links" % len(expect))


def check_queue(port, timeout=1.0):
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=timeout):
            return row("queue", "pass", "127.0.0.1:%d answers" % port)
    except OSError as exc:
        return row("queue", "fail",
                   "127.0.0.1:%d refused (%s)" % (port, exc.__class__.__name__))


def check_watchman(path, stale_after):
    if not path.is_file():
        return row("watchman", "absent", "no heartbeat at %s" % path)
    try:
        beat = json.loads(path.read_text(encoding="utf-8"))
        ts = float(beat["ts"])
    except (OSError, ValueError, KeyError, TypeError):
        return row("watchman", "fail", "heartbeat unreadable: %s" % path)
    age = max(0.0, time.time() - ts / 1000.0)
    if age > stale_after:
        return row("watchman", "fail",
                   "heartbeat %.0fs old (limit %ds)" % (age, stale_after))
    return row("watchman", "pass", "heartbeat %.0fs old" % age)


def maybe_restart(rows, timeout=60):
    command = os.environ.get("META_AGENT_RESTART", "").strip()
    if not command:
        return
    if not any(r["name"] == "queue" and r["state"] == "fail" for r in rows):
        return
    try:
        proc = subprocess.run(command, shell=True, capture_output=True,
                              text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        rows.append(row("restart", "fail", "timed out after %ds" % timeout))
        return
    output = (proc.stderr or proc.stdout or "").strip().splitlines()
    rows.append(row("restart", "pass" if proc.returncode == 0 else "fail",
                    "exit %d%s" % (proc.returncode,
                                   (": " + output[-1][:120]) if output else "")))


def write_verdict(state_dir, verdict):
    state_dir.mkdir(parents=True, exist_ok=True)
    line = json.dumps(verdict, sort_keys=True)
    tmp = state_dir / "health.json.tmp"
    tmp.write_text(line + "\n", encoding="utf-8")
    os.replace(tmp, state_dir / "health.json")
    with (state_dir / "health.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(line + "\n")


def main(argv=None):
    ap = argparse.ArgumentParser(description="one health check of the OC2 agent layer")
    ap.add_argument("--root", default=os.environ.get("METAOS_ROOT", "/"),
                    help="root filesystem to inspect (default /)")
    ap.add_argument("--home", default=str(Path.home()),
                    help="user home holding the state directory")
    ap.add_argument("--port", type=int, default=int(os.environ.get("OC2_QUEUE_PORT", "8935")))
    ap.add_argument("--stale-after", type=int, default=300,
                    help="seconds a watchman heartbeat may be old (default 300)")
    ap.add_argument("--json", action="store_true", help="print the verdict as JSON")
    ap.add_argument("--no-write", action="store_true", help="print only, write no state")
    args = ap.parse_args(argv)

    root = Path(args.root)
    home = Path(args.home)
    rows = [
        check_units(root),
        check_enabled(root),
        check_queue(args.port),
        check_watchman(home / BEAT_REL, args.stale_after),
    ]
    maybe_restart(rows)

    ok = not any(r["state"] == "fail" for r in rows)
    verdict = {
        "ts": int(time.time() * 1000),
        "iso": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "root": str(root),
        "port": args.port,
        "ok": ok,
        "rows": rows,
    }

    if not args.no_write:
        write_verdict(home / ".local/state/oc2-agent", verdict)

    if args.json:
        print(json.dumps(verdict, sort_keys=True))
    else:
        for r in rows:
            print("%-6s %-9s %s" % (r["state"].upper(), r["name"], r["detail"]))
        print("meta-agent-health: %s" % ("OK" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
