"""Tests for the multi-model wiring in the crew: SAM 3.1
segmentation on the flag path (TRIO_SAM_SEGMENT=1) and the Muse
Wonder second reader for review (TRIO_REVIEW_WONDER=1), plus
models.chat_image itself.

Everything here is offline: the model seams (models.segment,
models.chat_image, models._post) are stubbed, NO live call is ever
made. The behaviours pinned:

  * segment success lands a "segment" timeline step carrying the
    region, with the prompt taken from the first observation's
    description;
  * segment failure lands an error step and never raises — the
    flag pipeline stands on its assessments either way;
  * Wonder review produces the reading itself (the queue assess
    seam is not called), and the review step names reader wonder;
  * a failed Wonder call falls back to the Spark queue reading,
    and the step names reader spark WITH the fallback recorded;
  * with the flag off, review never touches Wonder;
  * chat_image refuses non-chat-surface models and sends the
    frame as an image_url data-URL part.
"""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")
sys.path.insert(0, QUEUE_DIR)

os.environ.pop("SPARK_API_KEY", None)
os.environ.pop("TRIO_SAM_SEGMENT", None)
os.environ.pop("TRIO_REVIEW_WONDER", None)
os.environ.pop("TRIO_JUDGE_MODEL", None)

import crew  # noqa: E402
import crew_records  # noqa: E402
import models  # noqa: E402

FRAME = b"\xff\xd8" + bytes(range(64))
CAM = {"id": "cam-a", "name": "1 Ave @ 84 St", "area": "Manhattan",
       "latitude": 40.7755, "longitude": -73.9502,
       "imageUrl": "https://example.invalid/cam-a/image"}
TS = "2026-11-02T10:00:00.000Z"


def v2_assessment(category, description="a visible thing"):
    return {
        "product": "vigiles",
        "timestamp": TS,
        "observations": [{
            "category": category, "description": description,
            "evidence": "test fixture", "confidence": None,
            "region": None}],
        "assessment": {"category": category,
                       "summary": "test summary",
                       "uncertainty": [],
                       "requires_human_review": True},
        "processing": {"model": "stub", "latency_ms": None},
    }


def ok_result(category):
    return {"status": "ok", "job_id": "job-1", "model": "muse-spark-1.3",
            "latency_ms": 11, "assessment": v2_assessment(category)}


class CrewHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="trio-model-wiring-")
        self.records = crew_records.CrewRecords(self.tmp)
        self.records.create_incident({"id": "incident-t",
                                      "status": "candidate"})
        self.assess_calls = []

        def assess(product, image_bytes, timestamp):
            self.assess_calls.append((product, timestamp))
            return ok_result("visible flame")

        self.crew = crew.Crew(
            self.records, assess, lambda camera: FRAME,
            lambda package: {"receipt_id": "sim-test"})
        self._env = unittest.mock.patch.dict(os.environ, {}, clear=False)
        self._env.start()

    def tearDown(self):
        self._env.stop()
        for var in ("TRIO_SAM_SEGMENT", "TRIO_REVIEW_WONDER"):
            os.environ.pop(var, None)

    def timeline(self):
        return self.records.get_incident("incident-t")["timeline"]


class SegmentTests(CrewHarness):
    def test_segment_success_records_region_and_prompt(self):
        fake = {"box_px": {"x1": 1, "y1": 2, "x2": 3, "y2": 4},
                "image_size": {"w": 100, "h": 100},
                "region": {"x": 10, "y": 20, "w": 30, "h": 40},
                "mask": None, "model": "sam-3.1", "latency_ms": 42,
                "raw_text_len": 99}
        with unittest.mock.patch.object(
                crew.models, "segment", return_value=fake) as seg:
            step = self.crew._run_segment(
                "incident-t", "vigiles", "visible flame",
                ok_result("visible flame"), FRAME)
        seg.assert_called_once()
        # The prompt is the first observation's description.
        self.assertEqual(seg.call_args[0][1], "a visible thing")
        self.assertEqual(step["step"], "segment")
        self.assertEqual(step["region"],
                         {"x": 10, "y": 20, "w": 30, "h": 40})
        self.assertNotIn("error", step)
        self.assertEqual(self.timeline()[-1]["step"], "segment")

    def test_segment_failure_records_error_and_never_raises(self):
        with unittest.mock.patch.object(
                crew.models, "segment",
                side_effect=RuntimeError("SAM response carried no "
                                         "output text")):
            step = self.crew._run_segment(
                "incident-t", "vigiles", "visible flame",
                ok_result("visible flame"), FRAME)
        self.assertEqual(step["step"], "segment")
        self.assertIn("no output text", step["error"])
        self.assertNotIn("region", step)


