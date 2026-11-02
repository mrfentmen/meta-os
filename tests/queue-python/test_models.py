"""Tests for the multi-model client (server/queue/models.py).
Offline: transports are faked; the SAM fixture follows the exact
output format verified live against sam-3.1 on 2026-11-02."""
import json
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402

SAM_TEXT = ("<|box;x1=8;y1=0;x2=599;y2=354;w=600;h=470|>"
            "<|mask;x=0;y=0;data=355,592,FAKEENCODED|>")


class SamParseTests(unittest.TestCase):
    def test_box_and_region_on_contract_scale(self):
        rec = models.parse_sam_text(SAM_TEXT)
        self.assertEqual(rec["box_px"],
                         {"x1": 8, "y1": 0, "x2": 599, "y2": 354})
        self.assertEqual(rec["image_size"], {"w": 600, "h": 470})
        self.assertEqual(rec["region"],
                         {"x": 13, "y": 0, "w": 985, "h": 753})
        self.assertEqual(rec["mask"]["data"], "355,592,FAKEENCODED")

    def test_no_box_raises_never_invents(self):
        with self.assertRaises(ValueError):
            models.parse_sam_text("no segments here")

    def test_malformed_box_raises(self):
        with self.assertRaises(ValueError):
            models.parse_sam_text(
                "<|box;x1=9;y1=0;x2=5;y2=3;w=600;h=470|>")


class FormatTests(unittest.TestCase):
    def test_magic_bytes(self):
        self.assertEqual(models.detect_image_format(
            b"\x89PNG\r\n\x1a\nrest"), "png")
        self.assertEqual(models.detect_image_format(
            b"\xff\xd8\xff\xe0rest"), "jpeg")
        self.assertEqual(models.detect_image_format(
            b"RIFFxxxxWEBPrest"), "webp")
        self.assertEqual(models.detect_image_format(b"????"), "unknown")


class ChatTests(unittest.TestCase):
    def test_chat_text_returns_text_and_writes_receipt(self):
        payload = {"model": "muse-wonder-1.0",
                   "choices": [{"message": {"content": "hello"}}],
                   "usage": {"prompt_tokens": 3, "completion_tokens": 1}}
        with tempfile.TemporaryDirectory() as td:
            receipts = os.path.join(td, "receipts.jsonl")
            with unittest.mock.patch.dict(
                    os.environ, {"METAOS_MODEL_RECEIPTS": receipts}), \
                    unittest.mock.patch.object(
                        models.spark_guardrail, "record",
                        return_value=0.0), \
                    unittest.mock.patch.object(
                        models, "_post",
                        return_value=(payload, 42)) as post:
                text, reported, latency = models.chat_text(
                    models.WONDER, "say hello")
            self.assertEqual(text, "hello")
            self.assertEqual(reported, "muse-wonder-1.0")
            self.assertEqual(latency, 42)
            post.assert_called_once()
            lines = open(receipts).read().strip().splitlines()
            self.assertEqual(len(lines), 1)
            rec = json.loads(lines[0])
            self.assertEqual(rec["model"], "muse-wonder-1.0")
            self.assertEqual(rec["kind"], "chat:muse-wonder-1.0")
            self.assertIsNone(rec["est_cost_usd"])  # no published rate

    def test_non_chat_model_refused(self):
        with self.assertRaises(models.EndpointUnresolvedError):
            models.chat_text(models.SAM, "hello")


class VoiceTests(unittest.TestCase):
    def test_transcribe_raises_until_surface_verified(self):
        with self.assertRaises(models.EndpointUnresolvedError):
            models.transcribe(b"\xff\xfb fake mp3 bytes")


if __name__ == "__main__":
    unittest.main()
