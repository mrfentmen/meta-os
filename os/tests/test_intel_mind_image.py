"""tests/test_intel_mind_image.py -- OS-101 (Pax).

Pins intel/mind_image.py: the mind-image bundle format. The
committed example bundle must parse and resolve every layer; the
failure cases pin each refusal. All bundles here are fixture dirs
under tempfile except the example bundle test, which reads the
real committed example.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))

from intel import mind_image  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE = os.path.join(ROOT, "intel", "examples", "mind-images",
                       "pax-default")
CATALOG = ["jobs", "briefs", "alerts"]


def _manifest(**overrides):
    base = {
        "format": "metaos-mind-image",
        "version": "1",
        "agent": {"nick": "pax", "identity": "coordinator"},
        "constitution": "constitution.md",
        "skills": ["skills/coordinate"],
        "memory_mount": {"own": "memory/own", "shared": "memory/shared"},
        "capability_grant": "grants.json",
        "tool_grants": ["jobs"],
        "environment_brief": {"file": "brief.json"},
        "changelog": "changelog.md",
    }
    base.update(overrides)
    return base


def _write_bundle(directory, manifest):
    os.makedirs(os.path.join(directory, "skills", "coordinate"))
    os.makedirs(os.path.join(directory, "memory", "own"))
    os.makedirs(os.path.join(directory, "memory", "shared"))
    for name in ("constitution.md", "changelog.md", "brief.json"):
        with open(os.path.join(directory, name), "w") as handle:
            handle.write("example\n")
    with open(os.path.join(directory, "grants.json"), "w") as handle:
        json.dump({"identity": "pax", "actions": ["jobs.read"]}, handle)
    with open(os.path.join(directory, "manifest.json"), "w") as handle:
        json.dump(manifest, handle)
    return os.path.join(directory, "manifest.json")


class ParseTest(unittest.TestCase):
    def test_golden_manifest_parses(self):
        bundle = mind_image.parse_bundle(json.dumps(_manifest()))
        self.assertEqual(bundle["version"], "1")
        self.assertEqual(bundle["agent"]["nick"], "pax")

    def test_malformed_json_refused(self):
        with self.assertRaises(mind_image.BundleError):
            mind_image.parse_bundle("{not json")

    def test_wrong_format_refused(self):
        with self.assertRaises(mind_image.BundleError):
            mind_image.parse_bundle(json.dumps(
                _manifest(format="other-format")))

    def test_bad_version_refused(self):
        with self.assertRaises(mind_image.BundleError):
            mind_image.parse_bundle(json.dumps(_manifest(version="v1")))

    def test_unknown_field_refused(self):
        manifest = _manifest()
        manifest["secrets"] = "never"
        with self.assertRaises(mind_image.BundleError):
            mind_image.parse_bundle(json.dumps(manifest))

    def test_duplicate_skill_refused(self):
        with self.assertRaises(mind_image.BundleError):
            mind_image.parse_bundle(json.dumps(
                _manifest(skills=["skills/coordinate",
                                  "skills/coordinate"])))

    def test_unknown_brief_slot_refused(self):
        with self.assertRaises(mind_image.BundleError):
            mind_image.parse_bundle(json.dumps(_manifest(
                environment_brief={"slot": "live-brief"})))


class ResolveTest(unittest.TestCase):
    def _resolve(self, manifest, catalog=CATALOG):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = _write_bundle(tmp.name, manifest)
        bundle, bundle_dir = mind_image.load_bundle(path)
        return mind_image.resolve_bundle(bundle, bundle_dir, catalog)

    def test_fixture_bundle_resolves(self):
        report = self._resolve(_manifest())
        self.assertEqual(report["errors"], [])

    def test_slot_brief_resolves_without_file(self):
        manifest = _manifest(environment_brief={"slot": "generated-at-launch"})
        report = self._resolve(manifest)
        self.assertEqual(report["errors"], [])
        self.assertEqual(report["layers"]["environment_brief"],
                         "generated-at-launch")

    def test_null_shared_memory_resolves(self):
        manifest = _manifest(memory_mount={"own": "memory/own",
                                           "shared": None})
        report = self._resolve(manifest)
        self.assertEqual(report["errors"], [])
        self.assertIsNone(report["layers"]["memory_shared"])

    def test_missing_constitution_is_error(self):
        manifest = _manifest(constitution="missing.md")
        report = self._resolve(manifest)
        self.assertTrue(any("constitution" in err
                            for err in report["errors"]))
        with self.assertRaises(mind_image.BundleError):
            mind_image.validate_bundle(
                mind_image.parse_bundle(json.dumps(manifest)),
                tempfile.gettempdir(), CATALOG)

    def test_missing_skill_dir_is_error(self):
        manifest = _manifest(skills=["skills/absent"])
        report = self._resolve(manifest)
        self.assertTrue(any("skills" in err for err in report["errors"]))

    def test_path_escape_refused(self):
        manifest = _manifest(constitution="../outside.md")
        report = self._resolve(manifest)
        self.assertTrue(any("escapes" in err for err in report["errors"]))

    def test_absolute_path_refused(self):
        manifest = _manifest(constitution="/etc/passwd")
        report = self._resolve(manifest)
        self.assertTrue(any("absolute" in err for err in report["errors"]))

    def test_secret_named_layer_refused(self):
        manifest = _manifest(constitution="my-secret-notes.md")
        report = self._resolve(manifest)
        self.assertTrue(any("secrets never" in err
                            for err in report["errors"]))

    def test_bad_grant_is_error(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = _write_bundle(tmp.name, _manifest())
        with open(os.path.join(tmp.name, "grants.json"), "w") as handle:
            json.dump({"identity": "pax", "actions": []}, handle)
        bundle, bundle_dir = mind_image.load_bundle(path)
        report = mind_image.resolve_bundle(bundle, bundle_dir, CATALOG)
        self.assertTrue(any("capability_grant" in err
                            for err in report["errors"]))

    def test_tool_outside_catalog_is_error(self):
        manifest = _manifest(tool_grants=["nope-server"])
        report = self._resolve(manifest)
        self.assertTrue(any("not in the gateway catalog" in err
                            for err in report["errors"]))

    def test_no_catalog_leaves_tools_unresolved(self):
        report = self._resolve(_manifest(), catalog=None)
        self.assertTrue(any("no gateway catalog" in err
                            for err in report["errors"]))

    def test_no_catalog_empty_grants_resolve(self):
        report = self._resolve(_manifest(tool_grants=[]), catalog=None)
        self.assertEqual(report["errors"], [])


class ExampleBundleTest(unittest.TestCase):
    def test_example_bundle_resolves_fully(self):
        with open(os.path.join(EXAMPLE, "gateway-catalog.json")) as handle:
            catalog = json.load(handle)["servers"]
        bundle, bundle_dir = mind_image.load_bundle(
            os.path.join(EXAMPLE, "manifest.json"))
        report = mind_image.validate_bundle(bundle, bundle_dir, catalog)
        self.assertEqual(report["errors"], [])
        summary = mind_image.bundle_summary(bundle, report)
        self.assertIn("pax mind image v1", summary)
        self.assertIn("all layers resolved", summary)


if __name__ == "__main__":
    unittest.main()
