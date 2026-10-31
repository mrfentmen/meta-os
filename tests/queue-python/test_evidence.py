"""Tests for event-gated person evidence (server/queue/evidence.py
+ the crew's evidence capture / purge / BOLO wiring). Del's design
(2026-10-31): passive — evidence exists only for flagged
incidents; false positives have it deleted, on the record.

Run from the repo root (same command as the queue suite):

    python3 -m unittest discover -s tests/queue-python -v

Everything here is offline: the assess/fetch/dispatch seams are
stubbed, exactly as in test_crew.py. The face detector is stubbed
by injection where a crop must be produced; the real detector's
honest states (opencv-haar when cv2 exists, "unavailable" when it
does not) are asserted without assuming which runtime this is.
"""
import io
import json
import os
import sys
import tempfile
import unittest

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")

_TMP = tempfile.mkdtemp(prefix="trio-evidence-tests-")
os.environ["TRIO_STORE"] = "local"
os.environ["TRIO_LOCAL_DB"] = os.path.join(_TMP, "evidence-local.db")
os.environ["TRIO_JOB_NS"] = "trio-test"
os.environ.pop("SPARK_API_KEY", None)
os.environ.pop("TRIO_SPARK_VIA_HELPER", None)

sys.path.insert(0, QUEUE_DIR)

import crew  # noqa: E402
import crew_common  # noqa: E402
import crew_records  # noqa: E402
import evidence  # noqa: E402

FRAME = b"\xff\xd8" + bytes(range(256)) * 4  # JPEG magic + payload

CAM_A = {"id": "cam-a", "name": "1 Ave @ 84 St", "latitude": 40.7755,
         "longitude": -73.9502, "area": "Manhattan", "isOnline": "true",
         "imageUrl": "https://example.invalid/cam-a/image"}
CAM_B = {"id": "cam-b", "name": "Central Park West @ 65 St",
         "latitude": 40.771797, "longitude": -73.979217,
         "area": "Manhattan", "isOnline": "true",
         "imageUrl": "https://example.invalid/cam-b/image"}
CAM_C = {"id": "cam-c", "name": "Broadway @ 45 St",
         "latitude": 40.757953, "longitude": -73.98549,
         "area": "Manhattan", "isOnline": "true",
         "imageUrl": "https://example.invalid/cam-c/image"}
ALL_CAMS = [CAM_A, CAM_B, CAM_C]


def canned_result(product, timestamp, frame, category, status="ok"):
    assessment = None
    if status == "ok":
        assessment = {
            "product": product,
            "timestamp": timestamp,
            "observations": [{
                "category": category,
                "description": f"stubbed reading: {category}",
                "evidence": "center of frame",
                "confidence": None,
            }],
            "assessment": {
                "category": category,
                "summary": f"stubbed summary: {category}",
                "uncertainty": ["stubbed uncertainty"],
                "requires_human_review": True,
            },
            "processing": {"model": "muse-spark-1.3", "latency_ms": None},
        }
    return {
        "job_id": crew_common.job_id_for(product, timestamp, frame),
        "status": status, "assessment": assessment,
        "error": None if status == "ok" else "stubbed failure",
        "model": "muse-spark-1.3", "latency_ms": 7,
        "completed_at": timestamp,
    }


class ScriptedAssessor:
    def __init__(self, script):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls = []

    def __call__(self, product, frame, timestamp):
        self.calls.append({"product": product, "timestamp": timestamp})
        entries = self.script[product]
        entry = entries.pop(0) if len(entries) > 1 else entries[0]
        return canned_result(product, timestamp, frame, entry)


def real_jpeg():
    """A real decodable JPEG (200x160), with a bright block where
    the injected detector will 'find' the face."""
    from PIL import Image, ImageDraw
    img = Image.new("RGB", (200, 160), (20, 20, 24))
    draw = ImageDraw.Draw(img)
    draw.rectangle([80, 40, 119, 79], fill=(210, 180, 160))
    out = io.BytesIO()
    img.save(out, "JPEG", quality=90)
    return out.getvalue()


def make_crew(tmp, assessor, frame=FRAME, detector=None):
    records = crew_records.CrewRecords(
        directory=os.path.join(tmp, "crew-data"))
    dispatched = []

    def dispatch(package):
        dispatched.append(package)
        return {"receipt_id": "sim-test123", "simulated": True}

    crew_obj = crew.Crew(records, assessor, lambda camera: frame,
                         dispatch, cameras=ALL_CAMS, detector=detector)
    return crew_obj, records, dispatched


def evidence_files_on_disk(tmp):
    root = os.path.join(tmp, "crew-data", "evidence")
    found = []
    for base, _dirs, names in os.walk(root):
        for name in names:
            found.append(os.path.join(base, name))
    return found


class EventGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="trio-evidence-")

    def test_baseline_check_captures_no_evidence(self):
        assessor = ScriptedAssessor({"vigiles": ["normal activity"]})
        crew_obj, records, _ = make_crew(self.tmp, assessor)
        outcome = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(outcome["outcome"], "baseline")
        self.assertEqual(records.list_incidents(), [])
        self.assertEqual(evidence_files_on_disk(self.tmp), [])

    def test_cleared_flag_purges_evidence_on_the_record(self):
        assessor = ScriptedAssessor(
            {"vigiles": ["possible altercation", "normal activity"]})
        crew_obj, records, _ = make_crew(self.tmp, assessor)
        outcome = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(outcome["outcome"], "cleared-by-review")
        self.assertEqual(evidence_files_on_disk(self.tmp), [])
        record = records.get_incident(outcome["incident_id"])
        self.assertIsNotNone(record)
        self.assertEqual(record["evidence"]["files"], [])
        purged = record["evidence"]["purged"]
        self.assertEqual(purged["reason"], "closed-false-positive")
        self.assertGreaterEqual(purged["files_removed"], 1)
        steps = [s["step"] for s in record["timeline"]]
        self.assertIn("evidence-purged", steps)
        # The flag frame's hash is retained: what was captured and
        # that it was deleted are both provable afterwards.
        self.assertTrue(record["evidence"]["frame_sha256"])

    def test_confirmed_flag_dispatches_bolo_with_the_package(self):
        assessor = ScriptedAssessor({
            "vigiles": ["possible altercation"],
            "ignis": ["no hazard visible"],
            "medicus": ["normal activity"],
        })
        crew_obj, records, dispatched = make_crew(self.tmp, assessor)
        outcome = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(outcome["outcome"], "dispatched-simulated")
        self.assertEqual(len(dispatched), 1)
        package = dispatched[0]
        self.assertTrue(package["simulated"])
        bolo = package["person_evidence"]
        self.assertEqual(set(bolo.keys()), set(evidence.BOLO_KEYS))
        self.assertEqual(bolo["category"], "possible altercation")
        self.assertEqual(bolo["camera_name"], CAM_A["name"])
        self.assertIn("stubbed reading: possible altercation",
                      bolo["person_descriptions"])
        self.assertIsNone(bolo["direction_of_travel"])
        self.assertGreaterEqual(len(bolo["frame_files"]), 1)
        record = records.get_incident(outcome["incident_id"])
        kinds = [f["kind"] for f in record["evidence"]["files"]]
        self.assertIn("flag-frame", kinds)
        self.assertIn("investigation-frame", kinds)
        self.assertNotIn("purged", record["evidence"])
        steps = [s["step"] for s in record["timeline"]]
        self.assertIn("bolo", steps)
        self.assertGreaterEqual(
            len(evidence_files_on_disk(self.tmp)), 1)

    def test_no_identity_shaped_key_anywhere_in_bolo(self):
        bolo = evidence.build_bolo(
            {"division": "vigiles", "category": "possible altercation",
             "camera": {"name": "Cam", "area": "Manhattan"},
             "created_at": "2026-10-31T00:00:00.000Z"},
            ["a person in a red jacket", "a person in a red jacket",
             "second description"],
            [{"ref": "evidence/i/flag.jpg", "kind": "flag-frame"},
             {"ref": "evidence/i/crop.jpg", "kind": "face-crop"}],
            visible_marks=["tattoo on the left cheek"])
        self.assertEqual(set(bolo.keys()), set(evidence.BOLO_KEYS))
        for key in bolo.keys():
            for banned in ("name", "identity", "match", "template",
                           "person_id"):
                if key == "camera_name":
                    continue  # the camera's name, not a person's
                self.assertNotIn(banned, key)
        self.assertEqual(
            bolo["person_descriptions"],
            ["a person in a red jacket", "second description"])
        self.assertEqual(bolo["visible_marks"],
                         ["tattoo on the left cheek"])
        self.assertEqual(bolo["face_crops"], 1)
        self.assertEqual(bolo["frame_files"], ["evidence/i/flag.jpg"])


class MarksAssessor:
    """A scripted assessor whose vigiles readings also carry a
    "Visible marks:" observation — the shape the real assessment
    prompt now instructs Spark to return when a person has visible
    tattoos, scars, or blood."""

    def __init__(self, script, marks):
        self.inner = ScriptedAssessor(script)
        self.marks = marks

    def __call__(self, product, frame, timestamp):
        result = self.inner(product, frame, timestamp)
        if product == "vigiles" and result.get("status") == "ok":
            result["assessment"]["observations"].append({
                "category": "possible altercation",
                "description": f"Visible marks: {self.marks}",
                "evidence": "face and upper body, center of frame",
                "confidence": None,
            })
        return result


class VisibleMarksTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="trio-evidence-")

    def test_extract_pulls_only_prefixed_descriptions(self):
        observations = [
            {"description": "a person in a red jacket"},
            {"description": "Visible marks: tattoo on the left "
                            "cheek; blood at the hairline"},
            {"description": "visible marks: scar on the chin"},
            {"description": "Visible marks:"},
            {"description": "Visible marks: tattoo on the left "
                            "cheek; blood at the hairline"},
            {"description": None},
            {"category": "possible altercation"},
            "not a dict",
        ]
        self.assertEqual(
            evidence.extract_visible_marks(observations),
            ["tattoo on the left cheek; blood at the hairline",
             "scar on the chin"])

    def test_extract_skips_absence_reports(self):
        # The 2026-10-31 eval batch: on low-resolution frames the
        # model files "no mark could be seen" lines under the same
        # prefix. Absences are not marks and must not reach a BOLO.
        observations = [
            {"description": "Visible marks: no tattoos, scars, "
                            "birthmarks, or blood clearly visible "
                            "on any person in this low-resolution "
                            "frame"},
            {"description": "Visible marks: none discernible on "
                            "any person; tattoos, scars, birthmarks, "
                            "or blood not visible due to low "
                            "resolution and distance"},
            {"description": "Visible marks: no distinct tattoos, "
                            "scars, birthmarks, or blood discernible "
                            "on any visible person"},
            {"description": "Visible marks: blood visible on the "
                            "forehead"},
            {"description": "Visible marks: tattoo on the left "
                            "cheek; blood at the hairline"},
        ]
        self.assertEqual(
            evidence.extract_visible_marks(observations),
            ["blood visible on the forehead",
             "tattoo on the left cheek; blood at the hairline"])

    def test_extract_caps_at_max_marks(self):
        observations = [
            {"description": f"Visible marks: mark {i}"}
            for i in range(evidence.MAX_MARKS + 3)]
        self.assertEqual(
            len(evidence.extract_visible_marks(observations)),
            evidence.MAX_MARKS)

    def test_confirmed_flag_bolo_carries_the_recorded_marks(self):
        assessor = MarksAssessor(
            {"vigiles": ["possible altercation"],
             "ignis": ["no hazard visible"],
             "medicus": ["normal activity"]},
            "tattoo on the left cheek; blood at the hairline")
        crew_obj, records, dispatched = make_crew(self.tmp, assessor)
        outcome = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(outcome["outcome"], "dispatched-simulated")
        bolo = dispatched[0]["person_evidence"]
        # Patrol, review, and the vigiles neighbour readings all
        # recorded the same marks; the BOLO lists them once.
        self.assertEqual(
            bolo["visible_marks"],
            ["tattoo on the left cheek; blood at the hairline"])
        record = records.get_incident(outcome["incident_id"])
        bolo_steps = [s for s in record["timeline"]
                      if s["step"] == "bolo"]
        self.assertEqual(
            bolo_steps[0]["bolo"]["visible_marks"],
            ["tattoo on the left cheek; blood at the hairline"])


class FaceCropTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="trio-evidence-")

    def test_padded_crop_box_math(self):
        self.assertEqual(
            evidence.padded_crop_box(
                {"x": 80, "y": 40, "w": 40, "h": 40}, 200, 160),
            (66, 26, 134, 94))
        self.assertEqual(
            evidence.padded_crop_box(
                {"x": 0, "y": 0, "w": 40, "h": 40}, 200, 160),
            (0, 0, 54, 54))
        self.assertIsNone(
            evidence.padded_crop_box(
                {"x": 500, "y": 500, "w": 40, "h": 40}, 200, 160))

    def test_default_detector_is_honest_about_its_state(self):
        try:
            boxes, name = evidence.detect_face_boxes(b"not an image")
            self.assertEqual(boxes, [])
            self.assertEqual(name, "unavailable")
        except ValueError:
            pass  # cv2 present: an undecodable frame is an error

    def test_injected_detector_produces_a_real_crop(self):
        jpeg = real_jpeg()
        assessor = ScriptedAssessor({
            "vigiles": ["possible altercation"],
            "ignis": ["no hazard visible"],
            "medicus": ["normal activity"],
        })
        crew_obj, records, dispatched = make_crew(
            self.tmp, assessor, frame=jpeg,
            detector=lambda data: [{"x": 80, "y": 40, "w": 40, "h": 40}])
        outcome = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(outcome["outcome"], "dispatched-simulated")
        record = records.get_incident(outcome["incident_id"])
        crops = [f for f in record["evidence"]["files"]
                 if f["kind"] == "face-crop"]
        self.assertGreaterEqual(len(crops), 1)
        bolo = dispatched[0]["person_evidence"]
        self.assertGreaterEqual(bolo["face_crops"], 1)
        from PIL import Image
        crop_path = os.path.join(self.tmp, "crew-data", crops[0]["ref"])
        with Image.open(crop_path) as img:
            self.assertEqual(img.size, (68, 68))


if __name__ == "__main__":
    unittest.main()
