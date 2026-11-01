"""Driver tests for the META CUSTOS standing service (stage 2).

Run from the repo root:

    python3 -m unittest discover -s tests/custos -v

The driver (os/os/bin/metaos-custos, POSIX sh) is run against a
stub patrol command in a temp state dir. The claims pinned here are
the service's safety claims:

  * the STOP kill switch halts before anything runs;
  * one patrol at a time: a live lock blocks, a stale lock is stolen;
  * no config is a logged no-op — the driver never invents a host
    list and never calls the patrol unconfigured;
  * a configured run invokes the patrol with the records and
    seen-state paths under the state dir;
  * a patrol failure propagates its exit code and is logged.
"""

import os
import subprocess
import sys
import tempfile
import time
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DRIVER = os.path.join(REPO, "os", "os", "bin", "metaos-custos")


class DriverCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = self.tmp.name
        self.state = os.path.join(root, "state")
        self.calls = os.path.join(root, "patrol-calls.txt")
        self.stub = os.path.join(root, "patrol-stub")
        self.config = os.path.join(root, "custos.json")
        self.write_stub(0)

    def write_stub(self, exit_code):
        with open(self.stub, "w") as f:
            f.write("#!/bin/sh\n")
            f.write('echo "$@" >> "%s"\n' % self.calls)
            f.write('echo "patrol complete: stub" >&2\n')
            f.write("exit %d\n" % exit_code)
        os.chmod(self.stub, 0o755)

    def write_config(self):
        with open(self.config, "w") as f:
            f.write('{"hosts": [], "inventory": []}\n')

    def run_driver(self, **env_extra):
        env = dict(os.environ)
        env.update({
            "METAOS_CUSTOS_STATE": self.state,
            "METAOS_CUSTOS_CONFIG": self.config,
            "METAOS_CUSTOS_PATROL": self.stub,
        })
        env.update(env_extra)
        return subprocess.run(["sh", DRIVER], env=env,
                              capture_output=True, text=True, timeout=30)

    def log_text(self):
        path = os.path.join(self.state, "custos.log")
        if not os.path.isfile(path):
            return ""
        with open(path) as f:
            return f.read()

    def calls_text(self):
        if not os.path.isfile(self.calls):
            return ""
        with open(self.calls) as f:
            return f.read()


class TestDriver(DriverCase):
    def test_stop_file_halts_before_anything(self):
        os.makedirs(self.state)
        with open(os.path.join(self.state, "STOP"), "w") as f:
            f.write("")
        self.write_config()
        result = self.run_driver()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.calls_text(), "")
        self.assertIn("stopped", self.log_text())

    def test_missing_config_is_a_logged_noop(self):
        result = self.run_driver()
        self.assertEqual(result.returncode, 0)
        self.assertEqual(self.calls_text(), "")
        self.assertIn("not-configured", self.log_text())

    def test_configured_run_invokes_patrol_with_state_paths(self):
        self.write_config()
        result = self.run_driver()
        self.assertEqual(result.returncode, 0)
        calls = self.calls_text()
        self.assertIn("run --config %s" % self.config, calls)
        self.assertIn("--records %s" % os.path.join(
            self.state, "records.jsonl"), calls)
        self.assertIn("--state %s" % os.path.join(
            self.state, "seen.json"), calls)
        self.assertIn("patrol-ok", self.log_text())

    def test_live_lock_blocks(self):
        sleeper = subprocess.Popen(["sleep", "30"])
        try:
            lockdir = os.path.join(self.state, "lock")
            os.makedirs(lockdir)
            with open(os.path.join(lockdir, "pid"), "w") as f:
                f.write(str(sleeper.pid))
            self.write_config()
            result = self.run_driver()
            self.assertEqual(result.returncode, 1)
            self.assertEqual(self.calls_text(), "")
            self.assertIn("busy", self.log_text())
        finally:
            sleeper.kill()
            sleeper.wait()

    def test_stale_lock_is_stolen(self):
        dead = subprocess.Popen(["true"])
        dead.wait()
        lockdir = os.path.join(self.state, "lock")
        os.makedirs(lockdir)
        with open(os.path.join(lockdir, "pid"), "w") as f:
            f.write(str(dead.pid))
        self.write_config()
        result = self.run_driver()
        self.assertEqual(result.returncode, 0)
        self.assertIn("run --config", self.calls_text())

    def test_patrol_failure_propagates(self):
        self.write_stub(3)
        self.write_config()
        result = self.run_driver()
        self.assertEqual(result.returncode, 3)
        self.assertIn("patrol-failed", self.log_text())
        self.assertIn("exit 3", self.log_text())


if __name__ == "__main__":
    unittest.main()
