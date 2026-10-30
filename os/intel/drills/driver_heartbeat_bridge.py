"""Driver heartbeat bridge drill (Milo lane, OS-056 follow-up to Pax OS-054).

OS-054 landed the thing OS-056 was waiting on: a real driver program
(os/drivers/muse_driver.py) and a per-driver template unit
(os/services/relay-driver@.service). This drill closes the bridge
between them and the watchdog, on fixtures, in four checks:

1. Template: relay-driver@.service joins relay-drivers.slice, and
   systemd-analyze verify accepts the template and the slice.
2. Driver: a real MuseDriver run against a fixture stand-in
   executable emits heartbeat records in the contract shape: a
   line "PROGRESS:<job_id> <note>", the job id, and a numeric ts.
3. Bridge: a heartbeat record maps onto the watchdog snapshot by
   one rule only, the heartbeat ts becomes the job's
   last_progress_at. A fresh heartbeat yields no stall alert; a
   stale heartbeat with the driver nick present yields exactly one
   progress-stall alert and no presence-stall; the same stale
   heartbeat with the nick absent yields exactly one
   presence-stall and no progress-stall. The detectors are the
   unchanged WDG-002/WDG-003 code, so a driver stall reads exactly
   like a worker stall.
4. Contract: a full tick alerts but leaves the job claimed, the
   OS-034 split, and intel/watchdog.py still mentions no drivers,
   so no driver special-casing crept in with the bridge.

What this drill does NOT claim, stated plainly. The heartbeat
updates progress age only; it does not put the driver nick in
presence, so a driver that heartbeats but never registers
presence still reads as a presence-stall, not a progress-stall,
when its heartbeat goes stale. Presence registration for driver
nicks is the overseer handoff's job (OS-055), not the driver's.
A live driver run against a real muse binary, a driver process
actually appearing in the slice on a booted test image, live
cgroup enforcement, and the kill -9 systemd restart all remain
owed on the test image, exactly as OS-054 and OS-056 recorded.
No bus post, no live Redis, no network.

Runs unattended: python3 intel/drills/driver_heartbeat_bridge.py
Exit 0 with a PASS line per phase on success, 1 on failure.
"""

import importlib.util
import os
import stat
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))

from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))
TEMPLATE = os.path.join(ROOT, "os", "services", "relay-driver@.service")
SLICE = os.path.join(ROOT, "os", "services", "relay-drivers.slice")
DRIVER_PATH = os.path.join(ROOT, "os", "drivers", "muse_driver.py")
WATCHDOG_SRC = os.path.join(ROOT, "intel", "watchdog.py")

DRIVER = "driver-audio"
JOB = "d1"

STANDIN = """#!/usr/bin/env python3
import sys
print("working on the job")
sys.stdout.flush()
"""


