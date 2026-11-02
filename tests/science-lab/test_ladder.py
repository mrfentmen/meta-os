"""Science Lab ladder tests: promotion rules, export guard, experiment caps.

stdlib unittest only. Run from the repo root, e.g.::

    python3 -m unittest discover -s tests/science-lab -v
    python3 tests/science-lab/test_ladder.py
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import ladder  # noqa: E402


class TestLevels(unittest.TestCase):
    def test_levels_cover_0_to_6_with_status_and_meaning(self):
        for level in range(7):
            self.assertIn(level, ladder.LEVELS)
            self.assertIn("status", ladder.LEVELS[level])
            self.assertIn("meaning", ladder.LEVELS[level])
            self.assertTrue(ladder.LEVELS[level]["status"])
            self.assertTrue(ladder.LEVELS[level]["meaning"])

    def test_level_names_match_pack(self):
        self.assertEqual(ladder.LEVELS[0]["status"], "Idea")
        self.assertEqual(ladder.LEVELS[3]["status"], "Independently reproduced")
        self.assertEqual(ladder.LEVELS[4]["status"], "Experimentally validated")


class TestCanPromote(unittest.TestCase):
    def test_valid_promotion_0_to_1(self):
        self.assertTrue(ladder.can_promote(
            0, 1, "pinned_source_claims", "unverified", False))
        self.assertTrue(ladder.can_promote(
            0, 1, "pinned_source_claims", "unverified", is_human=False))

    def test_valid_promotion_1_to_2(self):
        self.assertTrue(ladder.can_promote(
            1, 2, "computational_result", "unverified", False))

    def test_valid_promotion_2_to_3_with_reproduced(self):
        self.assertTrue(ladder.can_promote(
            2, 3, "independent_reproduction", "reproduced", False))

    def test_2_to_3_requires_reproduced(self):
        self.assertFalse(ladder.can_promote(
            2, 3, "independent_reproduction", "unverified", False))
        self.assertFalse(ladder.can_promote(
            2, 3, "independent_reproduction", "mismatch", False))
        self.assertFalse(ladder.can_promote(
            2, 3, "computational_result", "reproduced", False))

    def test_refusal_3_to_4_automated(self):
        # Automated path must never grant level 4: False or raise.
        try:
            ok = ladder.can_promote(
                3, 4, "human_physical_experiment", "reproduced", False)
        except NotImplementedError as exc:
            self.assertIn("UNIMPLEMENTED", str(exc))
            return
        self.assertFalse(ok)

    def test_refusal_3_to_4_automated_default_flag(self):
        try:
            ok = ladder.can_promote(
                3, 4, "human_physical_experiment", "reproduced")
        except NotImplementedError as exc:
            self.assertIn("UNIMPLEMENTED", str(exc))
            return
        self.assertFalse(ok)

    def test_no_automated_path_to_5_or_6(self):
        for target in (4, 5, 6):
            current = target - 1
            try:
                ok = ladder.can_promote(
                    current, target, "human_physical_experiment",
                    "reproduced", False)
            except NotImplementedError:
                continue
            self.assertFalse(ok)

    def test_human_path_above_3_allowed_with_experiment_evidence(self):
        self.assertTrue(ladder.can_promote(
            3, 4, "human_physical_experiment", "reproduced", True))

    def test_no_skips_or_downgrades(self):
        self.assertFalse(ladder.can_promote(
            0, 2, "computational_result", "unverified", False))
        self.assertFalse(ladder.can_promote(
            2, 2, "computational_result", "reproduced", False))
        self.assertFalse(ladder.can_promote(
            2, 1, "pinned_source_claims", "unverified", False))

    def test_next_required_points_up_one_rung(self):
        self.assertIn("pinned", ladder.next_required(0).lower())
        self.assertIn("computational", ladder.next_required(1).lower())
        self.assertIn("reproduc", ladder.next_required(2).lower())

    def test_next_required_3_is_human_only(self):
        text = ladder.next_required(3)
        self.assertIn("UNIMPLEMENTED", text)
        self.assertIn("human", text.lower())


class TestExportGuard(unittest.TestCase):
    def test_over_level_export_blocked(self):
        with self.assertRaises(ValueError):
            ladder.assert_export_allowed(2, 3)

    def test_over_level_export_blocked_other_direction_pair(self):
        # A second pair: displaying even one rung too high is blocked.
        with self.assertRaises(ValueError):
            ladder.assert_export_allowed(0, 1)
        with self.assertRaises(ValueError):
            ladder.assert_export_allowed(3, 4)

    def test_equal_and_under_level_allowed(self):
        ladder.assert_export_allowed(2, 2)
        ladder.assert_export_allowed(3, 2)
        ladder.assert_export_allowed(3, 0)

    def test_guard_accepts_claim_dict(self):
        # The CLI passes a claim dict as record_level.
        ladder.assert_export_allowed({"evidence_level": 2}, 2)
        with self.assertRaises(ValueError):
            ladder.assert_export_allowed({"evidence_level": 2}, 3)


class TestExperimentCap(unittest.TestCase):
    def test_unverified_caps_at_2(self):
        self.assertEqual(ladder.cap_for_experiment("unverified", False), 2)
        self.assertEqual(ladder.cap_for_experiment("unverified", True), 2)

    def test_mismatch_caps_at_2(self):
        self.assertEqual(ladder.cap_for_experiment("mismatch", False), 2)
        self.assertEqual(ladder.cap_for_experiment("mismatch", True), 2)

    def test_reproduced_supports_3(self):
        self.assertEqual(ladder.cap_for_experiment("reproduced", False), 3)
        self.assertEqual(ladder.cap_for_experiment("reproduced", True), 3)

    def test_no_path_returns_above_3(self):
        for status in ("unverified", "mismatch", "reproduced"):
            for pred in (False, True):
                self.assertLessEqual(
                    ladder.cap_for_experiment(status, pred), 3)

    def test_unknown_status_raises(self):
        with self.assertRaises(ValueError):
            ladder.cap_for_experiment("bogus", False)


if __name__ == "__main__":
    unittest.main()
