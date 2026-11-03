"""Bench-3 build-out: the model paths the earlier suites did not
pin. Offline throughout — every transport seam is stubbed, no live
call is ever made.

  * Judge v2 at CREW level (TRIO_JUDGE_MODEL=1): the model ruling
    actually decides (a model reject clears two agreeing flagged
    readings); judge_mode on the timeline says which ruling ruled;
    a failed model call falls back to combine() with the fallback
    NAMED in judge_reasons; a failed review never reaches the
    model judge at all.
  * models.segment() end to end over a stubbed transport: record
    shape, the no-output-text raise, and the box-less ValueError
    propagating instead of an invented region. Plus parse_sam_text
    edges: missing mask, empty/None text, zero width, full-frame
    region, multiline mask data.
  * models.generate_image(): base64 result decoded + format
    detected; a response with no image item raises.
  * models.chat_text(): list content parts joined; a response
    with no content raises instead of returning a fabrication.
  * Wonder review fallback on UNPARSEABLE Wonder output (not just
    a raised call): non-JSON text and a JSON non-object both fall
    back to the Spark queue reading with the fallback named.
"""
import base64
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
SAM_TEXT = ("<|box;x1=8;y1=0;x2=599;y2=354;w=600;h=470|>"
            "<|mask;x=0;y=0;data=355,592,FAKEENCODED|>")


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


def judge_reply(verdict, category="visible flame",
                reasons=("decided on both readings",)):
    return json.dumps({"verdict": verdict, "category": category,
                       "reasons": list(reasons), "confidence": None})


class CrewHarness(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="trio-bench3-")
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
        for var in ("TRIO_SAM_SEGMENT", "TRIO_REVIEW_WONDER",
                    "TRIO_JUDGE_MODEL"):
            os.environ.pop(var, None)

    def timeline(self):
        return self.records.get_incident("incident-t")["timeline"]

    def review_step(self):
        return [s for s in self.timeline() if s["step"] == "review"][-1]

    def run_review(self):
        first = ok_result("visible flame")
        return self.crew._run_review(
            "incident-t", CAM, "vigiles", FRAME, TS,
            first_category="visible flame", first_result=first)


class JudgeModelCrewTests(CrewHarness):
    def test_model_ruling_decides_and_mode_is_model(self):
        os.environ["TRIO_JUDGE_MODEL"] = "1"
        with unittest.mock.patch.object(
                crew.models, "chat_text",
                return_value=(judge_reply("confirm"),
                              "muse-spark-1.3", 5)):
            review, verdict = self.run_review()
        self.assertEqual(verdict, "confirmed")
        step = self.review_step()
        self.assertEqual(step["judge_mode"], "model")
        self.assertTrue(any("model judge ruling" in r
                            for r in step["judge_reasons"]))

    def test_model_reject_clears_two_agreeing_flagged_readings(self):
        # combine() alone would confirm (both readings flag and
        # agree); the model judge's reject must be what rules.
        os.environ["TRIO_JUDGE_MODEL"] = "1"
        with unittest.mock.patch.object(
                crew.models, "chat_text",
                return_value=(judge_reply("reject", "normal activity",
                                           ("a look-alike",)),
                              "muse-spark-1.3", 5)):
            review, verdict = self.run_review()
        self.assertEqual(verdict, "cleared")
        self.assertEqual(self.review_step()["judge_mode"], "model")

    def test_model_failure_falls_back_to_combine_named(self):
        os.environ["TRIO_JUDGE_MODEL"] = "1"
        with unittest.mock.patch.object(
                crew.models, "chat_text",
                side_effect=RuntimeError("HTTP 500")):
            review, verdict = self.run_review()
        # combine() on two agreeing flagged readings: confirmed.
        self.assertEqual(verdict, "confirmed")
        step = self.review_step()
        self.assertEqual(step["judge_mode"], "deterministic")
        self.assertIn("model judge unavailable",
                      step["judge_reasons"][0])
        self.assertIn("deterministic ruling used",
                      step["judge_reasons"][0])
        self.assertTrue(any("two independent readings agree" in r
                            for r in step["judge_reasons"]))

    def test_failed_review_never_reaches_the_model_judge(self):
        os.environ["TRIO_JUDGE_MODEL"] = "1"

        def failing_assess(product, image_bytes, timestamp):
            raise RuntimeError("queue is down")

        crew2 = crew.Crew(self.records, failing_assess,
                          lambda camera: FRAME,
                          lambda package: {"receipt_id": "sim-test"})
        with unittest.mock.patch.object(
                crew.models, "chat_text",
                side_effect=AssertionError("must not be called")):
            first = ok_result("visible flame")
            review, verdict = crew2._run_review(
                "incident-t", CAM, "vigiles", FRAME, TS,
                first_category="visible flame", first_result=first)
        self.assertEqual(verdict, "inconclusive")
        self.assertEqual(self.review_step()["judge_mode"],
                         "deterministic")

    def test_flag_off_model_judge_never_called(self):
        with unittest.mock.patch.object(
                crew.models, "chat_text",
                side_effect=AssertionError("must not be called")):
            review, verdict = self.run_review()
        self.assertEqual(verdict, "confirmed")
        step = self.review_step()
        self.assertEqual(step["judge_mode"], "deterministic")
        self.assertFalse(any("model judge unavailable" in r
                             for r in step["judge_reasons"]))


