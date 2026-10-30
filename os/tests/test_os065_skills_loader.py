"""tests/test_os065_skills_loader.py -- OS-065: the skills loader.

First light pins: a collection lists mountable skills only, a
named mount copies verbatim with a hash manifest, verify catches
tampering and unlisted mounts, and every refusal names its
fault before anything is copied. The mind loader mounts its
bundle skills through this same module, so its existing tests
pin the shared rule from the bundle side.

No bus post, no live Redis, no network, no process spawn: mounts
run against temporary directories plus the repo's fixture
collection. A driver process showing a mounted skill active in
its first action, and the unmounted control run, stay owed
(OS-055 integration proof), as does populating the image
collection root with a real collection.
"""

import hashlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from intel import skills_loader

FIXTURES = os.path.join(ROOT, "intel", "examples", "skills")


class SkillsLoaderTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="metaos-skills-")
        self.launch = os.path.join(self.tmp, "launch")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_list_fixture_collection(self):
        names = skills_loader.list_skills(FIXTURES)
        self.assertEqual(names, ["fixture-brief", "fixture-ledger"])

    def test_mount_selected_only(self):
        manifest = skills_loader.mount_skills(
            FIXTURES, ["fixture-ledger"], self.launch)
        self.assertEqual(sorted(manifest["skills"]), ["fixture-ledger"])
        self.assertFalse(os.path.exists(os.path.join(
            self.launch, "skills", "fixture-brief")))
        with open(os.path.join(self.launch, "skills", "fixture-ledger",
                               "SKILL.md"), encoding="utf-8") as handle:
            mounted = handle.read()
        with open(os.path.join(FIXTURES, "fixture-ledger",
                               "SKILL.md"), encoding="utf-8") as handle:
            original = handle.read()
        self.assertEqual(mounted, original)
        self.assertEqual(skills_loader.verify_mount(self.launch), [])

    def test_manifest_hashes_match_files(self):
        manifest = skills_loader.mount_skills(
            FIXTURES, ["fixture-ledger", "fixture-brief"], self.launch)
        for name, hashes in manifest["skills"].items():
            for rel, digest in hashes.items():
                path = os.path.join(self.launch, "skills", name, rel)
                with open(path, "rb") as handle:
                    self.assertEqual(hashlib.sha256(handle.read())
                                     .hexdigest(), digest)
        with open(os.path.join(self.launch, "skills.json"),
                  encoding="utf-8") as handle:
            stored = json.load(handle)
        self.assertEqual(stored["format"], "metaos-skills-mount")
        self.assertEqual(stored["skills"], manifest["skills"])

    def test_verify_tampered_file_names_skill(self):
        skills_loader.mount_skills(
            FIXTURES, ["fixture-ledger"], self.launch)
        with open(os.path.join(self.launch, "skills", "fixture-ledger",
                               "notes.md"), "a", encoding="utf-8") as handle:
            handle.write("tampered\n")
        errors = skills_loader.verify_mount(self.launch)
        self.assertTrue(any("fixture-ledger" in err for err in errors))

    def test_verify_extra_dir_is_unlisted_mount(self):
        skills_loader.mount_skills(
            FIXTURES, ["fixture-ledger"], self.launch)
        os.makedirs(os.path.join(self.launch, "skills", "sneaked"))
        errors = skills_loader.verify_mount(self.launch)
        self.assertTrue(any("sneaked" in err for err in errors))

    def test_verify_missing_manifest(self):
        os.makedirs(self.launch)
        errors = skills_loader.verify_mount(self.launch)
        self.assertTrue(errors)

    def test_folder_without_skill_md_refused(self):
        with self.assertRaises(skills_loader.SkillsLoaderError):
            skills_loader.mount_skills(
                FIXTURES, ["not-a-skill"], self.launch)
        self.assertFalse(os.path.exists(
            os.path.join(self.launch, "skills")))

    def test_unknown_name_refused(self):
        with self.assertRaises(skills_loader.SkillsLoaderError):
            skills_loader.mount_skills(FIXTURES, ["nope"], self.launch)

    def test_duplicate_name_refused(self):
        with self.assertRaises(skills_loader.SkillsLoaderError):
            skills_loader.mount_skills(
                FIXTURES, ["fixture-ledger", "fixture-ledger"],
                self.launch)
        self.assertFalse(os.path.exists(
            os.path.join(self.launch, "skills")))

    def test_traversal_names_refused(self):
        for bad in ("../outside", "a/b", "", ".", ".."):
            with self.assertRaises(skills_loader.SkillsLoaderError):
                skills_loader.mount_skills(FIXTURES, [bad], self.launch)

    def test_skill_dir_symlink_escape_refused(self):
        outside = os.path.join(self.tmp, "outside")
        os.makedirs(outside)
        with open(os.path.join(outside, "SKILL.md"),
                  "w", encoding="utf-8") as handle:
            handle.write("# outside\n")
        os.symlink(outside, os.path.join(self.tmp, "linked"))
        collection = os.path.join(self.tmp, "collection")
        os.makedirs(collection)
        os.symlink(os.path.join(self.tmp, "linked"),
                   os.path.join(collection, "linked"))
        with self.assertRaises(skills_loader.SkillsLoaderError):
            skills_loader.mount_skills(collection, ["linked"], self.launch)

    def test_file_symlink_escape_refused(self):
        collection = os.path.join(self.tmp, "collection")
        skill = os.path.join(collection, "leaky")
        os.makedirs(skill)
        with open(os.path.join(skill, "SKILL.md"),
                  "w", encoding="utf-8") as handle:
            handle.write("# leaky\n")
        secret = os.path.join(self.tmp, "secret.txt")
        with open(secret, "w", encoding="utf-8") as handle:
            handle.write("secret\n")
        os.symlink(secret, os.path.join(skill, "leak.txt"))
        with self.assertRaises(skills_loader.SkillsLoaderError):
            skills_loader.mount_skills(collection, ["leaky"], self.launch)

    def test_mount_over_existing_refused(self):
        skills_loader.mount_skills(
            FIXTURES, ["fixture-ledger"], self.launch)
        with self.assertRaises(skills_loader.SkillsLoaderError):
            skills_loader.mount_skills(
                FIXTURES, ["fixture-ledger"], self.launch)

    def test_empty_mount_writes_empty_manifest(self):
        manifest = skills_loader.mount_skills(FIXTURES, [], self.launch)
        self.assertEqual(manifest["skills"], {})
        self.assertEqual(skills_loader.verify_mount(self.launch), [])

    def test_cli_list_mount_verify(self):
        out = io.StringIO()
        with redirect_stdout(out):
            rc = skills_loader.main(["list", FIXTURES])
        self.assertEqual(rc, 0)
        self.assertEqual(out.getvalue().split(),
                         ["fixture-brief", "fixture-ledger"])
        rc = skills_loader.main(["mount", FIXTURES, "fixture-brief",
                                 "--into", self.launch])
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.isfile(os.path.join(
            self.launch, "skills", "fixture-brief", "SKILL.md")))
        rc = skills_loader.main(["verify", self.launch])
        self.assertEqual(rc, 0)
        rc = skills_loader.main(["mount", FIXTURES, "nope",
                                 "--into", self.launch])
        self.assertEqual(rc, 1)
        rc = skills_loader.main(["bogus"])
        self.assertEqual(rc, 2)


