"""Driver-stall drill (Milo lane, OS-057).

Acceptance: wedge a driver process (alive, heartbeat stale); the
watchdog raises the same STALL alert as for a crew worker and the
driver is restarted per contract without touching other drivers.

What fixtures can prove, and what they cannot, stated plainly. A
wedged driver is alive, so it stays in the presence list: this is
WDG-003's case, not WDG-002's. A driver nick in caps, present,
holding a claimed job with no progress past
thresholds.PROGRESS_STALL_MINUTES yields exactly one
progress-stall alert, severity critical, naming the driver and
the job, through the same detector a wedged crew worker fires
through, with no driver special-casing anywhere in
intel/watchdog.py. Under the demo thresholds profile
(intel/metaos-demo.env, WATCHDOG_PROGRESS_STALL_MINUTES=1) the
same wedge fires at 61 seconds, so the alert lands inside the
demo threshold. The full tick never mutates a job: the wedged
job stays claimed with its driver and the sibling driver's job
stays claimed with the sibling, so the watchdog cannot fight
systemd over a restart and cannot touch a driver it was not
asked about.

What this drill does NOT claim: a wedged driver process
restarted on a booted test image (no test image in this repo,
no driver runner program exists yet for a template unit to
start, so the restart itself is systemd's job under the OS-034
contract and is owed on the test image exactly as OS-056's
kill -9 restart was). The sibling-undisturbed half is proven
here only at the watchdog level: the tick leaves the sibling
job claimed, unalerted, and untouched. A live sibling driver
kept running through a real restart is owed on the test image
with the driver programs.

Runs unattended on fixtures: no network, no Redis, no bus posts.
Timeline uses a fake clock (base time T0) so the drill is
deterministic: thresholds are read from intel/thresholds.py,
never hardcoded, so a threshold retune retunes the drill. The
demo phase runs this same file in a subprocess with the demo
progress-stall window in the environment, because thresholds
are read once at import time.

Usage: python3 intel/drills/driver_stall.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
WATCHDOG_SRC = os.path.join(ROOT, "intel", "watchdog.py")
DEMO_ENV = os.path.join(ROOT, "intel", "metaos-demo.env")

WEDGED = "driver-audio"
SIBLING = "driver-video"
WORKER = "pax"
T0 = 100000


def snapshot_for(wedged_last_progress, sibling_last_progress,
                 worker_last_progress):
    """Caps carry two drivers and one worker; presence carries all
    three, so every nick is alive. The wedged driver holds one
    claimed job, the sibling driver holds one, the worker holds
    one. Only the progress timestamps differ."""
    return {
        "caps": {WEDGED: {"caps": "audio"},
                 SIBLING: {"caps": "video"},
                 WORKER: {"caps": "python"}},
        "presence": [WEDGED, SIBLING, WORKER],
        "jobs": [
            {"id": "d1", "title": "play boot sting",
             "status": "claimed", "claim": WEDGED,
             "claimed_at": T0, "last_progress_at": wedged_last_progress},
            {"id": "d2", "title": "render caption",
             "status": "claimed", "claim": SIBLING,
             "claimed_at": T0, "last_progress_at": sibling_last_progress},
            {"id": "w1", "title": "write brief",
             "status": "claimed", "claim": WORKER,
             "claimed_at": T0, "last_progress_at": worker_last_progress},
        ],
        "messages": [],
    }


def phase_detector():
    stall_at = T0 + thresholds.PROGRESS_STALL_MINUTES * 60 + 1
    snap = snapshot_for(T0, stall_at - 60, stall_at - 60)
    alerts = watchdog.detect_progress_stall(snap, stall_at)
    if len(alerts) != 1:
        print(f"detector: FAIL: expected 1 alert, got {len(alerts)}")
        return False
    alert = alerts[0]
    if alert.get("kind") != "progress-stall":
        print(f"detector: FAIL: kind {alert.get('kind')}")
        return False
    if alert.get("nick") != WEDGED or alert.get("job") != "d1":
        print(f"detector: FAIL: alert names {alert.get('nick')}/"
              f"{alert.get('job')}, expected {WEDGED}/d1")
        return False
    if alert.get("severity") != "critical":
        print(f"detector: FAIL: severity {alert.get('severity')}")
        return False
    print(f"detector: wedged driver stall names {WEDGED}/d1, "
          f"severity critical, age "
          f"{alert['last_progress_age_minutes']}m: PASS")
    # No double alert: the wedged driver is present, so the
    # presence-stall detector must stay silent for it.
    if watchdog.detect_presence_stall(snap, stall_at) != []:
        print("detector: FAIL: present wedged driver must yield no "
              "presence-stall")
        return False
    print("detector: present wedged driver yields no "
          "presence-stall: PASS")
    # Negative: all fresh yields nothing.
    snap = snapshot_for(stall_at - 60, stall_at - 60, stall_at - 60)
    if watchdog.detect_progress_stall(snap, stall_at) != []:
        print("detector: FAIL: fresh drivers must yield no alert")
        return False
    print("detector: fresh drivers yield no alert: PASS")
    # No driver special-casing in the detector source.
    with open(WATCHDOG_SRC) as f:
        src = f.read()
    if "driver" in src.lower():
        print("detector: FAIL: watchdog.py mentions drivers; the "
              "detector must be unchanged, not driver-aware")
        return False
    print("detector: watchdog.py has no driver special-casing: PASS")
    return True


def phase_equivalence():
    """The same wedge on a crew worker fires the same alert: same
    kind, same severity, same shape. The driver alert is not a
    driver-only code path."""
    stall_at = T0 + thresholds.PROGRESS_STALL_MINUTES * 60 + 1
    snap = snapshot_for(stall_at - 60, stall_at - 60, T0)
    alerts = watchdog.detect_progress_stall(snap, stall_at)
    if len(alerts) != 1:
        print(f"equivalence: FAIL: expected 1 alert, got {len(alerts)}")
        return False
    alert = alerts[0]
    if (alert.get("kind") != "progress-stall"
            or alert.get("nick") != WORKER
            or alert.get("job") != "w1"
            or alert.get("severity") != "critical"):
        print(f"equivalence: FAIL: worker alert differs: {alert}")
        return False
    print("equivalence: wedged worker fires the same progress-stall "
          "alert, critical, naming pax/w1: PASS")
    return True


def phase_demo():
    """The demo profile (metaos-demo.env) sets the progress-stall
    window to 1 minute. Rerun this file's probe mode in a
    subprocess with that window: a wedge at 61 seconds must fire,
    a wedge at 30 seconds must not."""
    if not os.path.exists(DEMO_ENV):
        print("demo: FAIL: metaos-demo.env missing")
        return False
    with open(DEMO_ENV) as f:
        demo_text = f.read()
    if "WATCHDOG_PROGRESS_STALL_MINUTES=1" not in demo_text:
        print("demo: FAIL: demo profile does not set the "
              "progress-stall window to 1")
        return False
    env = dict(os.environ)
    env["WATCHDOG_PROGRESS_STALL_MINUTES"] = "1"
    env["DRIVER_STALL_DEMO_PROBE"] = "1"
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__)],
        capture_output=True, text=True, env=env, timeout=60)
    print(f"demo: probe exit={proc.returncode}")
    if proc.stdout.strip():
        print(f"demo: probe stdout: {proc.stdout.strip()}")
    if proc.stderr.strip():
        print(f"demo: probe stderr: {proc.stderr.strip()}")
    if proc.returncode != 0:
        print("demo: FAIL")
        return False
    print("demo: wedge fires at 61s and stays quiet at 30s under "
          "the demo profile: PASS")
    return True


def phase_contract():
    """The tick records but never mutates: after a full tick on
    the wedged snapshot, both driver jobs are still claimed by
    their drivers, the sibling is unalerted, and the wedged
    driver gets exactly one alert. systemd owns the restart;
    the watchdog owns the alert, and touches neither driver."""
    stall_at = T0 + thresholds.PROGRESS_STALL_MINUTES * 60 + 1
    snap = snapshot_for(T0, stall_at - 60, stall_at - 60)
    alerts = watchdog.tick(snap, now=stall_at)
    driver_alerts = [a for a in alerts if a.get("nick") == WEDGED]
    sibling_alerts = [a for a in alerts if a.get("nick") == SIBLING]
    if len(driver_alerts) != 1:
        print(f"contract: FAIL: expected 1 wedged-driver alert from "
              f"tick, got {len(driver_alerts)}")
        return False
    if sibling_alerts:
        print(f"contract: FAIL: sibling driver must be unalerted, "
              f"got {sibling_alerts}")
        return False
    by_id = {j["id"]: j for j in snap["jobs"]}
    if (by_id["d1"].get("status") != "claimed"
            or by_id["d1"].get("claim") != WEDGED):
        print(f"contract: FAIL: tick mutated the wedged job: "
              f"{by_id['d1']}")
        return False
    if (by_id["d2"].get("status") != "claimed"
            or by_id["d2"].get("claim") != SIBLING):
        print(f"contract: FAIL: tick mutated the sibling job: "
              f"{by_id['d2']}")
        return False
    print("contract: tick alerts once for the wedged driver, leaves "
          "both driver jobs claimed, sibling untouched: PASS")
    return True


def demo_probe():
    """Probe mode for phase_demo: runs under the demo window.
    Wedge at 61s fires once; wedge at 30s stays quiet."""
    snap = snapshot_for(T0, T0 + 61, T0 + 61)
    alerts = watchdog.detect_progress_stall(snap, T0 + 61)
    if len(alerts) != 1 or alerts[0].get("nick") != WEDGED:
        print(f"probe: FAIL: 61s wedge must fire once, got {alerts}")
        return 1
    snap = snapshot_for(T0 + 31, T0 + 61, T0 + 61)
    if watchdog.detect_progress_stall(snap, T0 + 61) != []:
        print("probe: FAIL: 30s wedge must stay quiet")
        return 1
    print("probe: PASS")
    return 0


def main(argv=None):
    if os.environ.get("DRIVER_STALL_DEMO_PROBE") == "1":
        return demo_probe()
    ok = True
    for phase in (phase_detector, phase_equivalence, phase_demo,
                  phase_contract):
        if not phase():
            ok = False
    if not ok:
        print("driver_stall drill: FAIL")
        return 1
    print("driver_stall drill: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
