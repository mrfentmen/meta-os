"""Model error mapping tests (CB2-067..069). Offline; fake opener."""
import os
import sys
import unittest
import unittest.mock
import urllib.error

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402


class BadOpener:
    def __init__(self, code):
        self.code = code

    def open(self, *args, **kwargs):
        raise urllib.error.HTTPError(
            "https://api.meta.ai", self.code, "bad", {}, None)


class EmptyResponse:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return b""


class EmptyOpener:
    def open(self, *args, **kwargs):
        return EmptyResponse()


class ErrorMapTests(unittest.TestCase):
    def _post_code(self, code):
        with unittest.mock.patch.dict(
                os.environ, {"SPARK_API_KEY": "test"}), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "check"), \
                unittest.mock.patch.object(
                    models.urllib.request, "build_opener",
                    lambda handler: BadOpener(code)):
            return models._post("https://api.meta.ai", {}, "test")

    def test_429_is_rate_limit(self):
        with self.assertRaises(models.RateLimitError):
            self._post_code(429)

    def test_401_and_403_are_auth_errors(self):
        for code in (401, 403):
            with self.assertRaises(models.AuthError):
                self._post_code(code)

    def test_500_is_server_error(self):
        with self.assertRaises(models.ServerError):
            self._post_code(500)

    def test_empty_200_body_is_named(self):
        with unittest.mock.patch.dict(
                os.environ, {"SPARK_API_KEY": "test"}), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "check"), \
                unittest.mock.patch.object(
                    models.urllib.request, "build_opener",
                    lambda handler: EmptyOpener()):
            with self.assertRaises(models.EmptyResponseError):
                models._post("https://api.meta.ai", {}, "test")

    def test_chat_segment_image_empty_payloads_are_named(self):
        with unittest.mock.patch.object(
                models, "_post", return_value=({}, 1)), \
                unittest.mock.patch.object(
                    models.spark_guardrail, "record"):
            with self.assertRaises(models.EmptyResponseError):
                models.chat_text(models.SPARK, "hello")
            with self.assertRaises(models.EmptyResponseError):
                models.segment(b"\x89PNG\r\n\x1a\nrest", "person")
            with self.assertRaises(models.EmptyResponseError):
                models.generate_image("draw")


if __name__ == "__main__":
    unittest.main()
