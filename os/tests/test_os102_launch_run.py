"""tests/test_os102_launch_run.py -- OS-102 follow-up (Pax).

Pins intel/launch_run.py: a real child process started from an
assembled launch directory sees the mounted skills in its first
action, a control launch does not show a skill it never mounted,
and a launch that no longer verifies spawns nothing at all.

The probe is a real subprocess, not a stub: it runs with cwd set
to the launch directory and reads the assembled layers from
relative paths, exactly as a worker or driver process would.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from intel import launch_run  # noqa: E402
from intel import mind_loader  # noqa: E402

CATALOG = ["jobs", "briefs", "alerts"]

SKILL_PROBE = (
    "import json, os;"
    "base = 'skills';"
    "names = sorted(d for d in os.listdir(base) "
    "if os.path.isfile(os.path.join(base, d, 'SKILL.md'))) "
    "if os.path.isdir(base) else [];"
    "print(json.dumps({'skills': names, "
    "'launch_dir': os.environ.get('METAOS_LAUNCH_DIR', '')}))"
)


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(text)


def _bundle(root, brief="file", shared=True, grant_identity="pax",
            skill_names=("coordinate",), tool_grants=("jobs",)):
    skills = []
    for name in skill_names:
        _write(os.path.join(root, "skills", name, "SKILL.md"),
               "# " + name + " skill\n")
        skills.append("skills/" + name)
    _write(os.path.join(root, "constitution.md"),
           "# constitution\nBe direct.\n")
    _write(os.path.join(root, "memory", "own", "NOTE.md"), "own memory\n")
    memory = {"own": "memory/own", "shared": None}
    if shared:
        _write(os.path.join(root, "memory", "shared", "NOTE.md"),
               "shared memory\n")
        memory["shared"] = "memory/shared"
    _write(os.path.join(root, "grants.json"), json.dumps(
        {"identity": grant_identity, "actions": ["jobs.read"]}))
    brief_value = {"file": "brief.json"} if brief == "file" else {
        "slot": "generated-at-launch"}
    if brief == "file":
        _write(os.path.join(root, "brief.json"),
               json.dumps({"window": "today"}))
    _write(os.path.join(root, "changelog.md"), "# v1\n")
    manifest = {
        "format": "metaos-mind-image",
        "version": "1",
        "agent": {"nick": "pax", "identity": "coordinator"},
        "constitution": "constitution.md",
        "skills": skills,
        "memory_mount": memory,
        "capability_grant": "grants.json",
        "tool_grants": list(tool_grants),
        "environment_brief": brief_value,
        "changelog": "changelog.md",
    }
    _write(os.path.join(root, "manifest.json"),
           json.dumps(manifest, indent=2))
    return root


class LaunchRunTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bundle = _bundle(os.path.join(self.tmp, "bundle"))
        self.launch = os.path.join(self.tmp, "launch")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _assemble(self, launch=None, kind="worker", bundle=None):
        launch = launch or self.launch
        bundle = bundle or self.bundle
        if kind == "driver":
            mind_loader.assemble_driver_launch(bundle, launch, CATALOG)
        else:
            mind_loader.assemble_worker_launch(bundle, launch, CATALOG)
        return launch

    def _probe(self, launch, code=SKILL_PROBE):
        return launch_run.run_from_launch(
            launch, [sys.executable, "-c", code], self.bundle, CATALOG)

    def test_mounted_skill_visible_in_first_action(self):
        launch = self._assemble()
        result = self._probe(launch)
        self.assertEqual(result["returncode"], 0)
        body = json.loads(result["stdout"])
        self.assertEqual(body["skills"], ["coordinate"])
        self.assertEqual(body["launch_dir"], os.path.abspath(launch))

    def test_unmounted_skill_absent_control(self):
        bundle = _bundle(os.path.join(self.tmp, "bundle-other"),
                         skill_names=("other",))
        launch = self._assemble(launch=os.path.join(self.tmp, "launch-b"),
                                bundle=bundle)
        result = launch_run.run_from_launch(
            launch, [sys.executable, "-c", SKILL_PROBE], bundle, CATALOG)
        body = json.loads(result["stdout"])
        self.assertEqual(body["skills"], ["other"])
        self.assertNotIn("coordinate", body["skills"])

    def test_worker_and_driver_see_identical_skills(self):
        worker = self._assemble(launch=os.path.join(self.tmp, "worker"))
        driver = self._assemble(launch=os.path.join(self.tmp, "driver"),
                                kind="driver")
        worker_skills = json.loads(self._probe(worker)["stdout"])["skills"]
        driver_skills = json.loads(self._probe(driver)["stdout"])["skills"]
        self.assertEqual(worker_skills, ["coordinate"])
        self.assertEqual(worker_skills, driver_skills)

    def test_slot_brief_launch_runs(self):
        bundle = _bundle(os.path.join(self.tmp, "bundle-slot"),
                         brief="slot")
        launch = self._assemble(launch=os.path.join(self.tmp, "launch-s"),
                                bundle=bundle)
        self.assertTrue(os.path.isfile(os.path.join(launch, "brief.pending")))
        result = launch_run.run_from_launch(
            launch, [sys.executable, "-c", SKILL_PROBE], bundle, CATALOG)
        self.assertEqual(result["returncode"], 0)
        self.assertEqual(
            json.loads(result["stdout"])["skills"], ["coordinate"])

    def test_tampered_skill_refused_and_nothing_spawns(self):
        launch = self._assemble()
        with open(os.path.join(launch, "skills", "coordinate",
                               "SKILL.md"), "a", encoding="utf-8") as handle:
            handle.write("tampered\n")
        marker = os.path.join(launch, "ran.marker")
        with self.assertRaises(launch_run.LaunchRunError) as ctx:
            launch_run.run_from_launch(
                launch,
                [sys.executable, "-c",
                 "open('ran.marker', 'w').write('ran')"],
                self.bundle, CATALOG)
        self.assertIn("skill changed", str(ctx.exception))
        self.assertFalse(os.path.exists(marker))

    def test_tampered_constitution_refused(self):
        launch = self._assemble()
        with open(os.path.join(launch, "instructions.md"), "a",
                  encoding="utf-8") as handle:
            handle.write("tampered\n")
        with self.assertRaises(launch_run.LaunchRunError) as ctx:
            self._probe(launch)
        self.assertIn("constitution", str(ctx.exception))

    def test_missing_launch_refused(self):
        with self.assertRaises(launch_run.LaunchRunError):
            launch_run.run_from_launch(
                os.path.join(self.tmp, "no-such-launch"),
                [sys.executable, "-c", "pass"])

    def test_empty_argv_refused(self):
        launch = self._assemble()
        with self.assertRaises(launch_run.LaunchRunError):
            launch_run.run_from_launch(launch, [])

    def test_nonzero_exit_returned_not_raised(self):
        launch = self._assemble()
        result = launch_run.run_from_launch(
            launch, [sys.executable, "-c", "import sys; sys.exit(3)"],
            self.bundle, CATALOG)
        self.assertEqual(result["returncode"], 3)

    def test_stderr_captured(self):
        launch = self._assemble()
        result = launch_run.run_from_launch(
            launch,
            [sys.executable, "-c",
             "import sys; sys.stderr.write('first action note\\n')"],
            self.bundle, CATALOG)
        self.assertEqual(result["returncode"], 0)
        self.assertIn("first action note", result["stderr"])

    def test_timeout_kills_child(self):
        launch = self._assemble()
        with self.assertRaises(launch_run.LaunchRunError) as ctx:
            launch_run.run_from_launch(
                launch, [sys.executable, "-c", "import time; time.sleep(30)"],
                self.bundle, CATALOG, timeout=1)
        self.assertIn("timed out", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
