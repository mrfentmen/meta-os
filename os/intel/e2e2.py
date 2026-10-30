"""intel/e2e2.py -- INT-003 end-to-end test 2, scripted loop.

Worker dies mid-job -> watchdog alert -> sweep requeue -> second
worker finishes -> alert auto-resolves, as one scripted run with a
transcript written to intel/evals/e2e2.log.

What this run is, plainly:

- The queue is the in-memory fake Redis surface from
  tests/fake_redis.py, the same surface the unit suite uses.
  Nothing here touches the live bus or posts a real job. The job
  namespace is the INT-001 integration namespace
  (muse-bus:int-job), the capability namespace is
  muse-bus:int-cap, and the room is build-int, so even the fake
  state is disjoint from production keys.
- Every queue transition is a real jobs.py command: post, claim,
  progress, sweep, claim, progress, done. The watchdog step reads
  a real intel/ingest.py snapshot of that queue state, not a
  hand-built dict. That is the point of this loop: the WDG-020
  kill drill already proves the same story on fixture dicts;
  this loop proves it on the real command path.
- Time travel is the one simulation, and it uses the fake's own
  injectable clock: time.time is patched to the fake clock and
  the fake is advanced, so presence TTL (120s) and the claim
  lease (1800s) lapse by the fake's real expiry rules, not by
  deleting keys. The watchdog tick takes an explicit now from
  that same clock, the way WDG-026 documents. Nothing else
  about the death is faked: worker-a simply stops beating and
  stops renewing, and the loop waits (on the fake clock) until
  both lapses have happened.
- The watchdog fix this loop depends on is in
  intel/watchdog.py, not in this script: the stall detectors
  used to read only hand-snapshot timestamp fields
  (last_progress / claimed_at), while real snapshot rows carry
  last_progress_at. The loop pins the fixed behavior; it does
  not adapt the snapshot by hand to hide the gap.
- The alert announcement line is held, never posted: the loop
  asserts the room message list never gains the ALERT line.
  Watchdog v1 never mutates job state; the sweep command does
  the requeue, and the re-tick proving auto-resolve reads the
  requeued (open) job, which no detector fires on.

Stages, each asserted, any failure failing the run:

  1. post: one job posted, open, attempts 0, max_attempts 3.
  2. worker-a: worker-a registers caps, beats presence, claims,
     progresses; the snapshot shows it claimed by worker-a, and
     a tick at that moment yields zero alerts (healthy worker).
  3. death and alert: after the stall window passes on the fake
     clock, worker-a is gone from presence, the job is still
     claimed, and a tick yields exactly one presence-stall
     alert naming worker-a and the job, with the exact age
     since its last progress; the announcement line is held.
  4. sweep requeue: after the lease lapses on the fake clock,
     the real jobs.py sweep prints REQUEUED for the job, and
     the job reads open with its claim fields cleared.
  5. alert auto-resolves: a re-tick on the requeued state
     yields zero alerts.
  6. worker-b: worker-b claims, progresses, and finishes the
     job; it reads done.
  7. final quiet: a tick on the finished state yields zero
     alerts, and the snapshot carries the job done.

Usage, from the repo root: python3 intel/e2e2.py
Exit 0 with the transcript on stdout and in
intel/evals/e2e2.log when every stage passes, exit 1
otherwise. Importing this module runs nothing: all setup
(env, fake surface, nicks, clock) happens inside run_loop,
and run_loop restores the job namespace, capability
namespace, and nicks it changed, so the unit suite can call
it inside its own harness.
"""

import contextlib
import io
import json
import os
import sys
from unittest import mock

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

from intel import integration  # noqa: E402

TITLE = "Fix the e2e2 stall note"
SPEC = ("Goal: close the INT-003 loop. Context: INT-003 fixture. "
        "Files: intel/e2e2_note.txt. Steps: write the note. "
        "Out of scope: any other file.")
FILES = "intel/e2e2_note.txt"
MAX_ATTEMPTS = 3
WORKER_A = "worker-a"
WORKER_B = "worker-b"
PROGRESS_A = "halfway through the stall note"
PROGRESS_B = "finishing the stall note"
DONE_COMMIT = "e2e2-no-real-commit"

LOG_PATH = os.path.join(ROOT, "intel", "evals", "e2e2.log")

