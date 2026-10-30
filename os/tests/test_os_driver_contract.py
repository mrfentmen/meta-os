"""tests/test_os_driver_contract.py -- OS-053: the driver contract.

Runs the os/drivers/CONFORMANCE.md checklist (C1-C10) against the
reference stub driver, plus pins the contract and checklist docs.

Real subprocesses, real temp workdirs, real snapshot diffs: no
network, no live Redis, no bus post, no systemd. The child commands
are plain python -c one-liners that write files or sleep.
"""

import importlib.util
import os
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, "os", "drivers", "stub_driver.py")
CONTRACT = os.path.join(ROOT, "os", "drivers", "CONTRACT.md")
CONFORMANCE = os.path.join(ROOT, "os", "drivers", "CONFORMANCE.md")


def load_driver():
    spec = importlib.util.spec_from_file_location("stub_driver", DRIVER)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


driver_mod = load_driver()
StubDriver = driver_mod.StubDriver


def spec(**over):
    base = {
        "id": "job-1",
        "title": "write the output file",
        "spec": "Create out.txt in the workdir.",
        "files": ["out.txt"],
        "accept": "file-exists: out.txt",
        "sig": "deadbeef",
    }
    base.update(over)
    return base


def write_cmd(path, text="hi"):
    return [sys.executable, "-c",
            "open(%r, 'w').write(%r)" % (path, text)]


class DriverContractTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = self.tmp.name
        self.driver = None

    def tearDown(self):
        try:
            if self.driver is not None and self.driver._proc is not None:
                if self.driver.poll() is None:
                    self.driver.stop()
                self.driver.artifacts()
        except Exception:
            pass
        self.tmp.cleanup()

    def started(self, sp=None, cmd=None):
        self.driver = StubDriver(self.workdir)
        self.driver.start(sp or spec(),
                          cmd or write_cmd("out.txt"))
        return self.driver

    def test_c1_unsigned_spec_rejected_and_nothing_spawns(self):
        unsigned = spec()
        del unsigned["sig"]
        for bad in (spec(sig=""), unsigned):
            d = StubDriver(self.workdir)
            with self.assertRaises(driver_mod.UnsignedSpecError):
                d.start(bad, write_cmd("out.txt"))
            self.assertIsNone(d._proc)

    def test_c2_unparseable_accept_rejected(self):
        d = StubDriver(self.workdir)
        with self.assertRaises(driver_mod.BadSpecError):
            d.start(spec(accept="nonsense without a colon"),
                    write_cmd("out.txt"))
        self.assertIsNone(d._proc)

    def test_c3_empty_files_rejected(self):
        d = StubDriver(self.workdir)
        with self.assertRaises(driver_mod.BadSpecError):
            d.start(spec(files=[]), write_cmd("out.txt"))
        self.assertIsNone(d._proc)

    def test_c4_heartbeat_shape_and_before_start(self):
        d = StubDriver(self.workdir)
        with self.assertRaises(driver_mod.NotStartedError):
            d.heartbeat("early")
        self.started()
        rec = self.driver.heartbeat("wrote the file")
        self.assertEqual(rec["line"], "PROGRESS:job-1 wrote the file")
        self.assertEqual(rec["job_id"], "job-1")
        self.assertEqual(rec["note"], "wrote the file")
        self.assertIsInstance(rec["ts"], float)
        self.assertIn(rec, self.driver.heartbeats)

    def test_c5_stop_kills_sleeping_child(self):
        d = StubDriver(self.workdir)
        d.start(spec(), [sys.executable, "-c",
                         "import time; time.sleep(60)"])
        self.driver = d
        time.sleep(0.2)
        self.assertIsNone(d.poll())
        d.stop()
        self.assertIsNotNone(d.poll())

    def test_c6_changed_files_lists_new_file_not_log(self):
        self.started()
        arts = self.driver.artifacts()
        self.assertIn("out.txt", arts["changed_files"])
        self.assertNotIn("driver.log", arts["changed_files"])
        self.assertEqual(arts["status"], "done")
        self.assertEqual(arts["exit_code"], 0)
        self.assertTrue(os.path.exists(arts["log"]))

    def test_c7_acceptance_from_disk_true_and_false(self):
        self.started()
        self.assertTrue(self.driver.artifacts()["acceptance"]["ok"])
        d = StubDriver(self.workdir)
        d.start(spec(accept="file-exists: missing.txt"),
                write_cmd("out.txt"))
        self.driver = d
        self.assertFalse(d.artifacts()["acceptance"]["ok"])

    def test_c8_unowned_changes_visible(self):
        d = StubDriver(self.workdir)
        d.start(spec(), write_cmd("stray.txt"))
        self.driver = d
        arts = d.artifacts()
        self.assertIn("stray.txt", arts["changed_files"])
        self.assertIn("stray.txt", arts["unowned_files"])

    def test_c9_stop_after_finish_safe_and_artifacts_stable(self):
        self.started()
        first = self.driver.artifacts()
        self.driver.stop()
        second = self.driver.artifacts()
        self.assertEqual(first, second)

    def test_c10_no_bus_or_redis_imports(self):
        with open(DRIVER, encoding="utf-8") as f:
            imports = [ln.strip() for ln in f
                       if ln.startswith("import ") or ln.startswith("from ")]
        for ln in imports:
            self.assertNotIn("redis", ln)
            self.assertNotIn("upstash", ln)
            self.assertNotIn("relay_common", ln)

    def test_start_twice_rejected_and_spec_defaults(self):
        self.started()
        with self.assertRaises(driver_mod.DriverError):
            self.driver.start(spec(), write_cmd("out.txt"))
        self.assertEqual(driver_mod.validate_spec(spec())["max_attempts"], 3)

    def test_docs_pin_contract_and_checklist(self):
        with open(CONTRACT, encoding="utf-8") as f:
            contract = f.read()
        for token in ("start(job_spec)", "stop()", "heartbeat()",
                      "artifacts()", "PROGRESS:", "mos/acceptance.py"):
            self.assertIn(token, contract)
        with open(CONFORMANCE, encoding="utf-8") as f:
            conformance = f.read()
        for item in ("C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8",
                     "C9", "C10"):
            self.assertIn(item, conformance)
        for path in (CONTRACT, CONFORMANCE):
            with open(path, encoding="utf-8") as f:
                self.assertNotIn("\u2014", f.read(),
                                 "%s must stay em dash free" % path)
        with open(os.path.join(ROOT, "os", "README.md"),
                  encoding="utf-8") as f:
            self.assertIn("OS-053", f.read())
        with open(os.path.join(ROOT, "plan", "META_OS.md"),
                  encoding="utf-8") as f:
            self.assertIn("OS-053", f.read())


if __name__ == "__main__":
    unittest.main()
