"""tests/test_intel_driver_heartbeat_bridge.py -- OS-056 follow-up.

Pax OS-054 landed the driver program and template unit OS-056 was
waiting on, so this pins the bridge from that driver to the
watchdog detectors, on fixtures only:

- os/services/relay-driver@.service joins relay-drivers.slice in
  its [Service] section.
- A real MuseDriver run against a fixture stand-in emits
  heartbeat records shaped PROGRESS:<job_id> <note> with a numeric
  ts and the matching job_id.
- The bridge rule maps a heartbeat ts onto a job's
  last_progress_at without mutating the input job.
- Fresh heartbeat: no stall alert. Stale heartbeat, nick
  present: exactly one progress-stall, no presence-stall. Stale
  heartbeat, nick absent: exactly one presence-stall, no
  progress-stall.
- A full tick alerts but leaves the job claimed (OS-034), and
  intel/watchdog.py mentions no drivers.
- None of the new files carries an em dash.

No bus post, no live Redis, no network, no live muse binary, no
booted image: the driver runs against a stand-in executable, and
the image-level halves (a process in the slice, live cgroup
enforcement, the kill -9 restart) stay owed on the test image.
"""

import importlib.util
import os
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")

from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEMPLATE = os.path.join(ROOT, "os", "services", "relay-driver@.service")
DRILL = os.path.join(ROOT, "intel", "drills", "driver_heartbeat_bridge.py")
EVAL = os.path.join(ROOT, "intel", "evals", "driver_heartbeat_bridge.md")
WATCHDOG_SRC = os.path.join(ROOT, "intel", "watchdog.py")
DRIVER_PATH = os.path.join(ROOT, "os", "drivers", "muse_driver.py")

DRIVER = "driver-audio"
JOB = "d1"

STANDIN = "#!/usr/bin/env python3\nprint('working on the job')\n"


def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()


def section_values(text, section_name):
    values = {}
    section = None
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("[") and line.endswith("]"):
            section = line[1:-1]
            continue
        if section == section_name and "=" in line:
            key, val = line.split("=", 1)
            values[key.strip()] = val.strip()
    return values


def load_drill():
    spec = importlib.util.spec_from_file_location(
        "driver_heartbeat_bridge", DRILL)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


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


class DriverHeartbeatBridgeTest(unittest.TestCase):
    def test_template_joins_driver_slice(self):
        values = section_values(read(TEMPLATE), "Service")
        self.assertEqual(values.get("Slice"), "relay-drivers.slice")

    def test_drill_and_eval_exist(self):
        self.assertTrue(os.path.isfile(DRILL))
        self.assertTrue(os.path.isfile(EVAL))

    def test_no_em_dash_in_new_files(self):
        for path in (DRILL, EVAL, __file__):
            self.assertNotIn("\u2014", read(path), path)

    def test_driver_heartbeat_shape(self):
        spec = importlib.util.spec_from_file_location(
            "muse_driver_bridge_test", DRIVER_PATH)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        with tempfile.TemporaryDirectory() as workdir:
            standin = os.path.join(workdir, "fake-muse")
            with open(standin, "w") as f:
                f.write(STANDIN)
            os.chmod(standin, 0o755)
            driver = mod.MuseDriver(workdir, muse_binary=standin)
            driver.start({"id": JOB, "title": "play boot sting",
                          "spec": "Play the boot sting.",
                          "files": ["sting.mp3"],
                          "accept": "file-exists: sting.mp3",
                          "sig": "deadbeef"})
            try:
                deadline = time.time() + 5
                while not driver.heartbeats and time.time() < deadline:
                    time.sleep(0.05)
            finally:
                driver.stop()
        self.assertTrue(driver.heartbeats)
        for record in driver.heartbeats:
            self.assertTrue(record["line"].startswith(
                "PROGRESS:%s " % JOB))
            self.assertEqual(record["job_id"], JOB)
            self.assertIsInstance(record["ts"], (int, float))

    def test_bridge_mapping_does_not_mutate(self):
        drill = load_drill()
        job = {"id": JOB, "status": "claimed", "claim": DRIVER}
        out = drill.apply_heartbeat(job, {"ts": 1234567.9})
        self.assertEqual(out["last_progress_at"], 1234567)
        self.assertNotIn("last_progress_at", job)

    def test_fresh_heartbeat_no_alert(self):
        now = 200000
        snap = snapshot_for([DRIVER], now - 30)
        self.assertEqual(watchdog.detect_presence_stall(snap, now), [])
        self.assertEqual(watchdog.detect_progress_stall(snap, now), [])

    def test_stale_present_is_progress_stall_only(self):
        now = 200000
        stale = now - thresholds.PROGRESS_STALL_MINUTES * 60 - 1
        snap = snapshot_for([DRIVER], stale)
        progress = watchdog.detect_progress_stall(snap, now)
        self.assertEqual(len(progress), 1)
        self.assertEqual(progress[0]["kind"], "progress-stall")
        self.assertEqual(progress[0]["nick"], DRIVER)
        self.assertEqual(progress[0]["job"], JOB)
        self.assertEqual(watchdog.detect_presence_stall(snap, now), [])

    def test_stale_absent_is_presence_stall_only(self):
        now = 200000
        stale = now - thresholds.STALL_MINUTES * 60 - 1
        snap = snapshot_for([], stale)
        presence = watchdog.detect_presence_stall(snap, now)
        self.assertEqual(len(presence), 1)
        self.assertEqual(presence[0]["kind"], "presence-stall")
        self.assertEqual(watchdog.detect_progress_stall(snap, now), [])

    def test_tick_leaves_job_claimed(self):
        now = 200000
        stale = now - thresholds.PROGRESS_STALL_MINUTES * 60 - 1
        snap = snapshot_for([DRIVER], stale)
        alerts = watchdog.tick(snap, now=now)
        driver_alerts = [a for a in alerts if a.get("nick") == DRIVER]
        self.assertEqual(len(driver_alerts), 1)
        self.assertEqual(snap["jobs"][0]["status"], "claimed")

    def test_watchdog_has_no_driver_special_casing(self):
        self.assertNotIn("driver", read(WATCHDOG_SRC).lower())


if __name__ == "__main__":
    unittest.main()
