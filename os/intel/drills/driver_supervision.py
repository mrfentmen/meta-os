"""Driver-supervision drill (Milo lane, OS-056).

Acceptance: a driver process appears in the slice on the test image;
kill -9 restarts per the OS-034 contract with a watchdog event note
and no false stall alert.

What fixtures can prove, and what they cannot, stated plainly. The
slice half is provable here: the slice file parses with the spec
values (CPUQuota=100%, MemoryMax=1G, shared with the OS-035 worker
defaults until driver profiles are measured) and systemd-analyze
verify accepts it. The supervision half is provable at the detector
level: driver heartbeats feed the existing WDG stall detectors
unchanged, with no driver special-casing anywhere in
intel/watchdog.py. A driver nick in the caps registry, gone from
presence while holding a claimed job past the stall window, yields
exactly one presence-stall alert naming the driver nick and job,
severity critical, the same record shape a worker stall yields; and
the tick never mutates the job (it stays claimed), which is the
OS-034 split in code: the watchdog records, systemd restarts.

What this drill does NOT claim: a driver process appearing in this
slice on a booted test image (no test image in this repo, no driver
runner program exists yet for a template unit to start, and this
dev VM exposes no cpu or memory cgroup controller, so the
enforcement half is owed on the test image exactly as OS-035's was).
The kill -9 restart itself is systemd's job, not the watchdog's,
and is likewise owed on the test image. The wedge case (driver
alive, heartbeat stale) is OS-057's drill, not this one.

Runs unattended on fixtures: no network, no Redis, no bus posts.
Timeline uses a fake clock (base time T0) so the drill is
deterministic: thresholds are read from intel/thresholds.py,
never hardcoded, so a threshold retune retunes the drill.

Usage: python3 intel/drills/driver_supervision.py
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
SLICE = os.path.join(ROOT, "os", "services", "relay-drivers.slice")
WATCHDOG_SRC = os.path.join(ROOT, "intel", "watchdog.py")

EXPECTED = {"CPUQuota": "100%", "MemoryMax": "1G"}
DRIVER = "driver-audio"
WORKER = "pax"
T0 = 100000


def parse_slice(path):
    values = {}
    section = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
                continue
            if section == "Slice" and "=" in line:
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip()
    return values


def run(cmd, timeout=60):
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout)


def snapshot_for(present, driver_last_progress):
    """Caps carry a driver nick and a worker nick; presence is the
    caller's list. The driver holds one claimed job, the worker
    holds one claimed job, both with last progress at T0."""
    return {
        "caps": {DRIVER: {"caps": "audio"}, WORKER: {"caps": "python"}},
        "presence": list(present),
        "jobs": [
            {"id": "d1", "title": "play boot sting",
             "status": "claimed", "claim": DRIVER,
             "claimed_at": T0, "last_progress_at": driver_last_progress},
            {"id": "w1", "title": "write brief",
             "status": "claimed", "claim": WORKER,
             "claimed_at": T0, "last_progress_at": T0},
        ],
        "messages": [],
    }


def phase_file():
    values = parse_slice(SLICE)
    for key, want in EXPECTED.items():
        got = values.get(key)
        print(f"file: {key}={got} (expected {want})")
        if got != want:
            print(f"file: FAIL: {key} mismatch")
            return False
    print("file: PASS")
    return True


def phase_verify():
    proc = run(["systemd-analyze", "verify", SLICE])
    print(f"verify: exit={proc.returncode}")
    if proc.stdout.strip():
        print(f"verify: stdout: {proc.stdout.strip()}")
    if proc.stderr.strip():
        print(f"verify: stderr: {proc.stderr.strip()}")
    if proc.returncode != 0:
        print("verify: FAIL")
        return False
    print("verify: PASS")
    return True


def phase_detector():
    stall_at = T0 + thresholds.STALL_MINUTES * 60 + 1
    # Driver gone from presence, worker still present: exactly one
    # alert, and it names the driver, not the worker.
    snap = snapshot_for([WORKER], T0)
    alerts = watchdog.detect_presence_stall(snap, stall_at)
    if len(alerts) != 1:
        print(f"detector: FAIL: expected 1 alert, got {len(alerts)}")
        return False
    alert = alerts[0]
    if alert.get("kind") != "presence-stall":
        print(f"detector: FAIL: kind {alert.get('kind')}")
        return False
    if alert.get("nick") != DRIVER or alert.get("job") != "d1":
        print(f"detector: FAIL: alert names {alert.get('nick')}/"
              f"{alert.get('job')}, expected {DRIVER}/d1")
        return False
    if alert.get("severity") != "critical":
        print(f"detector: FAIL: severity {alert.get('severity')}")
        return False
    print(f"detector: driver stall names {DRIVER}/d1, severity "
          f"critical, age {alert['last_progress_age_minutes']}m: PASS")
    # Negative: driver present, same ages, yields nothing.
    snap = snapshot_for([DRIVER, WORKER], T0)
    if watchdog.detect_presence_stall(snap, stall_at) != []:
        print("detector: FAIL: present driver must yield no alert")
        return False
    print("detector: present driver yields no alert: PASS")
    # Negative: driver gone but still fresh yields nothing.
    snap = snapshot_for([WORKER], T0)
    if watchdog.detect_presence_stall(snap, T0 + 60) != []:
        print("detector: FAIL: fresh driver job must yield no alert")
        return False
    print("detector: fresh driver job yields no alert: PASS")
    # No driver special-casing in the detector source: the driver
    # fired through the same code path a worker fires through.
    with open(WATCHDOG_SRC) as f:
        src = f.read()
    if "driver" in src.lower():
        print("detector: FAIL: watchdog.py mentions drivers; the "
              "detector must be unchanged, not driver-aware")
        return False
    print("detector: watchdog.py has no driver special-casing: PASS")
    return True


def phase_contract():
    """The tick records but never mutates: after a full tick on the
    stalled-driver snapshot, the driver's job is still claimed, so
    no restart fight is possible from the watchdog side. systemd
    owns process death; the watchdog owns the alert."""
    stall_at = T0 + thresholds.STALL_MINUTES * 60 + 1
    snap = snapshot_for([WORKER], T0)
    alerts = watchdog.tick(snap, now=stall_at)
    driver_alerts = [a for a in alerts if a.get("nick") == DRIVER]
    if len(driver_alerts) != 1:
        print(f"contract: FAIL: expected 1 driver alert from tick, "
              f"got {len(driver_alerts)}")
        return False
    job = [j for j in snap["jobs"] if j["id"] == "d1"][0]
    if job.get("status") != "claimed" or job.get("claim") != DRIVER:
        print(f"contract: FAIL: tick mutated the job: {job}")
        return False
    print("contract: tick alerts but leaves job claimed with driver: "
          "PASS")
    return True


def main(argv=None):
    ok = True
    for phase in (phase_file, phase_verify, phase_detector,
                  phase_contract):
        if not phase():
            ok = False
    if not ok:
        print("driver_supervision drill: FAIL")
        return 1
    print("driver_supervision drill: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
