"""sam_spark.py: SAM-regions -> Spark-reasoning pipeline (offline tests).

Everything here runs on fixtures with the network blocked: no model
call, no key, no bus. The live providers are tested only for refusal
(no SPARK_API_KEY -> LiveNotConfigured, nothing sent).
"""
import json
import os
import socket
import sys
import unittest
from unittest import mock

OS_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(OS_ROOT)
sys.path.insert(0, os.path.join(OS_ROOT, "intel"))

import sam_spark as pipeline  # noqa: E402

SAM_DIR = os.path.join(OS_ROOT, "intel", "evals", "sam")
SCENARIOS = os.path.join(REPO_ROOT, "eval", "ignis", "scenarios.json")


class CaptureLedger:
    def __init__(self):
        self.entries = []

    def record_spend(self, entry):
        self.entries.append(dict(entry))
        return entry


def no_network(test_fn):
    def wrapper(*args, **kwargs):
        def blocked(*a, **k):
            raise AssertionError("network used in fixture mode")
        with mock.patch.object(socket, "socket", blocked), \
                mock.patch.object(socket, "create_connection", blocked):
            return test_fn(*args, **kwargs)
    wrapper.__name__ = test_fn.__name__
    return wrapper


class FixtureSegmentTests(unittest.TestCase):
    def _png(self, name):
        with open(os.path.join(SAM_DIR, name), "rb") as fh:
            return fh.read()

    def test_quiet_halves_yield_no_regions(self):
        for name in ("alerts-quiet-desktop.png",
                     "alerts-quiet-phone.png"):
            seg = pipeline.fixture_segments(self._png(name), name)
            self.assertEqual(seg["regions"], [])
            self.assertEqual(seg["model"], pipeline.FIXTURE_SAM_MODEL)

    def test_firing_halves_yield_one_stable_region(self):
        for name in ("alerts-firing-desktop.png",
                     "alerts-firing-phone.png"):
            data = self._png(name)
            first = pipeline.fixture_segments(data, name)
            second = pipeline.fixture_segments(data, name)
            self.assertEqual(len(first["regions"]), 1)
            self.assertEqual(first["regions"], second["regions"])
            box = first["regions"][0]
            for key in ("x", "y", "w", "h"):
                self.assertIsInstance(box[key], int)
            self.assertLessEqual(box["x"] + box["w"], 1000)
            self.assertLessEqual(box["y"] + box["h"], 1000)

    def test_non_png_raises(self):
        with self.assertRaises(pipeline.PipelineError):
            pipeline.fixture_segments(b"\xff\xd8fake-jpeg", "x-firing.png")
        with self.assertRaises(pipeline.PipelineError):
            pipeline.fixture_segments(b"", "x-quiet.png")

    def test_image_size_matches_ihdr(self):
        data = self._png("alerts-quiet-desktop.png")
        seg = pipeline.fixture_segments(data, "alerts-quiet-desktop.png")
        w, h = pipeline.png_size(data)
        self.assertEqual(seg["image_size"], {"w": w, "h": h})


class FixtureReasonTests(unittest.TestCase):
    def test_sam_verdict_keys_off_regions(self):
        self.assertEqual(
            pipeline.fixture_reason_sam("p", [{"x": 1, "y": 2, "w": 3,
                                               "h": 4}])["label"],
            "build-broken")
        self.assertEqual(pipeline.fixture_reason_sam("p", [])["label"],
                         "build-ok")

    def test_ignis_assessment_keys_off_regions(self):
        scenario = {"scenario_id": "IGN-001", "review_expected": True}
        hit = pipeline.fixture_reason_ignis(scenario, [{"x": 1, "y": 1,
                                                        "w": 1, "h": 1}])
        miss = pipeline.fixture_reason_ignis(scenario, [])
        self.assertEqual(hit["category"], "visible smoke")
        self.assertEqual(miss["category"], "no hazard visible")
        self.assertTrue(hit["requires_human_review"])


