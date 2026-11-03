"""CB2-454 — Officina's loop harness record shape, read from the run files.

`os/worlds/officina/runtime/brief.py` writes one record per briefed run:
a decision log (one entry per round), the amendments the loop applied, and
the final grade. `design_loop.py` writes the stage-1 harness record, one
entry per design job. Both are real files in `os/worlds/officina/runs/`, so
the shape is asserted against what the loop actually wrote, never a
hand-built copy.
"""

import json
import unittest
from pathlib import Path

RUNS = Path(__file__).resolve().parents[2] / "os/worlds/officina/runs"
BRIEFED = RUNS / "forced-airflow-run-001.json"
HARNESS = RUNS / "overnight-run-001.json"


def load(path):
    with path.open(encoding="utf-8") as fh:
        return json.load(fh)


class LoopRecordShape(unittest.TestCase):
    def setUp(self):
        self.record = load(BRIEFED)

    def test_run_record_carries_the_documented_top_level_fields(self):
        for key in (
            "rough_input",
            "brief",
            "rounds_used",
            "final_params",
            "final_grade",
            "verification",
            "proven",
            "status",
        ):
            self.assertIn(key, self.record, f"run record is missing {key}")
        self.assertIsInstance(self.record["rounds_used"], int)
        self.assertIsInstance(self.record["proven"], bool)
        self.assertIsInstance(self.record["final_params"], dict)
        self.assertIsInstance(self.record["final_grade"], dict)

    def test_every_amendment_names_its_round_change_and_reason(self):
        amendments = self.record["brief"]["amendments"]
        self.assertTrue(amendments, "the worked run applied at least one amendment")
        for entry in amendments:
            self.assertIsInstance(entry["round"], int)
            self.assertGreaterEqual(entry["round"], 1, "rounds are one-based")
            for field in ("change", "reason"):
                self.assertIsInstance(entry[field], str)
                self.assertTrue(entry[field].strip(), f"{field} is never blank")

    def test_every_decision_log_entry_carries_its_result(self):
        log = self.record["brief"]["decision_log"]
        self.assertTrue(log, "the loop logs its decisions")
        for entry in log:
            self.assertIsInstance(entry["round"], int)
            for field in ("rule", "decision", "reason"):
                self.assertIsInstance(entry[field], str)
                self.assertTrue(entry[field].strip(), f"{field} is never blank")
            self.assertIn("grade_before", entry, "a null grade is still a field")
            self.assertIsInstance(entry["params_after"], dict)
            # The intake round has no parameters before it, and says so with
            # null rather than an empty dict that would read as "no change".
            if entry["round"] == 0:
                self.assertIsNone(entry["params_before"])
            else:
                self.assertIsInstance(entry["params_before"], dict)

    def test_rounds_used_matches_the_highest_logged_round(self):
        log = self.record["brief"]["decision_log"]
        highest = max(entry["round"] for entry in log)
        self.assertEqual(
            self.record["rounds_used"],
            highest,
            "the count and the last round number agree; no round is lost",
        )
        # Every amendment belongs to a round the log also recorded.
        logged = {entry["round"] for entry in log}
        for entry in self.record["brief"]["amendments"]:
            self.assertIn(entry["round"], logged, "an amendment has no matching round")


class HarnessRecordShape(unittest.TestCase):
    def setUp(self):
        self.record = load(HARNESS)

    def test_jobs_carry_status_score_and_named_failure(self):
        jobs = self.record["jobs"]
        self.assertTrue(jobs)
        for job in jobs:
            for key in ("job_id", "params", "status", "score_r_th_c_per_w", "failure_reason"):
                self.assertIn(key, job, f"job record is missing {key}")
            self.assertIsInstance(job["job_id"], int)
            self.assertIn(job["status"], ("done", "failed"))
            # A failed job names why; a done job carries no failure reason.
            if job["status"] == "failed":
                self.assertTrue(
                    isinstance(job["failure_reason"], str) and job["failure_reason"].strip(),
                    f"failed job {job['job_id']} must name its violation",
                )
            else:
                self.assertIsNone(job["failure_reason"])

    def test_every_failure_also_appears_in_the_failure_ledger(self):
        failed = {j["job_id"] for j in self.record["jobs"] if j["status"] == "failed"}
        ledger = {j["job_id"] for j in self.record["failures"]}
        self.assertEqual(failed, ledger, "a failed design is never silently dropped")

    def test_winners_are_the_feasible_jobs_in_score_order(self):
        winners = self.record["winners"]
        scores = [w["score_r_th_c_per_w"] for w in winners]
        self.assertEqual(scores, sorted(scores), "winners are kept best-first")
        for winner in winners:
            self.assertEqual(winner["status"], "done")
            self.assertIsNone(winner["failure_reason"])


if __name__ == "__main__":
    unittest.main()