class WonderReviewTests(CrewHarness):
    def _run_review(self):
        first = ok_result("visible flame")
        return self.crew._run_review(
            "incident-t", CAM, "vigiles", FRAME, TS,
            first_category="visible flame", first_result=first)

    def test_wonder_reader_produces_the_review(self):
        os.environ["TRIO_REVIEW_WONDER"] = "1"
        payload = json.dumps(v2_assessment("visible flame"))
        with unittest.mock.patch.object(
                crew.models, "chat_image",
                return_value=(payload, "muse-wonder-1.0", 7)) as ci:
            review, verdict = self._run_review()
        ci.assert_called_once()
        self.assertEqual(self.assess_calls, [])
        self.assertEqual(review["reader"], "wonder")
        self.assertEqual(review["model"], "muse-wonder-1.0")
        self.assertIsNone(review["job_id"])
        step = [s for s in self.timeline() if s["step"] == "review"][-1]
        self.assertEqual(step["reader"], "wonder")
        self.assertIsNone(step["reader_fallback"])

    def test_wonder_failure_falls_back_to_spark_named(self):
        os.environ["TRIO_REVIEW_WONDER"] = "1"
        with unittest.mock.patch.object(
                crew.models, "chat_image",
                side_effect=RuntimeError("boom")):
            review, verdict = self._run_review()
        self.assertEqual(len(self.assess_calls), 1)
        self.assertEqual(review["model"], "muse-spark-1.3")
        step = [s for s in self.timeline() if s["step"] == "review"][-1]
        self.assertEqual(step["reader"], "spark")
        self.assertIn("Wonder review unavailable", step["reader_fallback"])

    def test_flag_off_never_touches_wonder(self):
        with unittest.mock.patch.object(
                crew.models, "chat_image",
                side_effect=AssertionError("must not be called")):
            review, verdict = self._run_review()
        self.assertEqual(len(self.assess_calls), 1)
        step = [s for s in self.timeline() if s["step"] == "review"][-1]
        self.assertEqual(step["reader"], "spark")
        self.assertIsNone(step["reader_fallback"])


class ChatImageTests(unittest.TestCase):
    def test_chat_image_sends_frame_and_returns_text(self):
        seen = {}

        def fake_post(url, body, kind):
            seen["body"] = body
            seen["kind"] = kind
            return {"choices": [{"message": {"content": "hello"}}],
                    "model": "muse-wonder-1.0"}, 5

        with tempfile.TemporaryDirectory() as td, \
                unittest.mock.patch.dict(
                    os.environ,
                    {"METAOS_MODEL_RECEIPTS": os.path.join(
                        td, "receipts.jsonl")}), \
                unittest.mock.patch.object(models, "_post", fake_post):
            text, model, latency = models.chat_image(
                models.WONDER, "describe", FRAME)
        self.assertEqual((text, model, latency),
                         ("hello", "muse-wonder-1.0", 5))
        parts = seen["body"]["messages"][0]["content"]
        self.assertEqual(parts[0], {"type": "text", "text": "describe"})
        self.assertEqual(parts[1]["type"], "image_url")
        self.assertTrue(parts[1]["image_url"]["url"].startswith(
            "data:image/jpeg;base64,"))

    def test_chat_image_refuses_non_chat_surface(self):
        with self.assertRaises(models.EndpointUnresolvedError):
            models.chat_image(models.SAM, "describe", FRAME)


if __name__ == "__main__":
    unittest.main()
