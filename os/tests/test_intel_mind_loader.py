"""tests/test_intel_mind_loader.py -- OS-102 (Pax).

Pins intel/mind_loader.py: process launch assembles a mind image
(OS-101 bundle) into a launch environment, worker and driver
through the identical layer assembly, and verify_launch() proves
the launched layers still match the bundle exactly. Fixture
bundles live under tempfile except the example-bundle tests,
which read the real committed example.
"""

import json
import os
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from intel import mind_loader  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(ROOT, "intel", "examples", "mind-images",
                       "pax-default")
CATALOG = ["jobs", "briefs", "alerts"]


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


class LoaderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.bundle = _bundle(os.path.join(self.tmp, "bundle"))
        self.launch = os.path.join(self.tmp, "launch")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_worker_launch_layers_match_bundle(self):
        manifest = mind_loader.assemble_worker_launch(
            self.bundle, self.launch, CATALOG)
        self.assertEqual(manifest["process_kind"], "worker")
        self.assertEqual(manifest["bundle_version"], "1")
        self.assertEqual(manifest["agent"]["nick"], "pax")
        with open(os.path.join(self.launch, "instructions.md")) as handle:
            self.assertEqual(handle.read(), "# constitution\nBe direct.\n")
        with open(os.path.join(self.launch, "skills", "coordinate",
                               "SKILL.md")) as handle:
            self.assertEqual(handle.read(), "# coordinate skill\n")
        self.assertEqual(manifest["tool_grants"], ["jobs"])
        with open(os.path.join(self.launch, "tool_grants.json")) as handle:
            self.assertEqual(json.load(handle), ["jobs"])
        self.assertTrue(os.path.islink(
            os.path.join(self.launch, "memory", "own")))
        self.assertTrue(os.path.islink(
            os.path.join(self.launch, "memory", "shared")))
        self.assertEqual(manifest["brief_status"], "file")
        with open(os.path.join(self.launch, "brief.json")) as handle:
            self.assertEqual(json.load(handle), {"window": "today"})
        self.assertTrue(mind_loader.verify_launch(
            self.launch, self.bundle, CATALOG)["ok"])

    def test_driver_launch_identical_layers(self):
        worker_dir = os.path.join(self.tmp, "worker")
        driver_dir = os.path.join(self.tmp, "driver")
        worker = mind_loader.assemble_worker_launch(
            self.bundle, worker_dir, CATALOG)
        driver = mind_loader.assemble_driver_launch(
            self.bundle, driver_dir, CATALOG)
        self.assertEqual(driver["process_kind"], "driver")
        self.assertEqual(worker["layers"], driver["layers"])
        self.assertEqual(worker["tool_grants"], driver["tool_grants"])
        self.assertEqual(worker["memory"], driver["memory"])
        self.assertTrue(mind_loader.verify_launch(
            driver_dir, self.bundle, CATALOG)["ok"])

    def test_example_bundle_launches_both_kinds(self):
        for kind, fn in (("worker", mind_loader.assemble_worker_launch),
                         ("driver", mind_loader.assemble_driver_launch)):
            launch = os.path.join(self.tmp, "ex-" + kind)
            manifest = fn(EXAMPLE, launch, CATALOG)
            self.assertEqual(manifest["process_kind"], kind)
            self.assertEqual(sorted(manifest["layers"]["skills"]),
                             ["coordinate", "dispatch"])
            self.assertTrue(mind_loader.verify_launch(
                launch, EXAMPLE, CATALOG)["ok"])

    def test_slot_brief_is_pending_not_fabricated(self):
        bundle = _bundle(os.path.join(self.tmp, "slot-bundle"),
                         brief="slot")
        manifest = mind_loader.assemble_launch(bundle, self.launch,
                                               CATALOG)
        self.assertEqual(manifest["brief_status"], "pending")
        self.assertFalse(os.path.exists(
            os.path.join(self.launch, "brief.json")))
        self.assertTrue(os.path.exists(
            os.path.join(self.launch, "brief.pending")))
        with open(os.path.join(self.launch, "brief.pending")) as handle:
            self.assertIn("generated-at-launch", handle.read())
        self.assertTrue(mind_loader.verify_launch(
            self.launch, bundle, CATALOG)["ok"])

    def test_null_shared_memory_has_no_shared_mount(self):
        bundle = _bundle(os.path.join(self.tmp, "noshared"),
                         shared=False)
        manifest = mind_loader.assemble_launch(bundle, self.launch,
                                               CATALOG)
        self.assertIsNone(manifest["memory"]["shared"])
        self.assertFalse(os.path.lexists(
            os.path.join(self.launch, "memory", "shared")))
        self.assertTrue(mind_loader.verify_launch(
            self.launch, bundle, CATALOG)["ok"])

    def test_unknown_kind_refused(self):
        with self.assertRaises(mind_loader.LaunchError):
            mind_loader.assemble_launch(self.bundle, self.launch,
                                        CATALOG, process_kind="daemon")

    def test_nonempty_launch_dir_refused(self):
        os.makedirs(self.launch)
        _write(os.path.join(self.launch, "stray.txt"), "stray\n")
        with self.assertRaises(mind_loader.LaunchError):
            mind_loader.assemble_launch(self.bundle, self.launch, CATALOG)

    def test_unresolved_bundle_refused(self):
        os.remove(os.path.join(self.bundle, "constitution.md"))
        with self.assertRaises(Exception):
            mind_loader.assemble_launch(self.bundle, self.launch, CATALOG)

    def test_skill_without_skill_md_refused(self):
        os.remove(os.path.join(self.bundle, "skills", "coordinate",
                               "SKILL.md"))
        with self.assertRaises(mind_loader.LaunchError):
            mind_loader.assemble_launch(self.bundle, self.launch, CATALOG)

    def test_tool_outside_catalog_refused(self):
        bundle = _bundle(os.path.join(self.tmp, "badtool"),
                         tool_grants=("nope",))
        with self.assertRaises(Exception):
            mind_loader.assemble_launch(bundle, self.launch, CATALOG)

    def test_extra_bundle_dir_not_mounted(self):
        _write(os.path.join(self.bundle, "skills", "unlisted",
                            "SKILL.md"), "# unlisted\n")
        mind_loader.assemble_launch(self.bundle, self.launch, CATALOG)
        self.assertFalse(os.path.exists(os.path.join(
            self.launch, "skills", "unlisted")))
        self.assertTrue(mind_loader.verify_launch(
            self.launch, self.bundle, CATALOG)["ok"])

    def test_tampered_constitution_fails_verify(self):
        mind_loader.assemble_launch(self.bundle, self.launch, CATALOG)
        _write(os.path.join(self.launch, "instructions.md"),
               "# tampered\n")
        report = mind_loader.verify_launch(
            self.launch, self.bundle, CATALOG)
        self.assertFalse(report["ok"])
        self.assertTrue(any("constitution" in err
                            for err in report["errors"]))

    def test_tampered_skill_fails_verify(self):
        mind_loader.assemble_launch(self.bundle, self.launch, CATALOG)
        _write(os.path.join(self.launch, "skills", "coordinate",
                            "SKILL.md"), "# tampered\n")
        report = mind_loader.verify_launch(
            self.launch, self.bundle, CATALOG)
        self.assertFalse(report["ok"])
        self.assertTrue(any("coordinate" in err
                            for err in report["errors"]))

    def test_repointed_memory_mount_fails_verify(self):
        mind_loader.assemble_launch(self.bundle, self.launch, CATALOG)
        link = os.path.join(self.launch, "memory", "own")
        os.remove(link)
        os.symlink(os.path.join(self.bundle, "memory", "shared"), link)
        report = mind_loader.verify_launch(
            self.launch, self.bundle, CATALOG)
        self.assertFalse(report["ok"])
        self.assertTrue(any("memory" in err
                            for err in report["errors"]))

    def test_missing_launch_json_fails_verify(self):
        report = mind_loader.verify_launch(self.launch, self.bundle,
                                           CATALOG)
        self.assertFalse(report["ok"])
        self.assertTrue(any("launch.json" in err
                            for err in report["errors"]))

    def test_verify_without_bundle_dir_uses_manifest_path(self):
        mind_loader.assemble_launch(self.bundle, self.launch, CATALOG)
        report = mind_loader.verify_launch(self.launch,
                                           gateway_catalog=CATALOG)
        self.assertTrue(report["ok"])

    def test_launch_summary_names_kind_and_version(self):
        manifest = mind_loader.assemble_launch(
            self.bundle, self.launch, CATALOG, process_kind="driver")
        summary = mind_loader.launch_summary(manifest)
        self.assertIn("driver", summary)
        self.assertIn("v1", summary)
        self.assertIn("pax", summary)


if __name__ == "__main__":
    unittest.main()