class SkillsBakeTest(unittest.TestCase):
    """The three image routes bake the collection root, empty plus marker."""

    def read(self, rel):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
            return handle.read()

    def test_build_image_bakes_collection_root(self):
        text = self.read("os/build-image.sh")
        self.assertIn("2e. OS-065", text)
        self.assertIn("/var/lib/metaos/skills", text)
        self.assertIn(".metaos-skills-root", text)
        self.assertIn("chown relay:relay /var/lib/metaos/skills", text)

    def test_build_live_stages_collection_root(self):
        text = self.read("os/build-live.sh")
        self.assertIn("OS-065", text)
        self.assertIn("/var/lib/metaos/skills", text)
        self.assertIn(".metaos-skills-root", text)

    def test_packer_bakes_collection_root(self):
        text = self.read("os/packer/metaos.pkr.hcl")
        self.assertIn("/var/lib/metaos/skills", text)
        self.assertIn(".metaos-skills-root", text)
        self.assertIn("chown -R relay:relay /var/lib/metaos/skills", text)

    def test_live_hook_owns_collection_root(self):
        text = self.read(
            "os/live-build/config/hooks/live/0900-metaos-services.hook.chroot")
        self.assertIn("/var/lib/metaos/skills", text)
        self.assertIn("chown relay:relay /var/lib/metaos/skills", text)

    @unittest.skipUnless(shutil.which("bash"), "bash not available")
    def test_build_scripts_parse(self):
        for rel in ("os/build-image.sh", "os/build-live.sh"):
            proc = subprocess.run(
                ["bash", "-n", os.path.join(ROOT, rel)],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_no_em_dash_in_new_files(self):
        paths = [
            os.path.join(ROOT, "intel", "skills_loader.py"),
            os.path.join(FIXTURES, "fixture-ledger", "SKILL.md"),
            os.path.join(FIXTURES, "fixture-brief", "SKILL.md"),
        ]
        for path in paths:
            with open(path, encoding="utf-8") as handle:
                self.assertNotIn("\u2014", handle.read(), path)


if __name__ == "__main__":
    unittest.main()
