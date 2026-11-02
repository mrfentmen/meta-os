"""Evidence BOLO tests (CB2-088..089). Pure; no model, no camera."""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import evidence  # noqa: E402

RECORD = {
    "division": "vigiles", "category": "physical contact",
    "camera": {"name": "1 Ave @ 84 St", "area": "Manhattan"},
    "created_at": "2026-11-02T00:00:00Z",
}
FILES = [
    {"ref": "evidence/i/flag.jpg", "kind": "flag-frame"},
    {"ref": "evidence/i/inv.jpg", "kind": "investigation-frame"},
    {"ref": "evidence/i/crop.jpg", "kind": "face-crop"},
]


class BoloTests(unittest.TestCase):
    def test_key_set_is_exact_and_has_no_identity_field(self):
        bolo = evidence.build_bolo(RECORD, ["a person"], FILES)
        self.assertEqual(tuple(bolo), evidence.BOLO_KEYS)
        for forbidden in ("name", "subject_id", "face_template",
                          "identity", "match"):
            self.assertNotIn(forbidden, bolo)

    def test_descriptions_are_deduped_and_frames_are_listed(self):
        bolo = evidence.build_bolo(
            RECORD, ["same", "same", "other"], FILES)
        self.assertEqual(bolo["person_descriptions"], ["same", "other"])
        self.assertEqual(bolo["frame_files"],
                         ["evidence/i/flag.jpg", "evidence/i/inv.jpg"])
        self.assertEqual(bolo["face_crops"], 1)

    def test_direction_is_never_invented(self):
        bolo = evidence.build_bolo(RECORD, [], FILES)
        self.assertIsNone(bolo["direction_of_travel"])
        self.assertIn("Not determined", bolo["direction_note"])


if __name__ == "__main__":
    unittest.main()
