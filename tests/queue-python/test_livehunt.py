"""Tests for livehunt.py — the bounded live-flag hunt.

Run from the repo root (same command as the queue suite):

    python3 -m unittest discover -s tests/queue-python -v

Everything here is offline: the generate/fetch/dispatch seams are
faked, NO live Spark call and NO live camera fetch is ever made.
The flag rule, baselines, and the crew pipeline are the REAL ones
(crew.py + js/command-flag.js) — only the model and the network are
stubbed, the same discipline as test_crew.py.
"""
import json
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")

for var in ("TRIO_SAM_SEGMENT", "TRIO_REVIEW_WONDER", "TRIO_JUDGE_MODEL"):
    os.environ.pop(var, None)

sys.path.insert(0, QUEUE_DIR)

import crew as crew_mod  # noqa: E402
import crew_records  # noqa: E402
import livehunt  # noqa: E402

FRAME = b"\xff\xd8\xff\xe0" + bytes(range(256)) * 4  # JPEG magic + payload

BASELINE = {"vigiles": "normal activity",
            "ignis": "no hazard visible",
            "medicus": "normal activity"}


def make_camera(idx):
    return {"id": f"cam-{idx}", "name": f"Hunt St @ {idx} Ave",
            "latitude": 40.60 + 0.001 * idx,
            "longitude": -73.98 - 0.001 * idx,
            "area": "Brooklyn", "isOnline": "true",
            "imageUrl": f"https://example.invalid/cam-{idx}/image"}


def contract_for(product, timestamp, category):
    return {
        "product": product,
        "timestamp": timestamp,
        "observations": [{
            "category": category,
            "description": f"fake reading: {category}",
            "evidence": "center of frame",
            "confidence": None,
        }],
        "assessment": {
            "category": category,
            "summary": f"fake summary: {category}",
            "uncertainty": ["fake uncertainty"],
            "requires_human_review": True,
        },
        "processing": {"model": "fake-model", "latency_ms": 3},
    }


class FakeGenerate:
    """spark_gen.generate stand-in. script maps product -> list of
    categories to return in order; after the list, the product's
    baseline. flag_first_two makes vigiles flag twice (patrol +
    review) and then read baseline, like a confirmed real flag."""

    def __init__(self, script=None):
        self.script = {k: list(v) for k, v in (script or {}).items()}
        self.calls = []

    def __call__(self, product, image_path, timestamp):
        with open(image_path, "rb") as fh:
            data = fh.read()
        assert data[0:2] == b"\xff\xd8", "assessor must pass a JPEG path"
        self.calls.append(product)
        queue = self.script.get(product) or []
        category = queue.pop(0) if queue else BASELINE[product]
        return contract_for(product, timestamp, category), "fake-model", 3


class FakeDispatch:
    def __init__(self):
        self.packages = []

    def __call__(self, package):
        self.packages.append(package)
        return {"receipt_id": "sim-fake-0001", "status": "accepted"}


def make_hunt(tmp, generate, cameras, fetch=None, dispatch=None,
              **hunt_kwargs):
    records = crew_records.CrewRecords(os.path.join(tmp, "crew-data"))
    dispatch = dispatch or FakeDispatch()
    crew_obj = crew_mod.Crew(
        records, livehunt.DirectAssessor(generate_fn=generate),
        fetch or (lambda camera: FRAME), dispatch, cameras=cameras)
    kwargs = dict(frame_source="fake frames", camera_source="fake-list",
                  guardrail_status=lambda: {"remaining_usd": 100.0,
                                            "calls": 0,
                                            "est_cost_usd": 0.0})
    kwargs.update(hunt_kwargs)
    return crew_obj, records, dispatch, kwargs


class TestDirectAssessor(unittest.TestCase):
    def test_wraps_generate_tuple_in_crew_shape(self):
        gen = FakeGenerate()
        assessor = livehunt.DirectAssessor(generate_fn=gen)
        result = assessor("vigiles", FRAME, "2026-11-02T20:00:00.000Z")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["model"], "fake-model")
        self.assertEqual(result["latency_ms"], 3)
        self.assertEqual(
            result["assessment"]["assessment"]["category"],
            "normal activity")
        import crew_common
        self.assertEqual(
            result["job_id"],
            crew_common.job_id_for("vigiles",
                                   "2026-11-02T20:00:00.000Z", FRAME))

    def test_refuses_non_jpeg_frame(self):
        assessor = livehunt.DirectAssessor(generate_fn=FakeGenerate())
        with self.assertRaises(ValueError):
            assessor("vigiles", b"<html>error page</html>",
                     "2026-11-02T20:00:00.000Z")

    def test_generate_failure_propagates(self):
        def boom(product, path, timestamp):
            raise RuntimeError("model down")
        assessor = livehunt.DirectAssessor(generate_fn=boom)
        with self.assertRaises(RuntimeError):
            assessor("vigiles", FRAME, "2026-11-02T20:00:00.000Z")