class OfflineRunTests(unittest.TestCase):
    @no_network
    def test_sam_pairs_score_against_manifest(self):
        ledger = CaptureLedger()
        sam = pipeline.run_sam_pairs(
            SAM_DIR, pipeline.fixture_segments,
            pipeline.fixture_reason_sam,
            lambda lane, ti, to, usage="estimated":
            pipeline.record_call_spend(ledger, lane, ti, to, usage))
        self.assertEqual(sam["sample_size"], 4)
        self.assertEqual(sam["errors"], 0)
        # The fixture keys off the filename convention, so this
        # exercises the harness, not detection -- and it must be 4/4.
        self.assertEqual(sam["correct"], 4)
        self.assertEqual(sam["accuracy"], 1.0)
        self.assertEqual(len(ledger.entries), 4)
        for entry in ledger.entries:
            for key in ("ts", "lane_feature", "tokens_in",
                        "tokens_out", "est_cost", "usage"):
                self.assertIn(key, entry)
            self.assertEqual(entry["lane_feature"],
                             "sam-spark:sam-pairs")
            self.assertGreaterEqual(entry["est_cost"], 0)

    @no_network
    def test_ignis_scores_against_ground_truth(self):
        ledger = CaptureLedger()
        with open(SCENARIOS) as fh:
            scenarios = json.load(fh)["scenarios"]
        self.assertEqual(len(scenarios), 20)
        ignis = pipeline.run_ignis(
            scenarios, pipeline.fixture_regions_for_scenario,
            pipeline.fixture_reason_ignis,
            lambda lane, ti, to, usage="estimated":
            pipeline.record_call_spend(ledger, lane, ti, to, usage))
        m = ignis["metrics"]
        self.assertEqual(m["sample_size"], 20)
        self.assertEqual(m["errors"]["count"], 0)
        assessed = [r for r in ignis["records"] if r["error"] is None]
        self.assertEqual(len(assessed), 20)
        self.assertEqual(m["true_positives"] + m["false_positives"]
                         + m["true_negatives"] + m["false_negatives"], 20)
        for key in ("precision", "recall", "false_positive_rate",
                    "false_negative_rate", "category_accuracy"):
            self.assertTrue(m[key] is None
                            or 0.0 <= m[key] <= 1.0, key)
        # Documented fixture miss: visible-flame truths are called
        # smoke -- the alert still fires, the category is wrong.
        flames = [r for r in ignis["records"]
                  if r["ground_truth_label"] == "visible flame"]
        self.assertTrue(flames)
        for r in flames:
            self.assertEqual(r["actual_category"], "visible smoke")
            self.assertTrue(r["alert_correct"])
            self.assertFalse(r["category_correct"])
        self.assertEqual(len(ledger.entries), 20)

    @no_network
    def test_est_cost_math(self):
        self.assertEqual(pipeline.estimate_cost(1_000_000, 1_000_000),
                         round(1.25 + 4.25, 6))
        entry, ok = pipeline.record_call_spend(
            CaptureLedger(), "lane", 400, 40, now=1700000000)
        self.assertTrue(ok)
        self.assertEqual(entry["ts"], 1700000000)
        self.assertEqual(entry["est_cost"],
                         pipeline.estimate_cost(400, 40))

    @no_network
    def test_ledger_failure_stays_local(self):
        class Boom:
            def record_spend(self, entry):
                raise RuntimeError("no bus offline")
        entry, ok = pipeline.record_call_spend(Boom(), "lane", 4, 4)
        self.assertFalse(ok)
        self.assertIn("est_cost", entry)


class LiveRefusalTests(unittest.TestCase):
    def test_live_refuses_without_key(self):
        env = {k: v for k, v in os.environ.items()
               if k != "SPARK_API_KEY"}
        with mock.patch.dict(os.environ, env, clear=True):
            with self.assertRaises(pipeline.LiveNotConfigured):
                pipeline.live_reason_ignis(
                    {"scenario_id": "IGN-001",
                     "expected_observable_condition": "smoke"}, [])
            with self.assertRaises(pipeline.LiveNotConfigured):
                pipeline.live_segments(b"bytes", "prompt")

    def test_cli_live_exits_before_any_call(self):
        env = {k: v for k, v in os.environ.items()
               if k != "SPARK_API_KEY"}
        with mock.patch.dict(os.environ, env, clear=True):
            rc = pipeline.main(["--mode", "live", "--sam-dir", SAM_DIR,
                                "--scenarios", SCENARIOS])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
