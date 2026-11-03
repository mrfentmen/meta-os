"""Fixture test for watchdog.sh: static + live-process, no VM, no network.

Supervises `sleep` snippets in tmp: dead (kill -9) restarts, hung (false
health) restarts, cap writes BLOCKED + exit 2, clean exit 0 propagates.
Subprocess sh only; stdlib only. Interval 1s keeps the suite fast.
"""
import os
import shutil
import signal
import subprocess
import tempfile
import time
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_SCRIPT = os.path.join(_REPO, "agent-layer", "watchdog.sh")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class TestWatchdog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oc2-watchdog-")
        self.logdir = os.path.join(self.tmp, "state")
        os.mkdir(self.logdir)
        self.pidfile = os.path.join(self.tmp, "svc.pid")
        self.kids = []

    def tearDown(self):
        for pid in self.kids:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass
        # Reap service shells by pidfile as well (exec'd sleep keeps pid).
        try:
            with open(self.pidfile, encoding="utf-8") as fh:
                os.kill(int(fh.read().strip()), signal.SIGKILL)
        except OSError:
            pass
        except IOError:
            pass
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _start(self):
        return ("echo $$ > %s; exec sleep 60" % self.pidfile)

    def _wait_pidfile(self, timeout=10):
        end = time.time() + timeout
        while time.time() < end:
            if os.path.exists(self.pidfile):
                with open(self.pidfile, encoding="utf-8") as fh:
                    try:
                        return int(fh.read().strip())
                    except ValueError:
                        pass
            time.sleep(0.2)
        self.fail("service pidfile never appeared")

    def test_syntax_ok(self):
        r = subprocess.run(["sh", "-n", _SCRIPT],
                           capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_dead_restart_then_cap_blocked(self):
        w = subprocess.Popen(
            ["sh", _SCRIPT, "svc", self._start(), "", "1", "1", self.logdir],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.kids.append(w.pid)
        try:
            pid1 = self._wait_pidfile()
            os.kill(pid1, signal.SIGKILL)
            # Wait for restart (new pid) then kill again to hit cap.
            end = time.time() + 15
            pid2 = None
            while time.time() < end:
                time.sleep(0.5)
                try:
                    with open(self.pidfile, encoding="utf-8") as fh:
                        cur = int(fh.read().strip())
                    if cur != pid1:
                        pid2 = cur
                        break
                except (IOError, ValueError):
                    pass
            self.assertIsNotNone(pid2, "watchdog never restarted dead service")
            log = _read(os.path.join(self.logdir, "svc.log"))
            self.assertIn("cause=dead-exit-", log)
            os.kill(pid2, signal.SIGKILL)
            rc = w.wait(timeout=20)
            self.assertEqual(rc, 2)
            self.assertTrue(os.path.exists(
                os.path.join(self.logdir, "svc.blocked")))
        finally:
            if w.poll() is None:
                w.kill()

    def test_hung_restart_then_cap_blocked(self):
        w = subprocess.Popen(
            ["sh", _SCRIPT, "svc", self._start(), "false", "1", "1",
             self.logdir],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.kids.append(w.pid)
        try:
            rc = w.wait(timeout=25)
            self.assertEqual(rc, 2)
            log = _read(os.path.join(self.logdir, "svc.log"))
            self.assertIn("cause=hung-health-fail", log)
            self.assertTrue(os.path.exists(
                os.path.join(self.logdir, "svc.blocked")))
        finally:
            if w.poll() is None:
                w.kill()

    def test_clean_exit_propagates(self):
        r = subprocess.run(
            ["sh", _SCRIPT, "svc", "exit 0", "", "3", "1", self.logdir],
            capture_output=True, text=True, timeout=20)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertFalse(os.path.exists(
            os.path.join(self.logdir, "svc.blocked")))
        log = _read(os.path.join(self.logdir, "svc.log"))
        self.assertIn("clean, no restart", log)


if __name__ == "__main__":
    unittest.main()
