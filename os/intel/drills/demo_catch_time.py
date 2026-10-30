"""Demo catch-time measurement (Milo lane, DEM-012).

DEMO.md Shot 8: from the Shot 7 silence cue to the red STALL
alert on the dashboard must be under 90 seconds, in demo
configuration — that is, with the DEM-013 profile
(intel/metaos-demo.env) loaded, not production thresholds.

This script measures that catch, three times, on fixtures.
Each rehearsal replays the DEM-011 staging exactly (milo
claims demo job 7, posts one progress note at T0+60, goes
silent at the T0+120 cue), then ticks the watchdog every
DEMO_TICK_INTERVAL_SECONDS (5 s, the demo loop's interval)
from the cue until the first alert, or until the 90 s budget
is spent. The three rehearsals differ only in tick-grid
phase (first tick at cue+0 s, cue+2 s, cue+4 s): a live loop's
phase against the cue is luck, so the measurement must hold
for every phase, not just one lucky alignment.

The catch is measured from the cue, not from the last
progress note: the audience sees silence start at the cue,
and the alert's displayed last-progress age is reported
separately so nobody confuses the two numbers. Under the
demo profile (stall 1 min) the alert fires as soon as the
last-progress age passes 60 s — the note is already 60 s old
at the cue, so the first post-cue tick past the threshold
is the catch, a handful of seconds, not minutes.

Usage: python3 intel/drills/demo_catch_time.py
Exit 0 with a PASS line per rehearsal on success, 1 on
failure. No network, no Redis, no bus posts: the ALERT line
is held, per Dale's posting rule. This script reads the
profile file itself and applies it before importing
intel.thresholds, so the measurement can never silently
run on production thresholds: it asserts the loaded stall
window equals the profile's value before ticking.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, REPO_ROOT)

PROFILE_PATH = os.path.join(REPO_ROOT, "intel", "metaos-demo.env")
CATCH_BUDGET_SECONDS = 90
TICK_INTERVAL_SECONDS = 5
TICK_PHASES_SECONDS = (0, 2, 4)

JOB_ID = "7"
NICK = "milo"
T0 = 100000
PROGRESS_AT_OFFSET = 60
CUE_OFFSET = 120


def load_profile(path):
    """Parse the demo .env file into {name: value}, comments out.

    Only WATCHDOG_* entries are applied to the environment;
    DEMO_TICK_INTERVAL_SECONDS is the operator's loop setting,
    not a threshold, and is returned for the caller to check
    against TICK_INTERVAL_SECONDS rather than exported.
    """
    values = {}
    with open(path) as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            name, _, value = line.partition("=")
            values[name.strip()] = value.strip()
    return values


def _apply_profile_or_fail():
    profile = load_profile(PROFILE_PATH)
    for name, value in profile.items():
        if name.startswith("WATCHDOG_"):
            os.environ[name] = value
    tick_interval = profile.get("DEMO_TICK_INTERVAL_SECONDS")
    assert tick_interval is not None, (
        "demo profile must state DEMO_TICK_INTERVAL_SECONDS")
    assert int(tick_interval) == TICK_INTERVAL_SECONDS, (
        f"measurement ticks every {TICK_INTERVAL_SECONDS}s but the "
        f"profile says {tick_interval}s — run the loop at the "
        f"measured interval or re-measure")
    return profile


# The profile must be applied before intel.thresholds is
# imported: thresholds are read once at import time.
_PROFILE = _apply_profile_or_fail()

from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402
from intel.drills import kill_worker  # noqa: E402

assert thresholds.STALL_MINUTES == int(
    _PROFILE["WATCHDOG_STALL_MINUTES"]), (
    f"loaded stall window {thresholds.STALL_MINUTES} does not match "
    f"demo profile {_PROFILE['WATCHDOG_STALL_MINUTES']} — refusing "
    f"to measure on the wrong thresholds")


def run_rehearsal(phase_seconds):
    """One catch measurement at the given tick-grid phase.

    Returns a report dict (catch seconds, displayed age,
    alert, phase, tick log) so tests can assert on the
    measurement without parsing stdout.
    """
    snapshot = {"messages": [], "jobs": [],
                "presence": [], "caps": {NICK: {"caps": "build"}}}
    worker = kill_worker.FakeWorker(NICK)
    worker.claim(snapshot, JOB_ID, T0)
    worker.progress(snapshot, T0 + PROGRESS_AT_OFFSET, "working on it")
    worker.heartbeat(snapshot, T0 + PROGRESS_AT_OFFSET)
    assert watchdog.tick(snapshot, now=T0 + PROGRESS_AT_OFFSET) == [], (
        "healthy staged worker must yield zero alerts")
    cue_at = T0 + CUE_OFFSET
    worker.kill(snapshot)
    assert NICK not in snapshot["presence"]

    tick_at = cue_at + phase_seconds
    alert = None
    ticks = 0
    while tick_at < cue_at + CATCH_BUDGET_SECONDS:
        ticks += 1
        got = watchdog.tick(snapshot, now=tick_at)
        if got:
            assert len(got) == 1, (
                f"catch tick must yield exactly one alert, got {got}")
            alert = got[0]
            break
        tick_at += TICK_INTERVAL_SECONDS
    assert alert is not None, (
        f"no alert within {CATCH_BUDGET_SECONDS}s of the cue "
        f"(phase {phase_seconds}s) — catch budget missed")
    assert alert["kind"] == "presence-stall", alert
    assert alert["nick"] == NICK, alert
    assert alert["job"] == JOB_ID, alert
    lines = watchdog.announcements_for([alert])
    assert len(lines) == 1 and lines[0].startswith("ALERT:"), lines
    return {
        "phase_seconds": phase_seconds,
        "catch_seconds": tick_at - cue_at,
        "last_progress_age_seconds": alert["last_progress_age_seconds"],
        "ticks_to_catch": ticks,
        "alert": alert,
    }


def run_measurement():
    """All three rehearsals; returns the list of reports."""
    return [run_rehearsal(phase) for phase in TICK_PHASES_SECONDS]


def main(argv=None):
    try:
        reports = run_measurement()
    except AssertionError as exc:
        print(f"demo_catch_time measurement: FAIL: {exc}")
        return 1
    for report in reports:
        print(f"demo_catch_time measurement: rehearsal "
              f"(tick phase +{report['phase_seconds']}s): catch "
              f"{report['catch_seconds']}s after cue, alert "
              f"presence-stall milo/7, last progress "
              f"{report['last_progress_age_seconds']}s ago, "
              f"{report['ticks_to_catch']} ticks")
        assert report["catch_seconds"] < CATCH_BUDGET_SECONDS
    print(f"demo_catch_time measurement: PASS — 3/3 rehearsals under "
          f"{CATCH_BUDGET_SECONDS}s (catches: "
          f"{', '.join(str(r['catch_seconds']) + 's' for r in reports)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
