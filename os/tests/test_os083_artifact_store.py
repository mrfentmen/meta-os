"""tests/test_os083_artifact_store.py -- OS-083: the artifact store.

First light pins: deposits land versioned in a git-backed store,
job records carry artifact paths, and the three image routes bake
the store root. No booted image exists in this repo, so a deposit
on a booted image stays owed, as do driver deposits, jobs.py hash
integration (OS-094), and dashboard links (OS-084).

No bus post, no live Redis, no network: deposits run against
temporary directories plus local git only.
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mos import artifact_store


@unittest.skipUnless(shutil.which("git"), "git not available")
class ArtifactStoreTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="metaos-artifacts-")
        self.root = os.path.join(self.tmp, "artifacts")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_deposit_and_read_round_trip(self):
        record = artifact_store.deposit(
            self.root, "7", "report.md", "# done\n", author="pax")
        self.assertEqual(record["version"], 1)
        self.assertTrue(record["new_commit"])
        self.assertEqual(record["sha256"], hashlib.sha256(b"# done\n").hexdigest())
        self.assertEqual(record["size"], 7)
        self.assertEqual(record["reference"], "artifact:7/report.md@v1")
        self.assertEqual(record["path"], "jobs/7/report.md")
        self.assertEqual(artifact_store.read(self.root, "7", "report.md"), b"# done\n")

    def test_binary_bytes_survive_versioned_read(self):
        blob = bytes(range(256))
        artifact_store.deposit(self.root, "7", "out.bin", blob)
        artifact_store.deposit(self.root, "7", "out.bin", b"second")
        self.assertEqual(artifact_store.read(self.root, "7", "out.bin", 1), blob)
        self.assertEqual(artifact_store.read(self.root, "7", "out.bin", 2), b"second")
        self.assertEqual(artifact_store.read(self.root, "7", "out.bin"), b"second")

    def test_versions_increment_and_history_counts(self):
        artifact_store.deposit(self.root, "7", "a.txt", "one")
        artifact_store.deposit(self.root, "7", "a.txt", "two")
        record = artifact_store.deposit(self.root, "7", "a.txt", "three")
        self.assertEqual(record["version"], 3)
        hist = artifact_store.history(self.root, "7", "a.txt")
        self.assertEqual([h["version"] for h in hist], [1, 2, 3])
        self.assertEqual(len({h["commit"] for h in hist}), 3)

    def test_identical_redeposit_is_a_noop(self):
        artifact_store.deposit(self.root, "7", "a.txt", "same")
        before = artifact_store.history(self.root, "7", "a.txt")
        record = artifact_store.deposit(self.root, "7", "a.txt", "same")
        self.assertEqual(record["version"], 1)
        self.assertFalse(record["new_commit"])
        self.assertEqual(artifact_store.history(self.root, "7", "a.txt"), before)

    def test_nested_artifact_path(self):
        artifact_store.deposit(self.root, "7", "reports/summary.md", "x")
        self.assertEqual(
            artifact_store.read(self.root, "7", "reports/summary.md"), b"x")

    def test_traversal_names_refused(self):
        for bad in ("../escape.txt", "/abs.txt", "a/../b.txt", "a//b.txt", "", "."):
            with self.assertRaises(artifact_store.ArtifactStoreError):
                artifact_store.deposit(self.root, "7", bad, "x")

    def test_bad_job_ids_refused(self):
        for bad in ("", "a/b", "..", "job id"):
            with self.assertRaises(artifact_store.ArtifactStoreError):
                artifact_store.deposit(self.root, bad, "a.txt", "x")

    def test_list_sorted_and_empty_job_empty(self):
        self.assertEqual(artifact_store.list_artifacts(self.root, "9"), [])
        artifact_store.deposit(self.root, "9", "z.txt", "z")
        artifact_store.deposit(self.root, "9", "a.txt", "a")
        names = [r["name"] for r in artifact_store.list_artifacts(self.root, "9")]
        self.assertEqual(names, ["a.txt", "z.txt"])

    def test_read_missing_artifact_and_bad_version_raise(self):
        artifact_store.deposit(self.root, "7", "a.txt", "x")
        with self.assertRaises(artifact_store.ArtifactStoreError):
            artifact_store.read(self.root, "7", "nope.txt")
        with self.assertRaises(artifact_store.ArtifactStoreError):
            artifact_store.read(self.root, "7", "a.txt", 2)
        with self.assertRaises(artifact_store.ArtifactStoreError):
            artifact_store.read(self.root, "7", "a.txt", 0)

    def test_attach_copies_record_and_carries_paths(self):
        artifact_store.deposit(self.root, "7", "out.bin", b"data", author="milo")
        record = {"id": "7", "title": "demo job"}
        attached = artifact_store.attach(self.root, "7", record)
        self.assertNotIn("artifacts", record)
        self.assertEqual(attached["title"], "demo job")
        self.assertEqual(len(attached["artifacts"]), 1)
        entry = attached["artifacts"][0]
        self.assertEqual(entry["path"], "jobs/7/out.bin")
        self.assertEqual(entry["reference"], "artifact:7/out.bin@v1")
        self.assertEqual(entry["version"], 1)

    def test_cli_deposit_and_list(self):
        src = os.path.join(self.tmp, "in.txt")
        with open(src, "w", encoding="utf-8") as handle:
            handle.write("cli-data")
        rc = artifact_store.main(
            ["deposit", self.root, "7", "in.txt", src, "--author", "pax"])
        self.assertEqual(rc, 0)
        rc = artifact_store.main(["list", self.root, "7"])
        self.assertEqual(rc, 0)
        self.assertEqual(artifact_store.read(self.root, "7", "in.txt"), b"cli-data")

    def test_cli_bad_command_exits_two(self):
        self.assertEqual(artifact_store.main(["bogus", self.root, "7"]), 2)
        self.assertEqual(artifact_store.main([]), 2)


class ArtifactBakeTest(unittest.TestCase):
    """The three image routes bake the store root, empty plus marker."""

    def read(self, rel):
        with open(os.path.join(ROOT, rel), encoding="utf-8") as handle:
            return handle.read()

    def test_build_image_bakes_store_root(self):
        text = self.read("os/build-image.sh")
        self.assertIn("2c. OS-083", text)
        self.assertIn("/var/lib/metaos/artifacts", text)
        self.assertIn(".metaos-artifact-store", text)
        self.assertIn("chown relay:relay /var/lib/metaos/artifacts", text)

    def test_build_live_stages_store_root(self):
        text = self.read("os/build-live.sh")
        self.assertIn("OS-083", text)
        self.assertIn("/var/lib/metaos/artifacts", text)
        self.assertIn(".metaos-artifact-store", text)

    def test_packer_bakes_store_root(self):
        text = self.read("os/packer/metaos.pkr.hcl")
        self.assertIn("/var/lib/metaos/artifacts", text)
        self.assertIn(".metaos-artifact-store", text)
        self.assertIn("chown -R relay:relay /var/lib/metaos/artifacts", text)

    @unittest.skipUnless(shutil.which("bash"), "bash not available")
    def test_build_scripts_parse(self):
        for rel in ("os/build-image.sh", "os/build-live.sh"):
            proc = subprocess.run(
                ["bash", "-n", os.path.join(ROOT, rel)],
                capture_output=True, text=True, timeout=30)
            self.assertEqual(proc.returncode, 0, proc.stderr)

    def test_no_em_dash_in_new_module(self):
        with open(os.path.join(ROOT, "mos", "artifact_store.py"),
                  encoding="utf-8") as handle:
            self.assertNotIn("\u2014", handle.read())


if __name__ == "__main__":
    unittest.main()
