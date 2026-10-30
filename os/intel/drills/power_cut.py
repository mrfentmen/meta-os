"""Power-cut drill (Milo lane, OS-040).

Acceptance: hard-kill the VM mid-job three times; on reboot
leases expire, jobs requeue, and the boot brief reports the
interruption. Three of three runs recover with zero manual
fixes.

Runs unattended on fixtures: no network, no Redis, no bus
posts, no real VM. A real hard kill of a booted Meta OS
image cannot be performed from this repo — there is no test
image here, and killing this host VM would kill the drill
itself — so the power cut is modeled the way the OS-034
drill models systemd: the cut means exactly one thing, the
worker vanishes with no graceful shutdown and no lease
release. What the drill proves is the watchdog + sweep +
brief half of the acceptance, which is Milo's lane:

  cut        presence stops, heartbeats stop, the job stays
             claimed with its lease still in the future.
  reboot     a tick past the lease expiry yields exactly one
             presence-stall alert naming nick, job, and age.
  sweep      the jobs.py requeue rule (imported from the
             WDG-020 drill, not re-implemented here) reopens
             the job: status open, claim fields cleared.
  brief      the sweep record reconciles through the OS-127
             recovery line: "1 recovered", job title named,
             baton step named — the interruption is reported,
             never silently dropped.
  reclaim    a second worker claims the requeued job and
             ticks healthy: the job is claimable after boot.

Zero manual fixes means no step in the drill edits a job
record by hand: the only state change between cut and
reclaim is the sweep rule, and the only watchdog output is
the tick. A control run proves the sweep respects the
lease: a reboot before lease expiry requeues nothing, the
job stays claimed, and only the stall alert fires.

Timeline uses a fake clock (base time T0) so the drill is
deterministic: thresholds are read from intel/thresholds.py,
never hardcoded, so a threshold retune retunes the drill.

Usage: python3 intel/drills/power_cut.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import brief as ibrief  # noqa: E402
from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402
from intel.drills.kill_worker import (  # noqa: E402
    FakeWorker, sweep_expired_leases)

T0 = 100000
RUNS = (("pax", "7"), ("rowan", "8"), ("hana", "9"))


def _check(log, name, condition, detail=""):
    log.append(("PASS" if condition else "FAIL") + ": " + name
               + (f" — {detail}" if detail and not condition else ""))
    return bool(condition)


def _one_run(nick, job_id):
    """One cut/reboot/recover cycle. Returns (ok, log, report).

    The report carries the alert, the sweep result, the boot
    brief recovery line, and the reclaim tick, so tests can
    assert on the outcome without parsing stdout.
    """
    log = []
    ok = True
    snapshot = {"messages": [], "jobs": [],
                "presence": [], "caps": {nick: {"caps": "build"}}}
    worker = FakeWorker(nick)

    # Phase 1 — healthy worker: claim, deposit progress + baton.
    job = worker.claim(snapshot, job_id, T0)
    worker.progress(snapshot, T0 + 120, "halfway through the job")
    job["baton_step"] = "step 2: second half remains"
    worker.heartbeat(snapshot, T0 + 300)
    ok &= _check(log, "healthy worker ticks zero alerts",
                 watchdog.tick(snapshot, now=T0 + 300) == [])

    # Phase 2 — the power cut: no shutdown, no lease release.
    worker.kill(snapshot)
    ok &= _check(log, "cut leaves the job claimed, lease unreleased",
                 job.get("status") == "claimed"
                 and job.get("claim") == nick
                 and job.get("lease_until", 0) > T0 + 300,
                 f"got {job}")

    # Phase 3 — reboot past lease expiry: stall alert fires.
    reboot_at = (T0 + 300 + thresholds.LEASE_DEFAULT_SECONDS + 61)
    got = watchdog.tick(snapshot, now=reboot_at)
    alert = got[0] if got else {}
    ok &= _check(log, "reboot tick yields exactly one presence-stall",
                 [a.get("kind") for a in got] == ["presence-stall"],
                 f"got {got}")
    ok &= _check(log, "stall alert names nick, job, and age",
                 alert.get("nick") == nick
                 and alert.get("job") == job_id
                 and alert.get("last_progress_age_seconds", 0)
                 > thresholds.STALL_MINUTES * 60,
                 f"got {alert}")

    # Phase 4 — lease sweep: the job requeues, nothing else moves.
    requeued = sweep_expired_leases(snapshot, reboot_at)
    ok &= _check(log, "sweep requeues exactly this job",
                 requeued == [job_id], f"got {requeued}")
    ok &= _check(log, "requeued job is open with claim cleared",
                 job.get("status") == "open"
                 and "claim" not in job
                 and "lease_until" not in job,
                 f"got {job}")

    # Phase 5 — boot brief reports the interruption, reconciled.
    recovery = {"recovered": [{"id": job_id,
                               "title": job.get("title", "demo job"),
                               "baton_step": job.get("baton_step")}],
                "sweep_count": len(requeued)}
    line = ibrief.recovery_line(recovery)
    ok &= _check(log, "boot brief recovery line reports 1 recovered",
                 line.startswith("In-flight jobs recovered at this boot: "
                                 "1 recovered")
                 and job_id in line
                 and "step 2" in line
                 and "recovery incomplete" not in line,
                 f"got {line}")

    # Phase 6 — the stall alert auto-resolves; job is claimable.
    ok &= _check(log, "re-tick after requeue yields zero stall alerts",
                 watchdog.tick(snapshot, now=reboot_at + 60) == [])
    second = FakeWorker("second-worker")
    second.claim(snapshot, job_id, reboot_at + 120)
    second.heartbeat(snapshot, reboot_at + 120)
    ok &= _check(log, "second worker claims the requeued job healthy",
                 watchdog.tick(snapshot, now=reboot_at + 120) == [])

    report = {"nick": nick, "job": job_id, "alert": alert,
              "requeued": requeued, "recovery_line": line}
    return ok, log, report


def _control_run():
    """Reboot before lease expiry: nothing requeues, job stays.

    Proves the sweep in the three real runs is the lease rule
    doing its job, not the drill forcing a requeue.
    """
    log = []
    ok = True
    nick, job_id = "pax", "7"
    snapshot = {"messages": [], "jobs": [],
                "presence": [], "caps": {nick: {"caps": "build"}}}
    worker = FakeWorker(nick)
    job = worker.claim(snapshot, job_id, T0)
    worker.progress(snapshot, T0 + 120, "halfway through the job")
    worker.kill(snapshot)
    early = T0 + 300 + thresholds.STALL_MINUTES * 60 + 61
    ok &= _check(log, "early reboot still fires the stall alert",
                 [a.get("kind") for a in watchdog.tick(snapshot, now=early)]
                 == ["presence-stall"])
    ok &= _check(log, "early sweep requeues nothing, lease unexpired",
                 sweep_expired_leases(snapshot, early) == []
                 and job.get("status") == "claimed",
                 f"got {job}")
    return ok, log


def run_drill():
    """Run all three power cuts plus the control.

    Returns a report dict (per-run reports, control outcome,
    phase log) so tests can assert on the drill's outcome
    without parsing stdout.
    """
    log = []
    ok = True
    reports = []
    for nick, job_id in RUNS:
        run_ok, run_log, report = _one_run(nick, job_id)
        ok &= run_ok
        log.append(f"--- power cut: {nick}/job {job_id} ---")
        log.extend(run_log)
        reports.append(report)
    ctl_ok, ctl_log = _control_run()
    ok &= ctl_ok
    log.append("--- control: reboot before lease expiry ---")
    log.extend(ctl_log)
    return {"ok": ok, "log": log, "runs": reports, "control_ok": ctl_ok}


def main():
    report = run_drill()
    for line in report["log"]:
        print(line)
    print("RESULT: " + ("PASS" if report["ok"] else "FAIL"))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
