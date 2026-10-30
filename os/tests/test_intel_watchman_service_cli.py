"""OS-122 follow-up: the unit's command runs as a process.

The service loop was proven in-process and the unit file as
a shape, but the command the unit execs had never run: as a
plain script it failed at import time (Python puts intel/
first on sys.path, not the repo root). These tests run the
real CLI as a subprocess with PYTHONPATH removed, so no
environment variable is load-bearing.
"""

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SERVICE = os.path.join(ROOT, "intel", "watchman_service.py")
UNIT = os.path.join(ROOT, "os", "services",
                    "relay-watchman-watch.service")
DRILL = os.path.join(ROOT, "intel", "drills",
                     "watchman_service_cli.py")
NEW_FILES = (SERVICE, DRILL,
             os.path.join(ROOT, "intel", "evals",
                          "watchman_service_cli.md"),
             __file__)


def _clean_env():
    env = dict(os.environ)
    env.pop("PYTHONPATH", None)
    return env


def _fixture_dir():
    tmp = tempfile.mkdtemp(prefix="watchman-service-cli-test-")
    jobs = [{"id": "j1", "status": "open", "addressed_to": "hana",
             "title": "Write the brief"}]
    agents = {"hana": {"nick": "hana", "heartbeat_at": None}}
    for name, value in (("jobs", jobs), ("agents", agents)):
        with open(os.path.join(
                tmp, "watchman-%s-alpha.json" % name),
                "w", encoding="utf-8") as handle:
            json.dump(value, handle)
    return tmp


def _run(argv):
    return subprocess.run(argv, capture_output=True, text=True,
                          timeout=120, cwd=ROOT, env=_clean_env())


class CliTest(unittest.TestCase):
    def test_plain_command_runs_without_pythonpath(self):
        tmp = _fixture_dir()
        proc = _run([sys.executable, SERVICE, "--machines", "alpha",
                     "--cycles", "2", "--interval", "0",
                     "--snapshot-dir", tmp])
        self.assertEqual(proc.returncode, 0,
                         proc.stdout + proc.stderr)
        self.assertEqual(proc.stdout.count("cycle "), 2)
        self.assertIn("service loop stopped after 2 cycles",
                      proc.stdout)

    def test_empty_machines_cycles_empty(self):
        tmp = _fixture_dir()
        proc = _run([sys.executable, SERVICE, "--machines", "",
                     "--cycles", "1", "--interval", "0",
                     "--snapshot-dir", tmp])
        self.assertEqual(proc.returncode, 0,
                         proc.stdout + proc.stderr)
        self.assertIn("cycle 0: 0 machines", proc.stdout)

    def test_bare_machines_flag_cycles_empty(self):
        # The unit's ExecStart with no env file: systemd expands
        # an unset ${WATCHMAN_WATCH_MACHINES} to nothing, leaving
        # a bare --machines before --snapshot-dir. That shape
        # must cycle empty, not fail argparse with exit 2.
        tmp = _fixture_dir()
        proc = _run([sys.executable, SERVICE, "--machines",
                     "--snapshot-dir", tmp,
                     "--cycles", "1", "--interval", "0"])
        self.assertEqual(proc.returncode, 0,
                         proc.stdout + proc.stderr)
        self.assertIn("cycle 0: 0 machines", proc.stdout)

    def test_unit_execstart_runs(self):
        tmp = _fixture_dir()
        with open(UNIT, encoding="utf-8") as handle:
            unit_text = handle.read()
        match = re.search(r"^ExecStart=(.+)$", unit_text, re.MULTILINE)
        self.assertIsNotNone(match, "no ExecStart line in unit file")
        command = match.group(1).strip()
        command = command.replace("/opt/relay", ROOT)
        command = command.replace("${WATCHMAN_WATCH_MACHINES}",
                                  "alpha")
        command = command.replace("/run/metaos", tmp)
        proc = _run(command.split()
                    + ["--cycles", "1", "--interval", "0"])
        self.assertEqual(proc.returncode, 0,
                         proc.stdout + proc.stderr)
        self.assertIn("cycle 0: 1 machines", proc.stdout)

    def test_drill_passes(self):
        proc = _run([sys.executable, DRILL])
        self.assertEqual(proc.returncode, 0,
                         proc.stdout + proc.stderr)
        self.assertIn("ALL PASS", proc.stdout)

    def test_no_em_dash_in_new_files(self):
        for path in NEW_FILES:
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("\u2014", handle.read(), path)


if __name__ == "__main__":
    unittest.main()