class WonderUnparseableFallbackTests(CrewHarness):
    def _run_with_wonder_text(self, text):
        os.environ["TRIO_REVIEW_WONDER"] = "1"
        with unittest.mock.patch.object(
                crew.models, "chat_image",
                return_value=(text, "muse-wonder-1.0", 7)):
            return self.run_review()

    def test_non_json_wonder_text_falls_back_named(self):
        review, verdict = self._run_with_wonder_text("flames, probably")
        self.assertEqual(len(self.assess_calls), 1)
        step = self.review_step()
        self.assertEqual(step["reader"], "spark")
        self.assertIn("Wonder review unavailable",
                      step["reader_fallback"])

    def test_json_non_object_wonder_text_falls_back_named(self):
        review, verdict = self._run_with_wonder_text('["visible flame"]')
        self.assertEqual(len(self.assess_calls), 1)
        step = self.review_step()
        self.assertEqual(step["reader"], "spark")
        self.assertIn("did not parse to a JSON object",
                      step["reader_fallback"])


class SegmentEndToEndTests(unittest.TestCase):
    def _segment(self, payload):
        with tempfile.TemporaryDirectory() as td, \
                unittest.mock.patch.dict(
                    os.environ,
                    {"METAOS_MODEL_RECEIPTS": os.path.join(
                        td, "receipts.jsonl")}), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "record", return_value=0.0), \
                unittest.mock.patch.object(
                    models, "_post", return_value=(payload, 33)):
            return models.segment(b"\xff\xd8frame", "the person")

    def _payload(self, text):
        return {"model": "sam-3.1", "output": [{
            "type": "message", "content": [
                {"type": "output_text", "text": text}]}]}

    def test_segment_record_shape(self):
        rec = self._segment(self._payload(SAM_TEXT))
        self.assertEqual(rec["box_px"],
                         {"x1": 8, "y1": 0, "x2": 599, "y2": 354})
        self.assertEqual(rec["region"],
                         {"x": 13, "y": 0, "w": 985, "h": 753})
        self.assertEqual(rec["model"], "sam-3.1")
        self.assertEqual(rec["latency_ms"], 33)
        self.assertEqual(rec["raw_text_len"], len(SAM_TEXT))

    def test_segment_no_output_text_raises(self):
        with self.assertRaises(RuntimeError) as cm:
            self._segment({"model": "sam-3.1", "output": []})
        self.assertIn("no output text", str(cm.exception))

    def test_segment_boxless_text_raises_never_invents(self):
        with self.assertRaises(ValueError):
            self._segment(self._payload("nothing segmented here"))


