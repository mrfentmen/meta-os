"""tests/test_os_driver_muse.py -- OS-054: the Muse Code driver.

Runs the os/drivers/CONFORMANCE.md checklist (C1-C10) against
muse_driver.MuseDriver, plus the OS-054 specifics: the prompt
built from a spec (no signature in it), the argv shape
(binary, exec, --prompt-file), child output streamed into
heartbeat records, a missing binary refused before spawning,
and one fixture job end to end through the driver.

No real `muse` binary exists on this machine, so the binary
under test is a fixture stand-in script: it reads its
--prompt-file argument, prints progress lines, and writes the
owned file. The stand-in proves the driver mechanics against a
real child process; it does not prove a live Muse Code run, and
no test here claims one. No network, no live Redis, no bus post.
"""

import importlib.util
import json
import os
import stat
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DRIVER = os.path.join(ROOT, "os", "drivers", "muse_driver.py")
RUNNER = os.path.join(ROOT, "os", "drivers", "run_driver.py")


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


driver_mod = load("muse_driver", DRIVER)


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


WRITER = """#!/usr/bin/env python3
import sys
prompt = None
args = sys.argv[1:]
for i, a in enumerate(args):
    if a == "--prompt-file":
        prompt = args[i + 1]
print("starting job from prompt file")
print("prompt file seen: %s" % bool(prompt))
with open("out.txt", "w") as f:
    f.write("hi\\n")
print("wrote out.txt")
"""

SLEEPER = """#!/usr/bin/env python3
import time
print("sleeping child ready")
time.sleep(60)
"""


class MuseDriverTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.workdir = self.tmp.name
        self.driver = None
        self.writer = self._standin("writer", WRITER)
        self.sleeper = self._standin("sleeper", SLEEPER)

    def _standin(self, name, text):
        path = os.path.join(self.workdir, name)
        with open(path, "w") as f:
            f.write(text)
        os.chmod(path, os.stat(path).st_mode | stat.S_IXUSR)
        return path

    def tearDown(self):
        try:
            if self.driver is not None and self.driver._proc is not None:
                if self.driver.poll() is None:
                    self.driver.stop()
                self.driver.artifacts()
        except Exception:
            pass
        self.tmp.cleanup()

    def started(self, sp=None, binary=None):
        self.driver = driver_mod.MuseDriver(
            self.workdir, muse_binary=binary or self.writer)
        self.driver.start(sp or spec())
        return self.driver

    def test_c1_unsigned_spec_rejected_and_nothing_spawns(self):
        unsigned = spec()
        del unsigned["sig"]
        for bad in (spec(sig=""), unsigned):
            d = driver_mod.MuseDriver(self.workdir,
                                      muse_binary=self.writer)
            with self.assertRaises(driver_mod.UnsignedSpecError):
                d.start(bad)
            self.assertIsNone(d._proc)

    def test_c2_unparseable_accept_rejected(self):
        d = driver_mod.MuseDriver(self.workdir, muse_binary=self.writer)
        with self.assertRaises(driver_mod.BadSpecError):
            d.start(spec(accept="nonsense without a colon"))
        self.assertIsNone(d._proc)

    def test_c3_empty_files_rejected(self):
        d = driver_mod.MuseDriver(self.workdir, muse_binary=self.writer)
        with self.assertRaises(driver_mod.BadSpecError):
            d.start(spec(files=[]))
        self.assertIsNone(d._proc)

    def test_c4_heartbeat_shape_and_before_start(self):
        d = driver_mod.MuseDriver(self.workdir, muse_binary=self.writer)
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
        d = driver_mod.MuseDriver(self.workdir, muse_binary=self.sleeper)
        d.start(spec())
        self.driver = d
        time.sleep(0.3)
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
        d = driver_mod.MuseDriver(self.workdir, muse_binary=self.writer)
        d.start(spec(accept="file-exists: missing.txt"))
        self.driver = d
        self.assertFalse(d.artifacts()["acceptance"]["ok"])

    def test_c8_unowned_changes_visible(self):
        d = driver_mod.MuseDriver(self.workdir, muse_binary=self.writer)
        # writer always writes out.txt; make out.txt unowned here
        d.start(spec(files=["other.txt"]))
        self.driver = d
        arts = d.artifacts()
        self.assertIn("out.txt", arts["changed_files"])
        self.assertIn("out.txt", arts["unowned_files"])

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

    def test_prompt_carries_work_not_signature(self):
        prompt = driver_mod.build_prompt(spec())
        self.assertIn("write the output file", prompt)
        self.assertIn("Create out.txt in the workdir.", prompt)
        self.assertIn("out.txt", prompt)
        self.assertIn("file-exists: out.txt", prompt)
        self.assertNotIn("deadbeef", prompt)

    def test_argv_shape_and_extra_args(self):
        argv = driver_mod.build_argv("muse", "/tmp/prompt.md")
        self.assertEqual(argv, ["muse", "exec", "--prompt-file",
                                "/tmp/prompt.md"])
        argv = driver_mod.build_argv("muse", "/tmp/prompt.md",
                                     ["--json"])
        self.assertEqual(argv[-1], "--json")

    def test_child_output_streamed_into_heartbeats(self):
        sink = []
        d = driver_mod.MuseDriver(self.workdir, heartbeat_sink=sink.append,
                                  muse_binary=self.writer)
        d.start(spec())
        self.driver = d
        d.artifacts()
        notes = [r["note"] for r in sink]
        self.assertIn("wrote out.txt", notes)
        for rec in sink:
            self.assertTrue(rec["line"].startswith("PROGRESS:job-1 "))
            self.assertEqual(rec["job_id"], "job-1")
        with open(os.path.join(self.workdir, "driver.log")) as f:
            log = f.read()
        self.assertIn("wrote out.txt", log)

    def test_missing_binary_refused_before_spawning(self):
        d = driver_mod.MuseDriver(self.workdir,
                                  muse_binary="/nonexistent/muse-binary")
        with self.assertRaises(driver_mod.DriverError):
            d.start(spec())
        self.assertIsNone(d._proc)

    def test_prompt_file_lives_outside_workdir_and_is_cleaned(self):
        self.started()
        tmpdir = self.driver._tmpdir
        self.assertFalse(tmpdir.startswith(self.workdir))
        self.driver.artifacts()
        self.assertFalse(os.path.exists(tmpdir))

    def test_runner_prints_artifacts_json(self):
        spec_path = os.path.join(self.workdir, "job.json")
        with open(spec_path, "w") as f:
            json.dump(spec(), f)
        proc = subprocess.run(
            [sys.executable, RUNNER, "--spec-file", spec_path,
             "--workdir", self.workdir, "--binary", self.writer],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        arts = json.loads(proc.stdout)
        self.assertEqual(arts["status"], "done")
        self.assertIn("out.txt", arts["changed_files"])
        self.assertTrue(arts["acceptance"]["ok"])

    def test_runner_refuses_unsigned_spec_with_exit_2(self):
        bad = spec()
        del bad["sig"]
        spec_path = os.path.join(self.workdir, "job.json")
        with open(spec_path, "w") as f:
            json.dump(bad, f)
        proc = subprocess.run(
            [sys.executable, RUNNER, "--spec-file", spec_path,
             "--workdir", self.workdir, "--binary", self.writer],
            capture_output=True, text=True, timeout=30)
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")


if __name__ == "__main__":
    unittest.main()
