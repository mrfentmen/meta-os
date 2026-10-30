"""OS-094 first light: artifact references live on the job hash.

A job's full state must be readable from the queue by a worker that
never met the worker that wrote it: spec, progress note, and OS-083
artifact references. These tests pin the jobs.py side only: post
--artifacts, show, list --json, and the attach subcommand. They do
not claim a booted image, a driver deposit, or a live store read.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from helpers import RelayTestCase
import jobs

REF_A = "artifact:1/report.md@v1"
REF_B = "artifact:1/build/app.bin@v2"


class PostArtifactsTest(RelayTestCase):
    def test_post_stores_show_and_lists_artifacts(self):
        rc, out, err = self.run_cli(
            jobs.main, ["post", "--title", "T", "--spec", "s",
                        "--files", "a.py", "--deps", "9",
                        "--artifacts", REF_A + "," + REF_B])
        self.assertEqual(rc, 0)
        h, spec = jobs.job_get("1")
        self.assertEqual(h["artifacts"], REF_A + "," + REF_B)
        rc, out, err = self.run_cli(jobs.main, ["show", "1"])
        self.assertEqual(rc, 0)
        self.assertIn("artifacts: " + REF_A + "," + REF_B, out)
        rc, out, err = self.run_cli(jobs.main, ["list", "--json"])
        self.assertEqual(rc, 0)
        docs = json.loads(out)
        self.assertEqual(docs[0]["artifacts"], [REF_A, REF_B])
        # Existing fields are untouched by the new field.
        self.assertEqual(docs[0]["files"], "a.py")
        self.assertEqual(docs[0]["deps"], "9")

    def test_post_without_artifacts_has_empty_list(self):
        self.run_cli(jobs.main, ["post", "--title", "T", "--spec", "s"])
        rc, out, err = self.run_cli(jobs.main, ["list", "--json"])
        self.assertEqual(json.loads(out)[0]["artifacts"], [])

    def test_post_malformed_ref_rejected_before_any_state(self):
        for bad in ("1/report.md@v1",  # missing artifact: prefix
                    "artifact:1/../escape.md@v1",  # traversal
                    "artifact:1//empty.md@v1",  # empty segment
                    "artifact:1/abs.md@v0",  # versions count from 1
                    "artifact:1/no-version",  # no @v
                    "artifact:1/a.md@vX",  # non-numeric version
                    "artifact:bad!id/x.md@v1"):  # illegal job-id char
            rc, out, err = self.run_cli(
                jobs.main, ["post", "--title", "T", "--spec", "s",
                            "--artifacts", bad])
            self.assertEqual(rc, 2, bad)
            self.assertIn("malformed artifact reference", err, bad)
        # Rejection happens before the id sequence moves: nothing posted.
        rc, out, err = self.run_cli(jobs.main, ["list"])
        self.assertIn("NO_JOBS", out)

    def test_parse_artifact_ref_shape(self):
        self.assertEqual(jobs.parse_artifact_ref(REF_B),
                         ("1", "build/app.bin", 2))
        self.assertIsNone(jobs.parse_artifact_ref("artifact:1/a.md@v0"))
        self.assertIsNone(jobs.parse_artifact_ref("artifact:1/a\\b.md@v1"))
        self.assertIsNone(jobs.parse_artifact_ref(None))


class AttachTest(RelayTestCase):
    def setUp(self):
        super().setUp()
        self.run_cli(jobs.main, ["post", "--title", "T", "--spec", "s"])

    def test_attach_appends_and_dedupes_in_order(self):
        rc, out, err = self.run_cli(
            jobs.main, ["attach", "1", "--ref", REF_A])
        self.assertEqual(rc, 0)
        self.assertIn("ATTACHED 1 " + REF_A, out)
        rc, out, err = self.run_cli(
            jobs.main, ["attach", "1", "--ref", REF_B, "--ref", REF_A])
        self.assertEqual(rc, 0)
        h, _ = jobs.job_get("1")
        self.assertEqual(h["artifacts"], REF_A + "," + REF_B)

    def test_attach_duplicate_is_a_noop(self):
        self.run_cli(jobs.main, ["attach", "1", "--ref", REF_A])
        rc, out, err = self.run_cli(
            jobs.main, ["attach", "1", "--ref", REF_A])
        self.assertEqual(rc, 0)
        self.assertIn("already present", out)
        h, _ = jobs.job_get("1")
        self.assertEqual(h["artifacts"], REF_A)

    def test_attach_malformed_leaves_hash_unchanged(self):
        rc, out, err = self.run_cli(
            jobs.main, ["attach", "1", "--ref", "artifact:1/../x@v1"])
        self.assertEqual(rc, 2)
        self.assertIn("malformed artifact reference", err)
        h, _ = jobs.job_get("1")
        self.assertNotIn("artifacts", h)

    def test_attach_missing_job_errors(self):
        rc, out, err = self.run_cli(
            jobs.main, ["attach", "99", "--ref", REF_A])
        self.assertEqual(rc, 2)
        self.assertIn("no such job", err)


class ResumeFromRecordTest(RelayTestCase):
    def test_second_worker_reads_everything_from_the_record(self):
        # Worker 1: posts, claims, notes progress, attaches a deposit.
        self.run_cli(jobs.main, ["post", "--title", "Build it",
                                 "--spec", "Goal: ship the thing",
                                 "--files", "a.py,b.py"])
        self.run_cli(jobs.main, ["claim", "1"])
        self.run_cli(jobs.main, ["progress", "1",
                                 "--note", "a.py done, b.py half done"])
        self.run_cli(jobs.main, ["attach", "1", "--ref", REF_A])
        # Worker 1's session ends. Worker 2 never met worker 1; the
        # record alone must carry spec, progress, files, artifacts.
        self.set_nick("worker2", "host-b")
        h, spec = jobs.job_get("1")
        self.assertEqual(spec, "Goal: ship the thing")
        self.assertEqual(h["note"], "a.py done, b.py half done")
        self.assertEqual(h["files"], "a.py,b.py")
        self.assertEqual(h["artifacts"], REF_A)
        rc, out, err = self.run_cli(jobs.main, ["list", "--json"])
        doc = json.loads(out)[0]
        self.assertEqual(doc["artifacts"], [REF_A])
        self.assertEqual(doc["status"], "claimed")

    def test_attach_after_signing_keeps_signature_valid(self):
        secret_file = os.path.join(self.tmp, "job-secret")
        with open(secret_file, "wb") as f:
            f.write(b"crew-secret-abc\n")
        self.run_cli(jobs.main, ["post", "--title", "T", "--spec", "s",
                                 "--secret-file", secret_file])
        self.assertEqual(jobs.verify_job("1", {"default": b"crew-secret-abc"}),
                         "OK")
        self.run_cli(jobs.main, ["attach", "1", "--ref", REF_A])
        # The v2 payload covers identity fields only, so a later
        # attach must not invalidate the post-time signature.
        self.assertEqual(jobs.verify_job("1", {"default": b"crew-secret-abc"}),
                         "OK")


if __name__ == "__main__":
    unittest.main()
