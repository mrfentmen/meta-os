#!/usr/bin/env python3
"""STR-002 screenshot digest in the brief record.

Acceptance: a brief record gains screenshot refs on a fixture
with --img posts. An --img post is a bus message whose text ends
with a BLOB pointer (see send.py): "BLOB:<16 hex hash>:<name>:
<chunk count>", where the name is the image filename. The digest
lists image pointers only, with the sender, file, hash, chunk
count, message time when the message carries one, and the post's
caption (text with pointers removed). It produces no verdict:
whether a screenshot shows a working or broken build is the SAM
pass's call (STR-004/STR-005), not this extractor's.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


IMG_A = "BLOB:0123456789abcdef:dashboard.png:2"
IMG_B = "BLOB:fedcba9876543210:brief-panel.jpg:1"
IMG_UPPER = "BLOB:0011223344556677:crew-board.PNG:1"
NOT_IMG = "BLOB:0123456789abcdef:notes.txt:1"
SHORT_HASH = "BLOB:abc:dashboard.png:1"


class ScreenshotRefsTest(unittest.TestCase):
    def test_img_posts_found_in_order_with_caption_and_time(self):
        snapshot = {"messages": [
            {"nick": "milo", "text": "look at this " + IMG_A,
             "ts": 1793101200},
            {"nick": "rowan", "text": IMG_B},
            {"nick": "pax", "text": "plain message, no image"},
        ]}
        got = brief.extract_screenshot_refs(snapshot)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0]["nick"], "milo")
        self.assertEqual(got[0]["file"], "dashboard.png")
        self.assertEqual(got[0]["hash"], "0123456789abcdef")
        self.assertEqual(got[0]["chunks"], 2)
        self.assertEqual(got[0]["ts"], 1793101200)
        self.assertEqual(got[0]["caption"], "look at this")
        self.assertEqual(got[1]["nick"], "rowan")
        self.assertEqual(got[1]["file"], "brief-panel.jpg")
        self.assertEqual(got[1]["caption"], "")
        self.assertIsNone(got[1]["ts"])

    def test_bus_string_messages_work_and_time_is_not_claimed(self):
        snapshot = {"messages": ["milo: " + IMG_A]}
        got = brief.extract_screenshot_refs(snapshot)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["nick"], "milo")
        self.assertIsNone(got[0]["ts"])

    def test_non_image_pointers_and_bad_pointers_skipped(self):
        snapshot = {"messages": [
            {"nick": "milo", "text": "file " + NOT_IMG},
            {"nick": "milo", "text": "bad " + SHORT_HASH},
            {"nick": "milo", "text": "upper " + IMG_UPPER},
            {"nick": "milo", "text": "fake.png.txt " +
             "BLOB:0123456789abcdef:fake.png.txt:1"},
        ]}
        got = brief.extract_screenshot_refs(snapshot)
        self.assertEqual([ref["file"] for ref in got],
                         ["crew-board.PNG"])

    def test_same_image_twice_yields_one_ref_at_latest_post(self):
        snapshot = {"messages": [
            {"nick": "milo", "text": "old caption " + IMG_A,
             "ts": 1793101000},
            {"nick": "rowan", "text": IMG_B, "ts": 1793101100},
            {"nick": "milo", "text": "new caption " + IMG_A,
             "ts": 1793101200},
        ]}
        got = brief.extract_screenshot_refs(snapshot)
        self.assertEqual([ref["file"] for ref in got],
                         ["brief-panel.jpg", "dashboard.png"])
        self.assertEqual(got[1]["caption"], "new caption")
        self.assertEqual(got[1]["ts"], 1793101200)

    def test_empty_snapshot_is_empty_not_an_error(self):
        self.assertEqual(brief.extract_screenshot_refs({}), [])
        self.assertEqual(brief.extract_screenshot_refs(None), [])
        self.assertEqual(brief.extract_screenshot_refs(
            {"messages": []}), [])


class ScreenshotDigestLinesTest(unittest.TestCase):
    def test_line_names_sender_file_and_time_or_not_reported(self):
        refs = [
            {"nick": "milo", "file": "dashboard.png",
             "hash": "0123456789abcdef", "chunks": 2,
             "ts": 1793101200, "caption": "look at this"},
            {"nick": "rowan", "file": "brief-panel.jpg",
             "hash": "fedcba9876543210", "chunks": 1,
             "ts": None, "caption": ""},
        ]
        lines = brief.screenshot_digest_lines(refs)
        self.assertEqual(lines[0],
                         "milo shared dashboard.png at "
                         "2026-10-27 07:40 ET: look at this")
        self.assertEqual(lines[1],
                         "rowan shared brief-panel.jpg at "
                         "time not reported")
        self.assertEqual(brief.screenshot_digest_lines([]), [])
        self.assertEqual(brief.screenshot_digest_lines(None), [])


class ScreenshotBriefRecordTest(unittest.TestCase):
    def test_template_brief_carries_screenshots_section(self):
        snapshot = {"messages": [
            {"nick": "milo", "text": "look at this " + IMG_A,
             "ts": 1793101200},
        ]}
        text = brief.compose_template_brief(snapshot)
        self.assertIn("Screenshots", text)
        self.assertIn("milo shared dashboard.png at "
                      "2026-10-27 07:40 ET: look at this", text)

    def test_template_brief_without_screenshots_keeps_old_shape(self):
        snapshot = {"messages": [
            {"nick": "pax", "text": "DECISION: ship the panel"},
        ]}
        text = brief.compose_template_brief(snapshot)
        self.assertNotIn("Screenshots", text)

    def test_generate_brief_record_gains_refs_inside_window(self):
        snapshot = {"messages": [
            {"nick": "milo", "text": "old shot " + IMG_A,
             "ts": 1793101200 - 90000},
            {"nick": "rowan", "text": IMG_B, "ts": 1793101200},
        ]}
        _text, record = brief.generate_brief(
            snapshot, "build", kind="morning", now=1793101200,
            dry_run=True)
        self.assertEqual(brief.validate_brief_record(record), [])
        self.assertEqual([ref["file"] for ref in
                          record["screenshot_refs"]],
                         ["brief-panel.jpg"])
        self.assertNotIn("verdict", str(record["screenshot_refs"]))


if __name__ == "__main__":
    unittest.main()
