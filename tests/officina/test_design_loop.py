"""Pinning tests for the Officina design-job loop and held-out gate.

Run from the repo root:

    python3 -m unittest discover -s tests/officina -v

Offline and $0: no model calls, no network, no bus. The loop
replays exactly from its seed, every failure carries its score,
and the gate accepts and rejects on the documented paths.
"""

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(
    0,
    os.path.join(
        os.path.dirname(__file__), "..", "..", "os", "worlds",
        "officina", "runtime",
    ),
)

from design_loop import (  # noqa: E402
    DesignBoard,
    export_best,
    run_loop,
    select_proven,
    verify_proven,
)
from heatsink import HeatsinkParams, simulate  # noqa: E402


class TestBoard(unittest.TestCase):
    def test_claim_is_ordered_and_atomic(self):
        board = DesignBoard()
        first = board.post(HeatsinkParams(10.0, 1.0, 10, 3.0))
        second = board.post(HeatsinkParams(20.0, 1.0, 10, 3.0))
        self.assertIs(board.claim(), first)
        self.assertIs(board.claim(), second)
        self.assertIsNone(board.claim())

    def test_complete_and_fail_carry_scores(self):
        board = DesignBoard()
        job = board.post(HeatsinkParams(10.0, 1.0, 10, 3.0))
        board.claim()
        board.complete(job, 2.5)
        self.assertEqual((job.status, job.score), ("done", 2.5))
        bad = board.post(HeatsinkParams(40.0, 3.0, 30, 8.0))
        board.claim()
        board.fail(bad, 9.9, "volume")
        self.assertEqual(
            (bad.status, bad.score, bad.failure_reason),
            ("failed", 9.9, "volume"),
        )


class TestLoop(unittest.TestCase):
    def test_seeded_replay_is_exact(self):
        first = run_loop(50, 7)
        second = run_loop(50, 7)
        self.assertEqual(first["jobs"], second["jobs"])
        self.assertEqual(
            first["score_curve_best_so_far"],
            second["score_curve_best_so_far"],
        )

    def test_every_failure_carries_score_and_reason(self):
        record = run_loop(60, 11)
        self.assertGreater(len(record["failures"]), 0)
        for failure in record["failures"]:
            self.assertEqual(failure["status"], "failed")
            self.assertIsNotNone(failure["score_r_th_c_per_w"])
            self.assertTrue(failure["failure_reason"])

    def test_done_jobs_are_feasible_and_winners_sorted(self):
        record = run_loop(60, 11)
        for job in record["jobs"]:
            if job["status"] == "done":
                self.assertTrue(
                    simulate(HeatsinkParams(**job["params"])).feasible
                )
        scores = [w["score_r_th_c_per_w"] for w in record["winners"]]
        self.assertEqual(scores, sorted(scores))

    def test_curve_is_best_so_far(self):
        record = run_loop(60, 11)
        curve = record["score_curve_best_so_far"]
        self.assertEqual(len(curve), 60)
        seen = [c for c in curve if c is not None]
        self.assertEqual(seen, sorted(seen, reverse=True))
        self.assertEqual(seen[-1], record["best"]["score_r_th_c_per_w"])

    def test_overnight_seed_proves_a_winner(self):
        # Under the original bounds this seed's raw best failed
        # held out and the gate proved the second winner. The
        # 2026-11-01 bounds widening (fin height 40 -> 80, base
        # 8 -> 12) changed the sampled space: the raw best now
        # proves on the first attempt. The skip behaviour itself
        # is pinned deterministically by the next test.
        record = run_loop(240, 20261101)
        selection = select_proven(record)
        self.assertIsNotNone(selection["proven_best"])
        self.assertTrue(selection["verification"]["proven"])
        self.assertEqual(len(selection["attempts"]), 1)
        self.assertEqual(
            selection["proven_best"]["score_r_th_c_per_w"],
            record["best"]["score_r_th_c_per_w"],
        )

    def test_select_proven_skips_unproven_raw_best(self):
        # The gate must skip a raw best that fails held out and
        # prove the next winner instead of exporting an unproven
        # design. Constructed record: the raw best is feasible as
        # drawn but its fin gap falls below minimum under the
        # held-out thickness tolerance; the second winner proves.
        raw_best = HeatsinkParams(30.0, 0.69, 30, 4.0)
        robust = HeatsinkParams(30.0, 1.0, 20, 4.0)
        record = {"winners": [
            {"params": raw_best.as_dict(),
             "score_r_th_c_per_w": simulate(raw_best).r_th_c_per_w},
            {"params": robust.as_dict(),
             "score_r_th_c_per_w": simulate(robust).r_th_c_per_w},
        ]}
        selection = select_proven(record)
        self.assertEqual(len(selection["attempts"]), 2)
        self.assertFalse(selection["attempts"][0]["proven"])
        self.assertTrue(selection["verification"]["proven"])
        self.assertEqual(
            selection["proven_best"]["params"], robust.as_dict())
        self.assertGreater(
            selection["proven_best"]["score_r_th_c_per_w"],
            record["winners"][0]["score_r_th_c_per_w"],
        )

    def test_export_never_claims_unproven(self):
        record = run_loop(240, 20261101)
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "best.json")
            export_best(record, path)
            payload = json.load(open(path))
        self.assertTrue(payload["proven"])
        self.assertEqual(
            payload["best"], select_proven(record)["proven_best"]
        )


class TestGate(unittest.TestCase):
    ROBUST = HeatsinkParams(30.0, 1.0, 20, 4.0)
    GAP_EDGE = HeatsinkParams(30.0, 0.69, 30, 4.0)

    def test_robust_design_proves(self):
        claimed = simulate(self.ROBUST).r_th_c_per_w
        verification = verify_proven(self.ROBUST, claimed)
        self.assertTrue(verification["fresh_agrees"])
        self.assertTrue(verification["heldout_feasible"])
        self.assertTrue(verification["proven"])

    def test_tampered_claim_is_rejected(self):
        claimed = simulate(self.ROBUST).r_th_c_per_w + 1.0
        verification = verify_proven(self.ROBUST, claimed)
        self.assertFalse(verification["fresh_agrees"])
        self.assertFalse(verification["proven"])

    def test_gap_edge_fails_held_out(self):
        # Feasible as drawn, infeasible under tolerance: the gate
        # must catch a design with no manufacturing margin.
        claimed = simulate(self.GAP_EDGE).r_th_c_per_w
        verification = verify_proven(self.GAP_EDGE, claimed)
        self.assertTrue(verification["fresh_agrees"])
        self.assertFalse(verification["heldout_feasible"])
        self.assertFalse(verification["proven"])


if __name__ == "__main__":
    unittest.main()
