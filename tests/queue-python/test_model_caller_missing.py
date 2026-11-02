"""Missing-case tests for the model caller (B240).

Covers what the transport tests in test_queue.py do not: text unwrapping,
content-part joining, prompt sections and the correction channel, the
JPEG magic refusal, the helper opt-in, and the truth table for the opt-in
environment variable.

Run with: python3 -m pytest tests/queue-python/test_model_caller_missing.py -q
"""
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import spark_gen  # noqa: E402


class UnwrapTests(unittest.TestCase):
    def test_fence_and_surrounding_prose_are_stripped(self):
        text = 'here is the answer\n```json\n{"a": 1}\n```\ndone'
        self.assertEqual(spark_gen.unwrap_model_text(text), '{"a": 1}')

    def test_text_without_an_object_is_returned_stripped(self):
        self.assertEqual(spark_gen.unwrap_model_text("  no json here \n"),
                         "no json here")

    def test_none_and_empty_become_an_empty_string(self):
        self.assertEqual(spark_gen.unwrap_model_text(None), "")
        self.assertEqual(spark_gen.unwrap_model_text(""), "")


class MessageContentTests(unittest.TestCase):
    def test_missing_or_malformed_shape_is_none(self):
        for data in ({}, {"choices": []}, {"choices": [{}]}, None, "x"):
            self.assertIsNone(spark_gen._message_content(data), data)

    def test_string_content_is_returned(self):
        self.assertEqual(spark_gen._message_content(
            {"choices": [{"message": {"content": "hello"}}]}), "hello")

    def test_only_text_parts_of_a_list_are_joined(self):
        data = {"choices": [{"message": {"content": [
            {"type": "text", "text": "a"},
            {"type": "image_url", "image_url": {"url": "data:"}},
            {"text": "ignored because it has no type"},
            {"type": "text", "text": "b"},
        ]}}]}
        self.assertEqual(spark_gen._message_content(data), "ab")

    def test_non_list_content_is_none(self):
        self.assertIsNone(spark_gen._message_content(
            {"choices": [{"message": {"content": 42}}]}))


class PromptTests(unittest.TestCase):
    def test_prompt_carries_the_product_department_and_shape(self):
        text = spark_gen.build_prompt("ignis", "2026-01-01T00:00:00Z")
        self.assertIn("ignis", text)
        self.assertIn("FDNY-oriented", text)
        self.assertIn("muse-spark-1.3", text)
        self.assertIn("2026-01-01T00:00:00Z", text)

    def test_vigiles_gets_the_crowd_note_and_ignis_does_not(self):
        vigiles = spark_gen.build_prompt("vigiles", "t")
        ignis = spark_gen.build_prompt("ignis", "t")
        self.assertIn("Category note:", vigiles)
        self.assertIn("pedestrian traffic", vigiles)
        self.assertNotIn("Category note:", ignis)

    def test_correction_is_appended_with_the_failed_checks(self):
        text = spark_gen.build_prompt(
            "medicus", "t", ["observations[0].category is invalid"])
        self.assertIn("CORRECTION", text)
        self.assertIn("observations[0].category is invalid", text)

    def test_no_correction_means_no_correction_block(self):
        self.assertNotIn("CORRECTION",
                         spark_gen.build_prompt("medicus", "t"))


class TransportRefusalTests(unittest.TestCase):
    def test_helper_opt_in_is_exactly_one(self):
        for value, expected in (("1", True), ("0", False), ("true", False),
                                ("", False), (" 1 ", False)):
            with unittest.mock.patch.dict(
                    os.environ, {"TRIO_SPARK_VIA_HELPER": value}, clear=False):
                self.assertEqual(spark_gen.via_helper(), expected, value)

    def test_a_non_jpeg_is_refused_before_any_transport(self):
        fd, path = tempfile.mkstemp(suffix=".jpg")
        try:
            os.write(fd, b"not a jpeg")
            os.close(fd)
            with unittest.mock.patch.dict(
                    os.environ, {"TRIO_SPARK_VIA_HELPER": ""}, clear=False):
                with self.assertRaises(RuntimeError) as caught:
                    spark_gen.generate("vigiles", path, "t")
            self.assertIn("not a JPEG", str(caught.exception))
        finally:
            if os.path.exists(path):
                os.remove(path)

    def test_missing_dev_helper_is_a_named_refusal(self):
        with unittest.mock.patch.object(
                spark_gen, "SPARK_CALL", "/nonexistent/spark_call.py"), \
             unittest.mock.patch.dict(
                os.environ, {"TRIO_SPARK_VIA_HELPER": "1"}, clear=False):
            with self.assertRaises(RuntimeError) as caught:
                spark_gen.generate("vigiles", "/tmp/unused.jpg", "t")
        self.assertIn("DEV helper", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
