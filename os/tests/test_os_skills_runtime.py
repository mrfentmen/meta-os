"""Tests for installing and routing the shipped skill catalog.

Run directly:

    python3 os/tests/test_os_skills_runtime.py -v

The installer copies the real 307-skill catalog into temporary roots and
verifies it; the router ranks real frontmatter. No network, no model call,
no writes outside temp directories.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
INSTALL = os.path.join(SKILLS, "_tools", "install.py")
ROUTER = os.path.join(SKILLS, "_tools", "router.py")


def run(script, *args):
    return subprocess.run(
        [sys.executable, script, *args],
        capture_output=True,
        text=True,
        timeout=120,
    )


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="metaos-skills-install-")
        self.root = os.path.join(self.tmp, "skills")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_install_and_check_the_real_catalog(self):
        result = run(INSTALL, "--root", self.root)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("INSTALLED 307 skills", result.stdout)
        with open(os.path.join(self.root, "skills.json"), encoding="utf-8") as handle:
            manifest = json.load(handle)
        self.assertEqual(manifest["format"], "metaos-skills-collection")
        self.assertEqual(len(manifest["skills"]), 307)
        check = run(INSTALL, "--root", self.root, "--check")
        self.assertEqual(check.returncode, 0, check.stderr)
        self.assertIn("OK 307 skills", check.stdout)

    def test_check_names_a_tampered_skill(self):
        self.assertEqual(run(INSTALL, "--root", self.root).returncode, 0)
        target = os.path.join(self.root, "flaky-tests", "SKILL.md")
        with open(target, "a", encoding="utf-8") as handle:
            handle.write("\ntampered\n")
        check = run(INSTALL, "--root", self.root, "--check")
        self.assertEqual(check.returncode, 1)
        self.assertIn("flaky-tests", check.stderr)

    def test_reinstall_requires_force(self):
        self.assertEqual(run(INSTALL, "--root", self.root).returncode, 0)
        refused = run(INSTALL, "--root", self.root)
        self.assertEqual(refused.returncode, 2)
        self.assertIn("--force", refused.stderr)
        forced = run(INSTALL, "--root", self.root, "--force")
        self.assertEqual(forced.returncode, 0, forced.stderr)

    def test_install_preserves_the_image_marker(self):
        os.makedirs(self.root)
        marker = os.path.join(self.root, ".metaos-skills-root")
        with open(marker, "w", encoding="utf-8") as handle:
            handle.write("skills-collection-root\n")
        self.assertEqual(run(INSTALL, "--root", self.root).returncode, 0)
        self.assertTrue(os.path.isfile(marker))

    def test_bad_source_is_refused_before_copying(self):
        source = os.path.join(self.tmp, "bad-source")
        os.makedirs(os.path.join(source, "Bad Name"))
        with open(os.path.join(source, "Bad Name", "SKILL.md"),
                  "w", encoding="utf-8") as handle:
            handle.write("---\nname: Bad Name\n---\n")
        result = run(INSTALL, "--root", self.root, "--source", source)
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid skill directory name", result.stderr)
        self.assertFalse(os.path.exists(self.root))


class RouterTests(unittest.TestCase):
    def route(self, query, *extra):
        result = run(ROUTER, "--json", *extra, query)
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)["matches"]

    def test_expected_skill_is_first(self):
        cases = [
            ("fix the flaky clipboard test", "flaky-tests"),
            ("write the README for this repo", "readme"),
            ("add a systemd unit that starts at boot", "systemd-unit"),
            ("rotate a key with an overlap window", "key-rotation"),
            ("trace a memory leak in the daemon", "memory-leak"),
        ]
        for query, expected in cases:
            matches = self.route(query)
            self.assertTrue(matches, f"{query!r} matched nothing")
            self.assertEqual(matches[0]["name"], expected,
                             f"{query!r} -> {matches}")

    def test_unrelated_requests_do_not_route(self):
        for query in ("flibbertigibbet zzz", "the a an", ""):
            if not query:
                continue
            self.assertEqual(self.route(query), [], query)

    def test_limit_and_determinism(self):
        first = self.route("fix a flaky test", "--limit", "2")
        second = self.route("fix a flaky test", "--limit", "2")
        self.assertEqual(first, second)
        self.assertLessEqual(len(first), 2)

    def test_list_is_the_whole_catalog(self):
        result = run(ROUTER, "--list")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(result.stdout.splitlines()), 307)


if __name__ == "__main__":
    unittest.main()
