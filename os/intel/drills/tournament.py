#!/usr/bin/env python3
"""Drill tournament (Milo lane, INT-021).

Runs the three watchdog drills back to back in one session,
in demo order, timed end to end, the way the demo will run
them live:

    1. kill_worker.py    (WDG-020: kill-a-worker)
    2. collision.py      (WDG-021: file collision)
    3. dead_dep.py       (WDG-022: dead dependency)

Acceptance (INT-021): the combined drill log is produced in
one session and its total wall time is under 6 minutes
(360 seconds). Each drill must exit 0 and print its PASS
line; a drill failure, a missing PASS line, or a total at
or over the limit fails the tournament.

Runs unattended on fixtures: no network, no Redis, no bus
posts; the drills themselves are fixture-only, and this
runner only spawns them as subprocesses and records their
output. The log is written to intel/evals/drill_tournament.log
unless write_log=False (used by the pinning tests, so the
suite run leaves no state behind).

Usage: python3 intel/drills/tournament.py
Exit 0 with an INT-021: PASS line on success, 1 on failure.
"""

import os
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
LOG_PATH = os.path.join(ROOT, "intel", "evals", "drill_tournament.log")

DRILLS = [
    ("kill_worker", "WDG-020"),
    ("collision", "WDG-021"),
    ("dead_dep", "WDG-022"),
]
LIMIT_SECONDS = 360.0


def run_tournament(write_log=True):
    """Run all three drills in order; return a result dict.

    Result keys: ok, total_seconds, drills (list of dicts with
    name, task, exit_code, seconds, pass_line), transcript.
    """
    lines = ["INT-021 drill tournament: kill_worker, collision, "
             "dead_dep, back to back in one session"]
    drills = []
    started = time.monotonic()
    ok = True
    for name, task in DRILLS:
        drill_started = time.monotonic()
        proc = subprocess.run(
            [sys.executable,
             os.path.join(ROOT, "intel", "drills", name + ".py")],
            capture_output=True, text=True, cwd=ROOT)
        seconds = time.monotonic() - drill_started
        out = (proc.stdout or "").strip()
        pass_line = None
        for line in out.splitlines():
            if line.strip().endswith(": PASS"):
                pass_line = line.strip()
        drill_ok = proc.returncode == 0 and pass_line is not None
        if not drill_ok:
            ok = False
        drills.append({"name": name, "task": task,
                       "exit_code": proc.returncode,
                       "seconds": seconds,
                       "pass_line": pass_line, "output": out})
        lines.append("PASS: %s (%s) -- exit 0, %s, %.2fs"
                     % (name, task, pass_line, seconds)
                     if drill_ok else
                     "FAIL: %s (%s) -- exit %d, %.2fs\n%s\n%s"
                     % (name, task, proc.returncode, seconds,
                        out, proc.stderr or ""))
    total = time.monotonic() - started
    if total >= LIMIT_SECONDS:
        ok = False
        lines.append("FAIL: total %.2fs >= %.0fs limit"
                     % (total, LIMIT_SECONDS))
    lines.append("INT-021: %s -- 3/3 drills passed, total %.2fs "
                 "(limit %.0fs)" % ("PASS" if ok else "FAIL",
                                    total, LIMIT_SECONDS)
                 if ok else
                 "INT-021: FAIL -- total %.2fs (limit %.0fs)"
                 % (total, LIMIT_SECONDS))
    transcript = "\n".join(lines) + "\n"
    if write_log:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "w") as fh:
            fh.write(transcript)
            for drill in drills:
                fh.write("\n--- %s (%s), %.2fs ---\n%s\n"
                         % (drill["name"], drill["task"],
                            drill["seconds"], drill["output"]))
    return {"ok": ok, "total_seconds": total, "drills": drills,
            "transcript": transcript}


def main():
    result = run_tournament(write_log=True)
    sys.stdout.write(result["transcript"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