def load_driver():
    spec = importlib.util.spec_from_file_location(
        "muse_driver_bridge", DRIVER_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def parse_section(path, section_name):
    values = {}
    section = None
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line.startswith("[") and line.endswith("]"):
                section = line[1:-1]
                continue
            if section == section_name and "=" in line:
                key, val = line.split("=", 1)
                values[key.strip()] = val.strip()
    return values


def apply_heartbeat(job, record):
    """The bridge rule, in one line: a driver heartbeat's ts is the
    job's last progress time. Returns a new job dict; the caller's
    job is never mutated, so a bad record cannot rewrite history
    in place."""
    out = dict(job)
    out["last_progress_at"] = int(record["ts"])
    return out


def snapshot_for(present, last_progress_at):
    return {
        "caps": {DRIVER: {"caps": "audio"}},
        "presence": list(present),
        "jobs": [{"id": JOB, "title": "play boot sting",
                  "status": "claimed", "claim": DRIVER,
                  "claimed_at": last_progress_at,
                  "last_progress_at": last_progress_at}],
        "messages": [],
    }


def phase_template():
    service = parse_section(TEMPLATE, "Service")
    got = service.get("Slice")
    print("template: Slice=%s (expected relay-drivers.slice)" % got)
    if got != "relay-drivers.slice":
        print("template: FAIL: template does not join the driver slice")
        return False
    slice_vals = parse_section(SLICE, "Slice")
    for key, want in (("CPUQuota", "100%"), ("MemoryMax", "1G")):
        if slice_vals.get(key) != want:
            print("template: FAIL: slice %s=%s, expected %s"
                  % (key, slice_vals.get(key), want))
            return False
    print("template: slice values CPUQuota=100%, MemoryMax=1G: PASS")
    proc = subprocess.run(["systemd-analyze", "verify", TEMPLATE, SLICE],
                          capture_output=True, text=True, timeout=60)
    print("template: systemd-analyze verify exit=%d" % proc.returncode)
    if proc.returncode != 0:
        print("template: FAIL: verify failed: %s" % proc.stderr.strip())
        return False
    print("template: PASS")
    return True


def phase_driver():
    mod = load_driver()
    tmp = tempfile.TemporaryDirectory()
    workdir = tmp.name
    standin_path = os.path.join(workdir, "fake-muse")
    with open(standin_path, "w") as f:
        f.write(STANDIN)
    os.chmod(standin_path, 0o755)
    driver = mod.MuseDriver(workdir, muse_binary=standin_path)
    spec = {"id": JOB, "title": "play boot sting",
            "spec": "Play the boot sting.",
            "files": ["sting.mp3"],
            "accept": "file-exists: sting.mp3",
            "sig": "deadbeef"}
    try:
        driver.start(spec)
        deadline = time.time() + 5
        while not driver.heartbeats and time.time() < deadline:
            time.sleep(0.05)
        manual = driver.heartbeat("manual note")
    finally:
        try:
            driver.stop()
        except Exception:
            pass
    # heartbeat() already appends through the sink, so the list
    # itself is the record set; do not append manual a second time.
    records = list(driver.heartbeats)
    if manual not in records:
        print("driver: FAIL: manual heartbeat missing from sink")
        return False
    if not records:
        print("driver: FAIL: no heartbeat records at all")
        return False
    for record in records:
        line = record.get("line", "")
        if not line.startswith("PROGRESS:%s " % JOB):
            print("driver: FAIL: bad line %r" % line)
            return False
        if record.get("job_id") != JOB:
            print("driver: FAIL: bad job_id %r" % record.get("job_id"))
            return False
        ts = record.get("ts")
        if not isinstance(ts, (int, float)):
            print("driver: FAIL: ts not numeric: %r" % (ts,))
            return False
    print("driver: %d records, line PROGRESS:%s <note>, "
          "job_id and numeric ts: PASS" % (len(records), JOB))
    return records


def phase_bridge(records):
    base_job = {"id": JOB, "title": "play boot sting",
                "status": "claimed", "claim": DRIVER}
    bridged = apply_heartbeat(base_job, records[0])
    if bridged["last_progress_at"] != int(records[0]["ts"]):
        print("bridge: FAIL: last_progress_at not the heartbeat ts")
        return False
    if "last_progress_at" in base_job:
        print("bridge: FAIL: apply_heartbeat mutated its input job")
        return False
    print("bridge: heartbeat ts becomes last_progress_at, "
          "input untouched: PASS")
    now = int(records[0]["ts"])
    fresh = snapshot_for([DRIVER], now - 30)
    if (watchdog.detect_presence_stall(fresh, now)
            or watchdog.detect_progress_stall(fresh, now)):
        print("bridge: FAIL: fresh heartbeat must yield no stall alert")
        return False
    print("bridge: fresh heartbeat yields no stall alert: PASS")
    stale_at = now - thresholds.PROGRESS_STALL_MINUTES * 60 - 1
    stale_present = snapshot_for([DRIVER], stale_at)
    progress = watchdog.detect_progress_stall(stale_present, now)
    presence = watchdog.detect_presence_stall(stale_present, now)
    if len(progress) != 1 or progress[0].get("kind") != "progress-stall":
        print("bridge: FAIL: stale present heartbeat must yield exactly "
              "one progress-stall, got %r" % (progress,))
        return False
    if presence:
        print("bridge: FAIL: stale present heartbeat must not also "
              "yield presence-stall")
        return False
    print("bridge: stale present heartbeat yields exactly one "
          "progress-stall naming %s/%s: PASS"
          % (progress[0].get("nick"), progress[0].get("job")))
    stale_absent = snapshot_for([], stale_at)
    presence = watchdog.detect_presence_stall(stale_absent, now)
    progress = watchdog.detect_progress_stall(stale_absent, now)
    if len(presence) != 1 or presence[0].get("kind") != "presence-stall":
        print("bridge: FAIL: stale absent heartbeat must yield exactly "
              "one presence-stall, got %r" % (presence,))
        return False
    if progress:
        print("bridge: FAIL: stale absent heartbeat must not also "
              "yield progress-stall")
        return False
    print("bridge: stale absent heartbeat yields exactly one "
          "presence-stall: PASS")
    return True


def phase_contract(records):
    now = int(records[0]["ts"])
    stale_at = now - thresholds.PROGRESS_STALL_MINUTES * 60 - 1
    snap = snapshot_for([DRIVER], stale_at)
    alerts = watchdog.tick(snap, now=now)
    driver_alerts = [a for a in alerts if a.get("nick") == DRIVER]
    if len(driver_alerts) != 1:
        print("contract: FAIL: expected 1 driver alert from tick, "
              "got %d" % len(driver_alerts))
        return False
    job = snap["jobs"][0]
    if job.get("status") != "claimed" or job.get("claim") != DRIVER:
        print("contract: FAIL: tick mutated the job: %r" % (job,))
        return False
    print("contract: tick alerts but leaves job claimed: PASS")
    with open(WATCHDOG_SRC) as f:
        src = f.read()
    if "driver" in src.lower():
        print("contract: FAIL: watchdog.py mentions drivers")
        return False
    print("contract: watchdog.py has no driver special-casing: PASS")
    return True


def main(argv=None):
    ok = True
    if not phase_template():
        ok = False
    records = phase_driver()
    if not records:
        ok = False
    else:
        if not phase_bridge(records):
            ok = False
        if not phase_contract(records):
            ok = False
    print("driver_heartbeat_bridge drill: %s" % ("PASS" if ok else "FAIL"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
