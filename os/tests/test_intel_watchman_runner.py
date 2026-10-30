"""tests/test_intel_watchman_runner.py -- OS-122 follow-up.

Pins intel/watchman_runner.py: the real subprocess runner
that runs Pax OS-118 relay_watchman.py --once once per
machine and turns each result into the (ok, stdout) pair
run_cycle() expects. Only exit 0 counts as success, a
failed run's stdout is discarded, timeouts and missing
programs are failed runs, and the runner never raises.

- Default argv shape: python + the repo program + --once,
  with per-machine jobs/agents/state filenames under the
  snapshot directory, distinct per machine.
- run_once() success returns the real stdout; nonzero
  exit, timeout, missing program, and bad argv all yield
  (False, "", detail) with the right detail, and a nonzero
  exit's partial stdout never survives.
- The runner never raises for a bad machine name, a bad
  argv, or a raising command_for.
- run_cycle_with_subprocess() over real snapshot files
  rings the ringing machine and invents no bell for the
  quiet machine, with clean diagnostics.
- A failed run carries the prior bell forward with
  restart_ok stripped, and priors/journal are unchanged.
- The drill script exists and passes; the eval note
  names OS-122.
- None of the new OS-122 runner files carries an em dash
  (the new-doc rule).

No bus post, no live Redis, no network, no systemd:
subprocess runs of the repo program and fixture scripts
in temp directories only.
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from intel import watchman_runner as runner  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAM = os.path.join(ROOT, "os", "watchman", "relay_watchman.py")
NOW = 1000000
NEW_FILES = [
    "intel/watchman_runner.py",
    "intel/drills/watchman_runner.py",
    "intel/evals/watchman_runner.md",
    "intel/evals/watchman_runner.log",
    "tests/test_intel_watchman_runner.py",
]


def _write_json(path, value):
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(value, handle)


def _snapshots(directory, machine, jobs, agents):
    _write_json(os.path.join(
        directory, "watchman-jobs-%s.json" % machine), jobs)
    _write_json(os.path.join(
        directory, "watchman-agents-%s.json" % machine), agents)


class TestMachineArgv(unittest.TestCase):
    def test_default_argv_shape(self):
        argv = runner.machine_argv("alpha", snapshot_dir="/run/metaos")
        self.assertEqual(argv[0], sys.executable)
        self.assertEqual(argv[1], PROGRAM)
        self.assertEqual(argv[2], "--once")
        self.assertIn("/run/metaos/watchman-jobs-alpha.json", argv)
        self.assertIn("/run/metaos/watchman-agents-alpha.json", argv)
        self.assertIn("/run/metaos/watchman-state-alpha.json", argv)
        self.assertTrue(os.path.exists(PROGRAM))

    def test_argv_distinct_per_machine(self):
        alpha = runner.machine_argv("alpha", snapshot_dir="/tmp/snap")
        beta = runner.machine_argv("beta", snapshot_dir="/tmp/snap")
        self.assertNotEqual(alpha, beta)
        self.assertNotIn("alpha", " ".join(beta))

    def test_bad_machine_yields_none(self):
        self.assertIsNone(runner.machine_argv(""))
        self.assertIsNone(runner.machine_argv(None))
        self.assertIsNone(runner.machine_argv(7))


class TestRunOnce(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="watchman-runner-test-")

    def _script(self, name, body):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(body)
        return path

    def test_success_returns_stdout(self):
        script = self._script("ok.py", "print('hello')\n")
        ok, stdout, detail = runner.run_once([sys.executable, script])
        self.assertEqual((ok, stdout.strip(), detail),
                         (True, "hello", None))

    def test_nonzero_discards_partial_stdout(self):
        script = self._script(
            "partial.py",
            "import sys\nprint('partial')\nsys.exit(3)\n")
        ok, stdout, detail = runner.run_once([sys.executable, script])
        self.assertEqual((ok, stdout, detail), (False, "", "exit-3"))

    def test_timeout(self):
        script = self._script("sleepy.py", "import time\ntime.sleep(30)\n")
        ok, stdout, detail = runner.run_once(
            [sys.executable, script], timeout_seconds=1)
        self.assertEqual((ok, stdout, detail), (False, "", "timeout"))

    def test_not_found(self):
        ok, stdout, detail = runner.run_once(
            [os.path.join(self.tmp, "no-such-program")])
        self.assertEqual((ok, detail), (False, "not-found"))

    def test_bad_argv(self):
        self.assertEqual(runner.run_once([]), (False, "", "bad-argv"))
        self.assertEqual(runner.run_once([sys.executable, 7]),
                         (False, "", "bad-argv"))
        self.assertEqual(runner.run_once(None), (False, "", "bad-argv"))


class TestSubprocessRunner(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="watchman-runner-test-")

    def test_runner_never_raises(self):
        plain = runner.make_subprocess_runner(snapshot_dir=self.tmp)
        self.assertEqual(plain(""), (False, ""))
        self.assertEqual(plain(None), (False, ""))

        def _raising(name):
            raise RuntimeError("boom")

        self.assertEqual(
            runner.make_subprocess_runner(command_for=_raising)("alpha"),
            (False, ""))

    def test_real_cycle_rings_and_stays_quiet(self):
        jobs = [{"id": "j1", "status": "open",
                 "addressed_to": "hana", "title": "Write the brief"}]
        agents = {"hana": {"nick": "hana", "heartbeat_at": None}}
        _snapshots(self.tmp, "alpha", jobs, agents)
        _snapshots(self.tmp, "beta", [], {})
        records, new_journal, diagnostics = \
            runner.run_cycle_with_subprocess(
                ["alpha", "beta"], NOW, priors={}, journal=[],
                snapshot_dir=self.tmp)
        self.assertTrue(records["alpha"]["watchman_alive"])
        self.assertIsNotNone(records["alpha"]["last_bell"])
        self.assertIsNone(records["beta"]["last_bell"])
        self.assertEqual(new_journal, [])
        self.assertEqual(diagnostics["run_failures"], [])

    def test_failed_run_carries_prior_bell_stripped(self):
        prior = {"watchman_alive": True, "last_tick": NOW - 1000,
                 "last_bell": NOW - 1000, "last_wake": NOW - 1000,
                 "restart_ok": True}
        priors = {"alpha": prior}
        journal = []
        priors_before = copy.deepcopy(priors)
        records, _new, diagnostics = \
            runner.run_cycle_with_subprocess(
                ["alpha"], NOW, priors=priors, journal=journal,
                command_for=lambda name: (_ for _ in ()).throw(
                    RuntimeError("boom")))
        # The runner contains the raising command_for, so the
        # cycle sees a plain failed run, not an exception.
        self.assertEqual(records["alpha"]["last_bell"], NOW - 1000)
        self.assertNotIn("restart_ok", records["alpha"])
        self.assertIn("alpha", diagnostics["run_failures"])
        self.assertEqual(priors, priors_before)
        self.assertEqual(journal, [])

    def test_missing_snapshots_are_quiet_not_failed(self):
        records, _new, diagnostics = \
            runner.run_cycle_with_subprocess(
                ["ghost"], NOW, priors={}, journal=[],
                snapshot_dir=self.tmp)
        self.assertEqual(diagnostics["run_failures"], [])
        self.assertIsNone(records["ghost"]["last_bell"])


class TestDrillAndDocs(unittest.TestCase):
    def test_drill_passes(self):
        proc = subprocess.run(
            [sys.executable,
             os.path.join(ROOT, "intel", "drills", "watchman_runner.py")],
            capture_output=True, text=True, timeout=120)
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("ALL PASS (6 phases)", proc.stdout)

    def test_no_em_dash_in_new_files(self):
        for rel in NEW_FILES:
            with open(os.path.join(ROOT, rel),
                      encoding="utf-8") as handle:
                self.assertNotIn("\u2014", handle.read(), rel)


if __name__ == "__main__":
    unittest.main()
