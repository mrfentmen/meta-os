"""intel/watchdog.py as a system service (Milo lane, OS-033).

The unit file's shape is guarded here, and the flag it passes
(--beat) is proven on a fake store: a service-mode tick renews
muse-bus:intel:wd:beat, and a tick without the flag writes
nothing — so a unit running the old flag-less CLI would never
show alive on the dashboard, which is exactly the gap OS-033
closes. Boot activation itself is NOT proven here: there is
no test image in this repo and relay-jobs.service (the unit
this one orders after) is not landed yet, so "active at boot"
and the stop-the-unit dashboard render stay owed on the test
image, and the unit file says so in its header.
"""

import io
import os
import subprocess
import sys
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
from intel import watchdog  # noqa: E402
from intel import store as istore  # noqa: E402


class WatchdogServiceUnitTest(unittest.TestCase):
    def _unit_text(self):
        path = os.path.join(os.path.dirname(__file__), "..",
                            "os", "services", "relay-watchdog.service")
        with open(path) as handle:
            return handle.read()

    def test_unit_is_simple_loop_after_jobs_with_beat(self):
        # OS-033 acceptance, unit half: a long-running loop (not
        # a oneshot), ordered after the queue service it reads,
        # restarting on failure, passing --beat so its ticks are
        # what the dashboard reads as alive.
        text = self._unit_text()
        self.assertIn("Type=simple", text)
        self.assertNotIn("Type=oneshot", text)
        self.assertIn("After=relay-jobs.service", text)
        self.assertIn("intel/watchdog.py --loop", text)
        self.assertIn("--beat", text)
        self.assertIn("User=relay", text)
        self.assertIn("WorkingDirectory=/opt/relay", text)
        self.assertIn("Restart=on-failure", text)
        self.assertIn("WantedBy=relay.target", text)

    def test_unit_header_names_its_proof_gaps(self):
        # The unit file must not let a reader mistake a file in
        # the repo for a booted service: boot activation and the
        # live-snapshot gap (FND-014) stay named in the header.
        text = self._unit_text()
        self.assertIn("NOT proven", text)
        self.assertIn("FND-014", text)
        self.assertIn("watchdog-silent", text)


class WatchdogServiceBeatTest(RelayTestCase):
    def test_once_with_beat_writes_beat_key(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = watchdog.main(["--once", "--beat"])
        self.assertEqual(code, 0)
        self.assertEqual(istore.wd_self_beat_age(int(self.fake.now())), 0)

    def test_once_without_beat_writes_no_beat(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = watchdog.main(["--once"])
        self.assertEqual(code, 0)
        self.assertIsNone(istore.wd_self_beat_age(int(self.fake.now())))

    def test_loop_with_beat_renews_on_every_tick(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = watchdog.main(["--loop", "--beat",
                                  "--interval", "0", "--max-ticks", "2"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().count("0 alert(s)"), 2)
        self.assertEqual(istore.wd_self_beat_age(int(self.fake.now())), 0)


class WatchdogDemoThresholdsDropinTest(unittest.TestCase):
    # OS-038: the demo thresholds profile (DEM-013) reaches the
    # demo image only through a unit drop-in, never by editing
    # the production unit or thresholds.py. The drop-in is env
    # only: no ExecStart, so the production command runs as
    # shipped, and build-image.sh installs it only under
    # METAOS_DEMO=1, so a production build never sees it.
    def _dropin_text(self):
        path = os.path.join(os.path.dirname(__file__), "..",
                            "os", "services",
                            "relay-watchdog.service.d",
                            "demo-thresholds.conf")
        with open(path) as handle:
            return handle.read()

    def test_dropin_is_env_only_pointing_at_image_profile(self):
        text = self._dropin_text()
        self.assertIn("[Service]", text)
        self.assertIn(
            "EnvironmentFile=/opt/relay/intel/metaos-demo.env", text)
        directives = [line.strip() for line in text.splitlines()
                      if line.strip()
                      and not line.strip().startswith("#")]
        self.assertFalse(
            [line for line in directives
             if line.startswith("ExecStart")],
            "drop-in must not override the production command")

    def test_production_unit_carries_no_environment_file(self):
        path = os.path.join(os.path.dirname(__file__), "..",
                            "os", "services", "relay-watchdog.service")
        with open(path) as handle:
            self.assertNotIn("EnvironmentFile", handle.read())

    def test_demo_profile_switches_stall_windows_only(self):
        # Same check as drill intel/drills/demo_thresholds_dropin.py
        # step 2, in-process here via a subprocess so the suite's
        # own thresholds module is never reloaded mid-run.
        env = dict(os.environ)
        env_path = os.path.join(os.path.dirname(__file__), "..",
                                "intel", "metaos-demo.env")
        with open(env_path) as handle:
            for line in handle:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    if key.strip().startswith("WATCHDOG_"):
                        env[key.strip()] = value.strip()
        code = ("import sys; sys.path.insert(0, '.'); "
                "from intel import thresholds; "
                "print(thresholds.STALL_MINUTES, "
                "thresholds.PROGRESS_STALL_MINUTES, "
                "thresholds.LEASE_RISK_WINDOW_MINUTES, "
                "thresholds.ALERT_DEDUPE_COOLDOWN_MINUTES)")
        proc = subprocess.run([sys.executable, "-c", code],
                              capture_output=True, text=True,
                              cwd=".", env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "1 1 5 30")

    def test_build_installs_dropin_only_for_demo_builds(self):
        path = os.path.join(os.path.dirname(__file__), "..",
                            "os", "build-image.sh")
        with open(path) as handle:
            text = handle.read()
        self.assertIn('METAOS_DEMO', text)
        self.assertIn("relay-watchdog.service.d/demo-thresholds.conf",
                      text)
        # The unconditional units install line must not mention
        # the drop-in: production builds stay drop-in free.
        for line in text.splitlines():
            if line.startswith("install -m 644 services/*.service"):
                self.assertNotIn("service.d", line)