class SamParseEdgeTests(unittest.TestCase):
    def test_missing_mask_is_none(self):
        rec = models.parse_sam_text(
            "<|box;x1=0;y1=0;x2=10;y2=10;w=100;h=100|>")
        self.assertIsNone(rec["mask"])

    def test_empty_and_none_text_raise(self):
        with self.assertRaises(ValueError):
            models.parse_sam_text("")
        with self.assertRaises(ValueError):
            models.parse_sam_text(None)

    def test_zero_width_box_raises(self):
        with self.assertRaises(ValueError):
            models.parse_sam_text(
                "<|box;x1=0;y1=0;x2=5;y2=5;w=0;h=470|>")

    def test_full_frame_box_maps_to_full_contract_region(self):
        rec = models.parse_sam_text(
            "<|box;x1=0;y1=0;x2=600;y2=470;w=600;h=470|>")
        self.assertEqual(rec["region"],
                         {"x": 0, "y": 0, "w": 1000, "h": 1000})

    def test_multiline_mask_data_captured(self):
        rec = models.parse_sam_text(
            "<|box;x1=0;y1=0;x2=10;y2=10;w=100;h=100|>"
            "<|mask;x=1;y=2;data=line1\nline2|>")
        self.assertEqual(rec["mask"],
                         {"x": 1, "y": 2, "data": "line1\nline2"})


class GenerateImageTests(unittest.TestCase):
    def _generate(self, payload):
        with tempfile.TemporaryDirectory() as td, \
                unittest.mock.patch.dict(
                    os.environ,
                    {"METAOS_MODEL_RECEIPTS": os.path.join(
                        td, "receipts.jsonl")}), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "record", return_value=0.0), \
                unittest.mock.patch.object(
                    models, "_post", return_value=(payload, 9)):
            return models.generate_image("draw a thing")

    def test_generate_decodes_base64_and_detects_format(self):
        png = b"\x89PNG\r\n\x1a\n" + b"fakedata"
        payload = {"model": "muse-image-1.0", "output": [{
            "type": "image_generation_call",
            "result": base64.b64encode(png).decode()}]}
        data, fmt, reported, latency = self._generate(payload)
        self.assertEqual(data, png)
        self.assertEqual(fmt, "png")
        self.assertEqual(reported, "muse-image-1.0")
        self.assertEqual(latency, 9)

    def test_generate_without_image_item_raises(self):
        payload = {"model": "muse-image-1.0", "output": [{
            "type": "message", "content": [
                {"type": "output_text", "text": "no image"}]}]}
        with self.assertRaises(RuntimeError) as cm:
            self._generate(payload)
        self.assertIn("no image result", str(cm.exception))


class ChatTextContentTests(unittest.TestCase):
    def _chat(self, payload):
        with tempfile.TemporaryDirectory() as td, \
                unittest.mock.patch.dict(
                    os.environ,
                    {"METAOS_MODEL_RECEIPTS": os.path.join(
                        td, "receipts.jsonl")}), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "record", return_value=0.0), \
                unittest.mock.patch.object(
                    models, "_post", return_value=(payload, 3)):
            return models.chat_text(models.SPARK, "hi")

    def test_list_content_parts_joined_text_only(self):
        payload = {"model": "muse-spark-1.3", "choices": [{
            "message": {"content": [
                {"type": "text", "text": "ab"},
                {"type": "image_url", "image_url": {"url": "x"}},
                {"type": "text", "text": "cd"}]}}]}
        text, reported, latency = self._chat(payload)
        self.assertEqual(text, "abcd")

    def test_no_content_raises_never_fabricates(self):
        payload = {"model": "muse-spark-1.3", "choices": []}
        with self.assertRaises(RuntimeError) as cm:
            self._chat(payload)
        self.assertIn("no message content", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
