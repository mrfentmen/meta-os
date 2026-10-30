"""tests/test_os128_disk_audit.py -- OS-128: the disk-state audit.

First light pins: a cold reader reconstructs every job's spec,
goal, progress, remaining files, artifacts, and settled
decisions from disk alone, and files a named leak per layer
for anything it cannot reconstruct. No booted image exists in
this repo, so a kill-every-process run on a real mid-work
machine stays owed, as does the live jobs.py export to disk.

No bus post, no live Redis, no network: the audit runs
against temporary directories plus local git only.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from mos import artifact_store, disk_audit, memory


def _job(job_id, **overrides):
    record = {
        "id": job_id,
        "title": "Rebuild the widget",
        "status": "claimed",
        "claim": "pax",
        "spec": "Goal: rebuild the widget\nFiles: widget.py\n",
        "files": ["widget.py", "widget_test.py"],
        "completed_files": ["widget.py"],
        "note": "widget.py rebuilt, tests still to run",
        "accept": "widget tests pass",
    }
    record.update(overrides)
    return record


@unittest.skipUnless(shutil.which("git"), "git not available")
class DiskAuditTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="metaos-disk-audit-")
        self.memory_root = os.path.join(self.tmp, "memory")
        self.artifact_root = os.path.join(self.tmp, "artifacts")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_clean_job_reconstructs_fully(self):
        memory.write_shared(self.memory_root, "decisions/widget",
                             "widget ships muted, not bright")
        artifact_store.deposit(self.artifact_root, "7", "report.md",
                               "# done\n", author="pax")
        record = _job("7", artifacts=["artifact:7/report.md@v1"],
                      decisions=["decisions/widget"])
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        self.assertTrue(result["passed"])
        self.assertEqual(result["leaks"], [])
        job = result["jobs"][0]
        self.assertEqual(job["goal"], "rebuild the widget")
        self.assertEqual(job["progress_notes"],
                         ["widget.py rebuilt, tests still to run"])
        self.assertEqual(job["remaining_files"], ["widget_test.py"])
        self.assertEqual(job["artifacts"], ["artifact:7/report.md@v1"])
        self.assertEqual(job["decisions"], ["decisions/widget"])
        self.assertEqual(result["decisions"], ["decisions/widget"])

    def test_open_job_with_no_progress_is_not_a_leak(self):
        record = _job("8", status="open", claim=None, note=None)
        del record["note"]
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        self.assertTrue(result["passed"])
        self.assertEqual(result["jobs"][0]["progress_notes"], [])

    def test_goal_key_beats_spec_goal_line(self):
        record = _job("9", goal="ship the widget quietly")
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        self.assertEqual(result["jobs"][0]["goal"],
                         "ship the widget quietly")

    def test_missing_spec_is_a_spec_leak(self):
        record = _job("10", spec=None)
        del record["spec"]
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        self.assertFalse(result["passed"])
        layers = [leak["layer"] for leak in result["leaks"]]
        self.assertIn("spec", layers)
        # No spec text also means no Goal: line, so a baton leak
        # alongside the spec leak is correct, not a second bug.
        self.assertIn("baton", layers)

    def test_claimed_job_without_goal_is_a_baton_leak(self):
        record = _job("11", spec="No goal line here\n")
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        layers = [leak["layer"] for leak in result["leaks"]]
        self.assertIn("baton", layers)
        self.assertFalse(result["passed"])

    def test_claimed_job_without_claimer_is_a_claim_leak(self):
        record = _job("12", claim=None)
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        layers = [leak["layer"] for leak in result["leaks"]]
        self.assertIn("claim", layers)
        self.assertFalse(result["passed"])

    def test_artifact_version_mismatch_is_an_artifacts_leak(self):
        artifact_store.deposit(self.artifact_root, "13", "report.md",
                               "# done\n", author="pax")
        record = _job("13", artifacts=["artifact:13/report.md@v2"])
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        layers = [leak["layer"] for leak in result["leaks"]]
        self.assertIn("artifacts", layers)
        self.assertEqual(result["jobs"][0]["artifacts"], [])

    def test_artifact_with_no_manifest_is_an_artifacts_leak(self):
        record = _job("14", artifacts=["artifact:14/report.md@v1"])
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        layers = [leak["layer"] for leak in result["leaks"]]
        self.assertIn("artifacts", layers)

    def test_unparseable_artifact_reference_is_an_artifacts_leak(self):
        record = _job("15", artifacts=["report.md"])
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        layers = [leak["layer"] for leak in result["leaks"]]
        self.assertIn("artifacts", layers)

    def test_missing_decision_is_a_memory_leak(self):
        record = _job("16", decisions=["decisions/never-written"])
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        layers = [leak["layer"] for leak in result["leaks"]]
        self.assertIn("memory", layers)

    def test_decision_in_claimers_own_journal_counts(self):
        memory.write(self.memory_root, "pax", "decisions/widget",
                     "widget ships muted")
        record = _job("17", decisions=["decisions/widget"])
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        self.assertTrue(result["passed"])
        self.assertEqual(result["jobs"][0]["decisions"],
                         ["decisions/widget"])

    def test_corrupt_shared_journal_is_a_memory_journal_leak(self):
        memory.write_shared(self.memory_root, "decisions/widget", "muted")
        journal = os.path.join(self.memory_root, "shared", "journal.jsonl")
        with open(journal, "a", encoding="utf-8") as handle:
            handle.write("this is not a journal entry\n")
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [_job("18")])
        layers = [leak["layer"] for leak in result["leaks"]]
        self.assertIn("memory-journal", layers)
        self.assertFalse(result["passed"])

    def test_non_object_record_is_a_record_leak(self):
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  ["not a record"])
        layers = [leak["layer"] for leak in result["leaks"]]
        self.assertIn("record", layers)

    def test_record_without_id_is_a_record_leak(self):
        record = _job("19")
        del record["id"]
        result = disk_audit.audit(self.memory_root, self.artifact_root,
                                  [record])
        layers = [leak["layer"] for leak in result["leaks"]]
        self.assertIn("record", layers)

    def test_missing_store_roots_read_as_empty(self):
        result = disk_audit.audit(
            os.path.join(self.tmp, "no-memory"),
            os.path.join(self.tmp, "no-artifacts"),
            [_job("20", status="open", claim=None)])
        self.assertTrue(result["passed"])

    def test_audit_rejects_a_non_list(self):
        with self.assertRaises(disk_audit.DiskAuditError):
            disk_audit.audit(self.memory_root, self.artifact_root,
                             {"id": "21"})

    def test_cli_pass_exit_zero_and_leak_exit_one(self):
        jobs_path = os.path.join(self.tmp, "jobs.json")
        with open(jobs_path, "w", encoding="utf-8") as handle:
            json.dump([_job("22", status="open", claim=None)], handle)
        proc = subprocess.run(
            [sys.executable, "-m", "mos.disk_audit",
             "--jobs", jobs_path,
             "--memory-root", self.memory_root,
             "--artifact-root", self.artifact_root],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("PASS", proc.stdout)
        with open(jobs_path, "w", encoding="utf-8") as handle:
            json.dump([_job("23", spec=None)], handle)
            # spec=None writes null; the audit must still file spec.
        proc = subprocess.run(
            [sys.executable, "-m", "mos.disk_audit",
             "--jobs", jobs_path,
             "--memory-root", self.memory_root,
             "--artifact-root", self.artifact_root],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("LEAK", proc.stdout)

    def test_cli_missing_jobs_file_exits_two(self):
        proc = subprocess.run(
            [sys.executable, "-m", "mos.disk_audit",
             "--jobs", os.path.join(self.tmp, "absent.json"),
             "--memory-root", self.memory_root,
             "--artifact-root", self.artifact_root],
            cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("RELAY_ERROR", proc.stderr)


if __name__ == "__main__":
    unittest.main()
