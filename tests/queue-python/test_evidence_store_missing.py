"""Missing-case tests for the Python evidence store (B228).

Cases test_evidence.py does not cover: injected-detector ordering and
cap, crop-box edges, reference-name provenance, BOLO caps and picture
selection.

Offline only: no detector is loaded, no image is fetched; the
injected detector path is the seam the crew uses in tests.
"""
import os
import sys
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")
sys.path.insert(0, QUEUE_DIR)

import evidence  # noqa: E402


class InjectedDetectorTests(unittest.TestCase):
    def test_boxes_are_sorted_by_area_and_capped(self):
        boxes = [
            {"x": 0, "y": 0, "w": 10, "h": 10},
            {"x": 1, "y": 1, "w": 50, "h": 50},
            {"x": 2, "y": 2, "w": 30, "h": 30},
            {"x": 3, "y": 3, "w": 20, "h": 20},
            {"x": 4, "y": 4, "w": 40, "h": 40},
            {"x": 5, "y": 5, "w": 5, "h": 5},
        ]
        found, name = evidence.detect_face_boxes(
            b"frame", detector=lambda _data: list(boxes))
        self.assertEqual(name, "injected")
        self.assertEqual(len(found), evidence.MAX_FACES)
        self.assertEqual([b["w"] for b in found], [50, 40, 30, 20])

    def test_returned_boxes_are_copies(self):
        source = [{"x": 0, "y": 0, "w": 10, "h": 10}]
        found, _ = evidence.detect_face_boxes(
            b"frame", detector=lambda _data: source)
        source[0]["w"] = 999
        self.assertEqual(found[0]["w"], 10)


class CropBoxTests(unittest.TestCase):
    def test_zero_size_box_has_no_crop(self):
        self.assertIsNone(
            evidence.padded_crop_box(
                {"x": 10, "y": 10, "w": 0, "h": 0}, 200, 160))

    def test_zero_pad_is_the_exact_box(self):
        self.assertEqual(
            evidence.padded_crop_box(
                {"x": 10, "y": 20, "w": 30, "h": 40}, 200, 160,
                pad_ratio=0),
            (10, 20, 40, 60))

    def test_negative_origin_is_clamped(self):
        self.assertEqual(
            evidence.padded_crop_box(
                {"x": -10, "y": -10, "w": 40, "h": 40}, 200, 160,
                pad_ratio=0),
            (0, 0, 30, 30))


class RefNameTests(unittest.TestCase):
    def test_name_carries_only_provenance(self):
        name = evidence.frame_ref_name(
            "flag-frame", "cam a/1", b"frame-bytes")
        self.assertTrue(name.startswith("flag-frame-cam-a-1-"))
        self.assertTrue(name.endswith(".jpg"))
        digest = name[len("flag-frame-cam-a-1-"):-len(".jpg")]
        self.assertEqual(len(digest), 6)
        int(digest, 16)  # hex, not words

    def test_same_frame_same_name_and_different_frame_differs(self):
        a = evidence.frame_ref_name("flag-frame", "cam", b"one")
        b = evidence.frame_ref_name("flag-frame", "cam", b"one")
        c = evidence.frame_ref_name("flag-frame", "cam", b"two")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)


class MarksTests(unittest.TestCase):
    def test_bare_prefix_and_non_strings_contribute_nothing(self):
        observations = [
            {"description": "Visible marks:"},
            {"description": "Visible marks:   "},
            {"description": None},
            {"category": "possible altercation"},
            "not a dict",
            {"description": "Visible marks: scar on the chin"},
        ]
        self.assertEqual(
            evidence.extract_visible_marks(observations),
            ["scar on the chin"])

    def test_duplicate_marks_keep_first_order(self):
        observations = [
            {"description": "Visible marks: blood at the hairline"},
            {"description": "Visible marks: tattoo on the left cheek"},
            {"description": "Visible marks: blood at the hairline"},
        ]
        self.assertEqual(
            evidence.extract_visible_marks(observations),
            ["blood at the hairline", "tattoo on the left cheek"])


class BoloTests(unittest.TestCase):
    RECORD = {
        "division": "vigiles",
        "category": "person down",
        "camera": {"name": "Cam A", "area": "Manhattan"},
        "created_at": "2026-11-02T00:00:00.000Z",
    }

    def test_descriptions_are_deduped_and_capped_at_six(self):
        descriptions = ["same", "same"] + [f"d{i}" for i in range(8)]
        bolo = evidence.build_bolo(self.RECORD, descriptions, [])
        self.assertEqual(len(bolo["person_descriptions"]), 6)
        self.assertEqual(bolo["person_descriptions"][0], "same")
        self.assertNotIn("d6", bolo["person_descriptions"])

    def test_non_string_descriptions_are_ignored(self):
        bolo = evidence.build_bolo(
            self.RECORD, ["ok", None, 3, ""], [])
        self.assertEqual(bolo["person_descriptions"], ["ok"])

    def test_frame_files_and_crop_count_follow_kind(self):
        files = [
            {"ref": "a.jpg", "kind": "flag-frame"},
            {"ref": "b.jpg", "kind": "investigation-frame"},
            {"ref": "c.jpg", "kind": "face-crop"},
            {"ref": "d.jpg", "kind": "face-crop"},
            {"ref": "e.jpg", "kind": "something-else"},
        ]
        bolo = evidence.build_bolo(self.RECORD, [], files)
        self.assertEqual(bolo["frame_files"], ["a.jpg", "b.jpg"])
        self.assertEqual(bolo["face_crops"], 2)

    def test_missing_camera_fields_are_none(self):
        bolo = evidence.build_bolo(
            {"division": "vigiles", "category": "person down"},
            [], [])
        self.assertIsNone(bolo["camera_name"])
        self.assertIsNone(bolo["area"])
        self.assertIsNone(bolo["flagged_at"])

    def test_visible_marks_are_deduped_and_capped(self):
        marks = ["m1", "m1"] + [f"m{i}" for i in range(2, 9)]
        bolo = evidence.build_bolo(
            self.RECORD, [], [], visible_marks=marks)
        self.assertEqual(len(bolo["visible_marks"]), evidence.MAX_MARKS)
        self.assertEqual(bolo["visible_marks"][0], "m1")


class PictureRefsTests(unittest.TestCase):
    def test_flag_frame_is_preferred_over_investigation(self):
        refs = evidence.picture_refs([
            {"ref": "inv.jpg", "kind": "investigation-frame"},
            {"ref": "flag.jpg", "kind": "flag-frame"},
            {"ref": "crop.jpg", "kind": "face-crop"},
        ])
        self.assertEqual(refs,
                         {"frame": "flag.jpg",
                          "evidence_crop": "crop.jpg"})

    def test_investigation_frame_stands_in_without_a_flag_frame(self):
        refs = evidence.picture_refs([
            {"ref": "inv.jpg", "kind": "investigation-frame"},
        ])
        self.assertEqual(refs["frame"], "inv.jpg")
        self.assertIsNone(refs["evidence_crop"])

    def test_empty_list_is_none_not_invented(self):
        self.assertEqual(evidence.picture_refs([]),
                         {"frame": None, "evidence_crop": None})


if __name__ == "__main__":
    unittest.main()
