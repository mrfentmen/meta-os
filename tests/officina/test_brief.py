"""Tests for the Officina stage-2a rough-words brief + self-iteration.

Run from the repo root:

    python3 -m unittest discover -s tests/officina -v

Offline and $0: the parser is rules in code, the only grader is
the stage-1 simulator plus the held-out gate, and no test trusts
a number the loop itself produced — the end-to-end test re-runs
the held-out gate independently on the final parameters.
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

from brief import (  # noqa: E402
    _volume_move,
    export_design,
    grading_conditions,
    iterate_brief,
    parse_rough_words,
    run_rough_words,
)
from design_loop import verify_proven  # noqa: E402
from heatsink import Conditions, HeatsinkParams, simulate  # noqa: E402

WORKED = ("i need a heatsink for a hot little chip, about 50mm "
          "square, no fan, keep it small, needs to stay cool under "
          "2 degrees per watt")


class TestParse(unittest.TestCase):
    def test_extracts_stated_facts(self):
        brief = parse_rough_words(
            "heatsink for a 30 watt chip, 50mm square, no fan, "
            "under 2 degrees per watt")
        self.assertEqual(brief["artefact_class"], "heatsink-fin-geometry")
        self.assertTrue(brief["gradeable"])
        reqs = {r["kind"]: r["value"] for r in brief["requirements"]}
        self.assertEqual(reqs["footprint_mm"], 50.0)
        self.assertEqual(reqs["power_w"], 30.0)
        self.assertTrue(reqs["passive_cooling"])
        target = next(t for t in brief["targets"]
                      if t["kind"] == "target_r_c_per_w")
        self.assertEqual(target["value"], 2.0)
        self.assertEqual(target["source"], "stated")

    def test_unknowns_are_gaps_not_inventions(self):
        brief = parse_rough_words("i need a heatsink")
        slots = {u["slot"] for u in brief["unknowns"]}
        self.assertIn("power_w", slots)
        self.assertIn("footprint_mm", slots)
        self.assertIn("target_r", slots)
        self.assertIn("airflow", slots)
        # No power was stated, so no power requirement may exist.
        self.assertNotIn(
            "power_w", {r["kind"] for r in brief["requirements"]})
        # The fallback target is labelled a workshop default, not a
        # stated fact.
        target = next(t for t in brief["targets"]
                      if t["kind"] == "target_r_c_per_w")
        self.assertEqual(target["source"], "workshop-default")

    def test_preferences_recorded_but_not_graded(self):
        brief = parse_rough_words(
            "cheap little heatsink, keep it small, no fan")
        prefs = {p["kind"] for p in brief["preferences"]}
        self.assertIn("compact", prefs)
        self.assertIn("low_cost", prefs)
        self.assertNotIn(
            "compact", {t["kind"] for t in brief["targets"]})
        self.assertNotIn(
            "low_cost", {t["kind"] for t in brief["targets"]})

    def test_unknown_class_is_ungradeable(self):
        brief = parse_rough_words("build me a better mousetrap")
        self.assertFalse(brief["gradeable"])
        self.assertIsNone(brief["artefact_class"])

    def test_footprint_conflict_recorded_not_rewritten(self):
        brief = parse_rough_words("heatsink 80mm square, no fan")
        self.assertEqual(len(brief["conflicts"]), 1)
        self.assertEqual(brief["conflicts"][0]["stated"], 80.0)
        self.assertEqual(brief["conflicts"][0]["class_value"], 50.0)

    def test_height_bound_parsed_both_wordings(self):
        for text in ("heatsink 25mm tall, no fan",
                     "heatsink, no taller than 25mm"):
            brief = parse_rough_words(text)
            self.assertEqual(brief["bounds"]["fin_height_mm_max"], 25.0)


class TestIterate(unittest.TestCase):
    def test_worked_run_proves_and_gate_agrees_independently(self):
        record = run_rough_words(WORKED)
        self.assertTrue(record["proven"])
        self.assertEqual(record["status"], "proven")
        # The test the loop didn't grade: re-run the held-out gate
        # here, from the final parameters, and demand agreement.
        params = HeatsinkParams(**record["final_params"])
        check = verify_proven(
            params, record["final_grade"]["r_th_c_per_w"])
        self.assertTrue(check["proven"])
        rules = [e["rule"] for e in record["brief"]["decision_log"]]
        self.assertIn("improve", rules)
        self.assertIn("accept", rules)

    def test_every_decision_logged_with_reason(self):
        record = run_rough_words(WORKED)
        log = record["brief"]["decision_log"]
        self.assertGreaterEqual(len(log), 2)
        for entry in log:
            self.assertIn("round", entry)
            self.assertIn("rule", entry)
            self.assertIn("decision", entry)
            self.assertTrue(entry["reason"])
        for amendment in record["brief"]["amendments"]:
            self.assertIn("round", amendment)
            self.assertIn("change", amendment)
            self.assertTrue(amendment["reason"])

    def test_height_bound_respected(self):
        record = run_rough_words(
            "heatsink, no taller than 25mm, under 2 degrees per watt")
        self.assertLessEqual(
            record["final_params"]["fin_height_mm"], 25.0)
        self.assertTrue(record["proven"])

    def test_gap_repair_rule_fires(self):
        brief = parse_rough_words("heatsink, no fan")
        brief["parameters"].update(
            {"fin_count": 28, "fin_thickness_mm": 2.0})
        record = iterate_brief(brief)
        rules = [e["rule"] for e in record["brief"]["decision_log"]]
        self.assertIn("gap repair", rules)

    def test_impossible_target_ends_unproven_not_falsely_proven(self):
        record = run_rough_words(
            "heatsink to cool a chip under 0.1 degrees per watt, "
            "no fan")
        self.assertFalse(record["proven"])
        self.assertTrue(record["status"].startswith("unproven"))
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "best.json")
            export_design(record, path)
            with open(path) as f:
                exported = json.load(f)
        self.assertFalse(exported["proven"])

    def test_ungradeable_run_claims_nothing(self):
        record = run_rough_words("build me a better mousetrap")
        self.assertEqual(record["status"], "ungradeable")
        self.assertFalse(record["proven"])
        self.assertIsNone(record["final_params"])

    def test_deterministic(self):
        first = run_rough_words(WORKED)
        second = run_rough_words(WORKED)
        self.assertEqual(
            json.dumps(first["brief"], sort_keys=True),
            json.dumps(second["brief"], sort_keys=True))
        self.assertEqual(first["final_params"], second["final_params"])


class TestForcedAirflowGrading(unittest.TestCase):
    # ML-001: a stated forced-airflow requirement used to be
    # parsed and then dropped — the run graded at passive h=10,
    # so this input produced the exact same design and R as the
    # passive demo. The requirement must flow into grading.
    PAX_EXAMPLE = ("cool a power supply in a hot garage, fan is "
                   "fine, cheap")

    def test_forced_airflow_grades_under_forced_conditions(self):
        brief = parse_rough_words(self.PAX_EXAMPLE)
        reqs = {r["kind"]: r["value"] for r in brief["requirements"]}
        self.assertTrue(reqs["forced_airflow"])
        self.assertEqual(
            grading_conditions(brief).h_w_m2k, 25.0)
        record = iterate_brief(brief)
        grade = record["final_grade"]
        self.assertEqual(grade["conditions"]["h_w_m2k"], 25.0)
        # Every grade the loop acted on was a forced grade.
        for entry in record["brief"]["decision_log"]:
            before = entry["grade_before"]
            if before is not None:
                self.assertEqual(
                    before["conditions"]["h_w_m2k"], 25.0)
        # The grade reproduces under forced conditions, not passive.
        params = HeatsinkParams(**record["final_params"])
        self.assertAlmostEqual(
            simulate(params, Conditions(h_w_m2k=25.0)).r_th_c_per_w,
            grade["r_th_c_per_w"], places=9)
        self.assertNotAlmostEqual(
            simulate(params, Conditions(h_w_m2k=10.0)).r_th_c_per_w,
            grade["r_th_c_per_w"], places=3)
        self.assertTrue(record["proven"])

    def test_passive_still_grades_at_natural_convection(self):
        record = run_rough_words(WORKED)
        self.assertEqual(
            record["final_grade"]["conditions"]["h_w_m2k"], 10.0)


class TestGapVolumeHeadroom(unittest.TestCase):
    # ML-003: the improve loop climbed fin height only — gap and
    # volume moves existed in code but never fired in a run.
    # When the best improving move is blocked, the loop must
    # exercise a gap/volume move whose two-step outcome improves
    # the grade, not stall and not climb height only.

    def test_gap_headroom_move_fires_and_improves(self):
        # Height capped at 40, add fins gap-blocked (gap would be
        # 0.667 mm), target 1.4 below the stall-point grade: the
        # old loop had no improving move here.
        brief = parse_rough_words("heatsink under 1.4 degrees per watt")
        brief["parameters"].update({
            "fin_height_mm": 40.0, "fin_thickness_mm": 2.0,
            "fin_count": 17, "base_thickness_mm": 8.0})
        stall_r = simulate(HeatsinkParams(
            fin_height_mm=40.0, fin_thickness_mm=2.0,
            fin_count=17, base_thickness_mm=8.0)).r_th_c_per_w
        record = iterate_brief(brief)
        log = record["brief"]["decision_log"]
        rules = [e["rule"] for e in log]
        self.assertIn("gap headroom", rules)
        self.assertIn("improve", rules)
        # The gap move comes first, then add fins fires on the
        # widened gap — the loop is no longer height-only.
        gap_at = rules.index("gap headroom")
        improve_at = next(
            i for i, e in enumerate(log)
            if e["rule"] == "improve" and "fin_count" in e["decision"])
        self.assertLess(gap_at, improve_at)
        self.assertIn("add fins", log[gap_at]["reason"])
        self.assertLess(
            record["final_grade"]["r_th_c_per_w"], stall_r)
        self.assertTrue(record["proven"])

    def test_volume_move_returns_thin_base(self):
        # Function-level pin: under the current bounds the loop
        # cannot reach volume repair from a feasible start (the
        # largest gap-feasible volume is about 92,000 mm^3
        # against a 100,000 budget), so this tests the move
        # itself, not a loop path — and says so.
        brief = parse_rough_words("heatsink")
        brief["parameters"]["base_thickness_mm"] = 8.0
        changes, reason = _volume_move(
            brief, {"violations": ["volume above budget"]})
        self.assertEqual(changes, {"base_thickness_mm": 7.0})
        self.assertIn("volume", reason)


if __name__ == "__main__":
    unittest.main()