class TestRunHunt(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="livehunt-test-")

    def test_baseline_run_exhausts_and_files_record(self):
        cameras = [make_camera(i) for i in range(3)]
        crew_obj, records, dispatch, kwargs = make_hunt(
            self.tmp, FakeGenerate(), cameras)
        out_path = os.path.join(self.tmp, "hunt.json")
        record = livehunt.run_hunt(crew_obj, cameras, records,
                                   out_path=out_path, **kwargs)
        self.assertEqual(record["frames_checked"], 3)
        self.assertEqual(record["stop_reason"], "exhausted")
        self.assertIsNone(record["flagged"])
        self.assertEqual([o["outcome"] for o in record["outcomes"]],
                         ["baseline"] * 3)
        self.assertEqual([o["division"] for o in record["outcomes"]],
                         ["vigiles", "ignis", "medicus"])
        self.assertEqual(dispatch.packages, [])
        with open(out_path, encoding="utf-8") as fh:
            filed = json.load(fh)
        self.assertEqual(filed["frames_checked"], 3)
        self.assertIsNone(filed["flagged"])

    def test_max_frames_caps_the_hunt(self):
        cameras = [make_camera(i) for i in range(5)]
        crew_obj, records, dispatch, kwargs = make_hunt(
            self.tmp, FakeGenerate(), cameras)
        record = livehunt.run_hunt(crew_obj, cameras, records,
                                   max_frames=2, **kwargs)
        self.assertEqual(record["frames_checked"], 2)
        self.assertEqual(record["stop_reason"], "max-frames")

    def test_confirmed_flag_dispatches_simulated_and_stops(self):
        cameras = [make_camera(i) for i in range(3)]
        gen = FakeGenerate({"vigiles": ["person down", "person down"]})
        crew_obj, records, dispatch, kwargs = make_hunt(
            self.tmp, gen, cameras)
        record = livehunt.run_hunt(crew_obj, cameras, records, **kwargs)
        self.assertEqual(record["stop_reason"], "flag-dispatched")
        self.assertEqual(record["frames_checked"], 1)
        flagged = record["flagged"]
        self.assertIsNotNone(flagged)
        self.assertEqual(flagged["category"], "person down")
        self.assertEqual(flagged["dispatch"]["receipt_id"],
                         "sim-fake-0001")
        self.assertTrue(flagged["dispatch"]["simulated"])
        self.assertEqual(len(dispatch.packages), 1)
        self.assertTrue(dispatch.packages[0]["simulated"])

    def test_budget_reserve_stops_before_any_assessment(self):
        cameras = [make_camera(0)]
        gen = FakeGenerate()
        crew_obj, records, dispatch, kwargs = make_hunt(
            self.tmp, gen, cameras,
            guardrail_status=lambda: {"remaining_usd": 4.50})
        record = livehunt.run_hunt(crew_obj, cameras, records, **kwargs)
        self.assertEqual(record["stop_reason"], "budget-reserve")
        self.assertEqual(record["frames_checked"], 0)
        self.assertEqual(gen.calls, [])
        self.assertEqual(dispatch.packages, [])

    def test_feed_error_recorded_and_hunt_continues(self):
        cameras = [make_camera(0), make_camera(1)]

        def fetch(camera):
            if camera["id"] == "cam-0":
                raise RuntimeError("egress blocked")
            return FRAME

        crew_obj, records, dispatch, kwargs = make_hunt(
            self.tmp, FakeGenerate(), cameras, fetch=fetch)
        record = livehunt.run_hunt(crew_obj, cameras, records, **kwargs)
        self.assertEqual([o["outcome"] for o in record["outcomes"]],
                         ["feed-error", "baseline"])
        self.assertEqual(record["stop_reason"], "exhausted")

    def test_cleared_flag_does_not_stop_or_dispatch(self):
        cameras = [make_camera(0), make_camera(1)]
        gen = FakeGenerate(
            {"vigiles": ["possible altercation", "normal activity"]})
        crew_obj, records, dispatch, kwargs = make_hunt(
            self.tmp, gen, cameras)
        record = livehunt.run_hunt(crew_obj, cameras, records, **kwargs)
        self.assertEqual(record["outcomes"][0]["outcome"],
                         "cleared-by-review")
        self.assertIsNone(record["flagged"])
        self.assertEqual(dispatch.packages, [])
        self.assertEqual(record["frames_checked"], 2)


class TestStagedFrames(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="livehunt-staged-")

    def _write_staged(self, cameras):
        for cam in cameras:
            with open(os.path.join(self.tmp, f"{cam['id']}.jpg"),
                      "wb") as fh:
                fh.write(FRAME)
        with open(os.path.join(self.tmp, "manifest.json"), "w",
                  encoding="utf-8") as fh:
            json.dump({"captured_at": "2026-11-02T20:30:00Z",
                       "note": "browser capture, sandbox egress blocked",
                       "cameras": cameras}, fh)

    def test_loads_manifest_and_serves_frames(self):
        cameras = [make_camera(0), make_camera(1)]
        self._write_staged(cameras)
        staged = livehunt.StagedFrames(self.tmp)
        self.assertEqual([c["id"] for c in staged.cameras()],
                         ["cam-0", "cam-1"])
        self.assertEqual(staged(cameras[0]), FRAME)
        self.assertIn("2026-11-02T20:30:00Z", staged.describe())

    def test_missing_frame_raises_named_error(self):
        cameras = [make_camera(0), make_camera(9)]
        self._write_staged(cameras[:1])
        staged = livehunt.StagedFrames(self.tmp)
        with self.assertRaises(livehunt.LiveHuntError):
            staged(cameras[1])

    def test_missing_manifest_raises_named_error(self):
        with self.assertRaises(livehunt.LiveHuntError):
            livehunt.StagedFrames(self.tmp)


if __name__ == "__main__":
    unittest.main()
