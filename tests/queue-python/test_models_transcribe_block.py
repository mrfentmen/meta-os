"""Transcribe block tests (CB2-065..066). Offline; no transport."""
import os
import sys
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402


class TranscribeBlockTests(unittest.TestCase):
    def test_transcribe_names_the_unresolved_surface(self):
        with self.assertRaises(models.EndpointUnresolvedError) as raised:
            models.transcribe(b"\xff\xfb fake mp3")
        self.assertIn("no verified call surface", str(raised.exception))

    def test_transcribe_never_calls_transport(self):
        calls = []
        with unittest.mock.patch.object(
                models, "_post",
                side_effect=lambda *a: calls.append(a)):
            with self.assertRaises(models.EndpointUnresolvedError):
                models.transcribe(b"audio", "mp3")
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
