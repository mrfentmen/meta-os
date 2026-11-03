"""Model id constants tests (CB2-074). Offline; pure data."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import models  # noqa: E402


class ModelIdConstantTests(unittest.TestCase):
    def test_verified_ids_are_exact(self):
        self.assertEqual(models.SPARK, "muse-spark-1.3")
        self.assertEqual(models.WONDER, "muse-wonder-1.0")
        self.assertEqual(models.SAM, "sam-3.1")
        self.assertEqual(models.IMAGE, "muse-image-1.0")
        self.assertEqual(models.VOICE, "muse-voice-transcribe-1.0")

    def test_registry_surfaces_match_the_verified_list(self):
        self.assertEqual(models.MODELS[models.SPARK]["surface"], "chat")
        self.assertEqual(models.MODELS[models.WONDER]["surface"], "chat")
        self.assertEqual(models.MODELS[models.SAM]["surface"], "responses")
        self.assertEqual(models.MODELS[models.IMAGE]["surface"], "responses")
        self.assertIsNone(models.MODELS[models.VOICE]["surface"])


if __name__ == "__main__":
    unittest.main()