_STAGE_NAMES = ("post", "worker-a", "death and alert",
                "sweep requeue", "alert auto-resolves",
                "worker-b", "final quiet")


def _run_cli(main, argv):
    """Run a script main(); return (exit code, stdout, stderr)."""
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), \
            contextlib.redirect_stderr(err), \
            mock.patch("sys.stdin", io.StringIO("")):
        code = main(argv)
    return code, out.getvalue(), err.getvalue()


def _job_list_json(jobs_mod):
    code, out, _err = _run_cli(jobs_mod.main, ["list", "--json"])
    if code != 0:
        raise AssertionError(f"jobs list failed with exit {code}")
    return json.loads(out)


def run_loop(write_log=True):
    """Run the INT-003 loop; return the result dict.

    Returns {"ok": bool, "stages": [(name, ok, detail)], ...}.
    With write_log, the transcript is also written to
    intel/evals/e2e2.log. Restores jobs.NS, capabilities.CAPNS,
    and the nicks it changed, so a caller inside another
    harness is unaffected.
    """
    # INT-001 import-order rule: the namespace variables must be
    # set before jobs (and mos.capabilities) are imported, or
    # the already-read prefixes do not move.
    integration.apply_env()
    import relay_common as rc  # noqa: E402
    import jobs  # noqa: E402
    from intel import ingest  # noqa: E402
    from intel import thresholds  # noqa: E402
    from intel import watchdog  # noqa: E402
    from mos import capabilities  # noqa: E402
    from fake_redis import FakeUpstash  # noqa: E402

    stages = []

    def stage(name, fn):
        try:
            detail = fn()
        except Exception as exc:  # noqa: BLE001 - a stage
            # failure is a loop failure, reported, not traced
            stages.append((name, False, f"{type(exc).__name__}: {exc}"))
            return None
        stages.append((name, True, detail))
        return detail

    old_ns = jobs.NS
    old_capns = capabilities.CAPNS
    old_nicks = (rc.NICK, jobs.NICK)
    fake = FakeUpstash()
    patches = [
        mock.patch.object(rc, "api_get", fake.api_get),
        mock.patch.object(rc, "api_post", fake.api_post),
        mock.patch.object(rc, "bus_push", fake.bus_push),
        mock.patch("time.time", fake.now),
    ]
    for mod in (jobs,):
        for attr in ("api_get", "api_post", "bus_push"):
            if hasattr(mod, attr):
                patches.append(mock.patch.object(
                    mod, attr, getattr(fake, attr)))
    # intel.store and intel.ingest reach the bus through
    # relay_common's names; patching relay_common covers them,
    # but modules that did `from relay_common import api_get`
    # hold their own reference, so patch those too.
    import intel.store as store_mod  # noqa: E402
    import intel.ingest as ingest_mod  # noqa: E402
    for mod in (store_mod, ingest_mod):
        for attr in ("api_get", "api_post", "bus_push"):
            if hasattr(mod, attr):
                patches.append(mock.patch.object(
                    mod, attr, getattr(fake, attr)))
    result = {"ok": False, "stages": stages}
    try:
        for patch in patches:
            patch.start()
        # INT-001 import-order rule, second half: when jobs and
        # capabilities were already imported before this call
        # (as in the unit harness), setting the variables
        # cannot move the already-read prefixes, so assign
        # the integration prefixes explicitly. The finally
        # block below restores the old prefixes.
        assert os.environ.get("MUSE_RELAY_JOBNS") == \
            integration.INT_JOBNS
        assert os.environ.get("MUSE_RELAY_CAPNS") == \
            integration.INT_CAPNS
        jobs.NS = integration.INT_JOBNS
        capabilities.CAPNS = integration.INT_CAPNS

        job_holder = {}
        alert_holder = {}

        def do_post():
            rc.NICK = "pax"
            jobs.NICK = "pax"
            before = _job_list_json(jobs)
            assert before == [], f"job list not empty before: {before}"
            code, out, err = _run_cli(jobs.main, [
                "post", "--title", TITLE, "--spec", SPEC,
                "--files", FILES, "--max-attempts", str(MAX_ATTEMPTS),
                "--room", integration.INT_ROOM])
            assert code == 0, f"post failed: {err}"
            assert out.startswith("JOB "), f"unexpected post out: {out}"
            job_id = out.split()[1]
            listed = _job_list_json(jobs)
            assert len(listed) == 1, f"job list after post: {listed}"
            row = listed[0]
            assert row["id"] == job_id
            assert row["status"] == "open"
            assert row["attempts"] == 0
            stored = jobs._hgetall(jobs._job_key(job_id))
            assert stored.get("max_attempts") == str(MAX_ATTEMPTS), (
                f"max_attempts stored as {stored.get('max_attempts')}")
            job_holder["id"] = job_id
            return (f"job {job_id} posted, open, attempts 0, "
                    f"max_attempts {MAX_ATTEMPTS}")

        stage("post", do_post)

        def do_worker_a():
            job_id = job_holder["id"]
            assert capabilities.register(WORKER_A, ["python"]) is True
            rc.NICK = WORKER_A
            jobs.NICK = WORKER_A
            rc.presence_beat()
            code, _out, err = _run_cli(jobs.main, ["claim", job_id])
            assert code == 0, f"worker-a claim failed: {err}"
            code, _out, err = _run_cli(
                jobs.main, ["progress", job_id, "--note", PROGRESS_A])
            assert code == 0, f"worker-a progress failed: {err}"
            snapshot = ingest.snapshot(integration.INT_ROOM)
            assert WORKER_A in snapshot["presence"], (
                "worker-a must be present while alive")
            assert WORKER_A in snapshot["caps"], (
                "worker-a must be in the caps registry")
            rows = {job["id"]: job for job in snapshot["jobs"]}
            row = rows[job_id]
            assert row["status"] == "claimed"
            assert row["claim"] == WORKER_A
            assert row["last_progress_at"] is not None
            job_holder["last_progress_at"] = row["last_progress_at"]
            got = watchdog.tick(snapshot, now=int(fake.now()))
            assert got == [], f"healthy worker must yield zero alerts, got {got}"
            return (f"{WORKER_A} claimed and progressed job {job_id}; "
                    f"healthy tick yields zero alerts")

        stage("worker-a", do_worker_a)

        def do_death_and_alert():
            job_id = job_holder["id"]
            # Presence TTL is 120s and the stall window is
            # STALL_MINUTES; advancing past the window lapses
            # presence by the fake's own expiry rule. The lease
            # (1800s) still holds at this point, so the job
            # stays claimed: the watchdog must fire, not the
            # sweep, at this stage.
            fake.advance(thresholds.STALL_MINUTES * 60 + 61)
            stall_now = int(fake.now())
            snapshot = ingest.snapshot(integration.INT_ROOM)
            assert WORKER_A not in snapshot["presence"], (
                "dead worker must be gone from presence")
            assert WORKER_A in snapshot["caps"], (
                "caps registry keeps the dead worker listed")
            rows = {job["id"]: job for job in snapshot["jobs"]}
            row = rows[job_id]
            assert row["status"] == "claimed", (
                "job must still be claimed before the sweep")
            assert row["claim"] == WORKER_A
            got = watchdog.tick(snapshot, now=stall_now)
            assert len(got) == 1, (
                f"dead worker must yield exactly one alert, got {len(got)}: {got}")
            alert = got[0]
            assert alert["kind"] == "presence-stall", alert
            assert alert["nick"] == WORKER_A, alert
            assert alert["job"] == job_id, alert
            expected_age = stall_now - job_holder["last_progress_at"]
            assert alert["last_progress_age_seconds"] == expected_age, alert
            assert expected_age > thresholds.STALL_MINUTES * 60
            lines = watchdog.announcements_for(got)
            assert len(lines) == 1 and lines[0].startswith("ALERT:"), lines
            assert all(lines[0] not in msg
                       for msg in snapshot["messages"]), (
                "announcement line must be held, never posted")
            alert_holder["alert"] = alert
            alert_holder["stall_now"] = stall_now
            return (f"presence-stall alert names {WORKER_A}/{job_id}, "
                    f"age {expected_age}s; announcement line held")

        stage("death and alert", do_death_and_alert)

        def do_sweep():
            job_id = job_holder["id"]
            # Lease lapses 1800s after the progress renewal;
            # advance the remainder past it, then run the real
            # sweep command: it, not the loop, requeues.
            elapsed = thresholds.STALL_MINUTES * 60 + 61
            fake.advance(thresholds.LEASE_DEFAULT_SECONDS - elapsed + 1)
            rc.NICK = "pax"
            jobs.NICK = "pax"
            code, out, err = _run_cli(jobs.main, ["sweep"])
            assert code == 0, f"sweep failed: {err}"
            assert f"REQUEUED {job_id}" in out, (
                f"sweep must requeue the job, got: {out}")
            listed = _job_list_json(jobs)
            row = {job["id"]: job for job in listed}[job_id]
            assert row["status"] == "open", f"job after sweep: {row}"
            assert row["claim"] is None, f"claim not cleared: {row}"
            assert row["lease_until"] is None, (
                f"lease_until not cleared: {row}")
            return (f"sweep printed REQUEUED {job_id}; job open, "
                    f"claim and lease cleared")

        stage("sweep requeue", do_sweep)

        def do_auto_resolve():
            job_id = job_holder["id"]
            snapshot = ingest.snapshot(integration.INT_ROOM)
            rows = {job["id"]: job for job in snapshot["jobs"]}
            assert rows[job_id]["status"] == "open"
            got = watchdog.tick(snapshot, now=int(fake.now()))
            assert got == [], (
                f"requeued job must stop firing, got {got}")
            return "re-tick on the requeued job yields zero alerts"

        stage("alert auto-resolves", do_auto_resolve)

        def do_worker_b():
            job_id = job_holder["id"]
            assert capabilities.register(WORKER_B, ["python"]) is True
            rc.NICK = WORKER_B
            jobs.NICK = WORKER_B
            code, _out, err = _run_cli(jobs.main, ["claim", job_id])
            assert code == 0, f"worker-b claim failed: {err}"
            code, _out, err = _run_cli(
                jobs.main, ["progress", job_id, "--note", PROGRESS_B])
            assert code == 0, f"worker-b progress failed: {err}"
            code, _out, err = _run_cli(
                jobs.main, ["done", job_id,
                            "--commit", DONE_COMMIT,
                            "--note", PROGRESS_B])
            assert code == 0, f"worker-b done failed: {err}"
            listed = _job_list_json(jobs)
            row = {job["id"]: job for job in listed}[job_id]
            assert row["status"] == "done", f"job after worker-b: {row}"
            return (f"{WORKER_B} claimed, progressed, done job {job_id}")

        stage("worker-b", do_worker_b)

        def do_final_quiet():
            job_id = job_holder["id"]
            snapshot = ingest.snapshot(integration.INT_ROOM)
            rows = {job["id"]: job for job in snapshot["jobs"]}
            assert rows[job_id]["status"] == "done"
            got = watchdog.tick(snapshot, now=int(fake.now()))
            assert got == [], f"finished job must yield zero alerts, got {got}"
            return "final tick yields zero alerts; snapshot job done"

        stage("final quiet", do_final_quiet)
    finally:
        for patch in reversed(patches):
            patch.stop()
        jobs.NS = old_ns
        capabilities.CAPNS = old_capns
        rc.NICK, jobs.NICK = old_nicks

    ok = (len(stages) == len(_STAGE_NAMES)
          and all(passed for _name, passed, _d in stages))
    result["ok"] = ok
    if ok:
        result["job_id"] = job_holder["id"]
        result["alert"] = alert_holder["alert"]

    lines = ["INT-003 end-to-end test 2",
             f"job: {TITLE} (files: {FILES})",
             ("queue: in-memory fake surface, namespace "
              f"{integration.INT_JOBNS}, caps "
              f"{integration.INT_CAPNS}, room {integration.INT_ROOM}"),
             ("clock: fake clock advanced, never wall-waited; "
              "presence TTL 120s, lease 1800s, stall window "
              f"{thresholds.STALL_MINUTES} minutes"),
             ""]
    for name, passed, detail in stages:
        lines.append(f"[{'PASS' if passed else 'FAIL'}] {name}: {detail}")
    lines.append("")
    lines.append("INT-003: " + ("PASS (all stages)"
                                if ok else "FAIL"))
    transcript = "\n".join(lines) + "\n"
    result["transcript"] = transcript
    if write_log:
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "w") as handle:
            handle.write(transcript)
    return result


def main():
    """Run the loop, print the transcript, exit 0/1."""
    result = run_loop(write_log=True)
    sys.stdout.write(result["transcript"])
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
