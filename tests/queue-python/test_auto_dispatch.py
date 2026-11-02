"""Tests for Imperium direct dispatch (docs/IMPERIUM_AUTO_DISPATCH.md,
boss directive 2026-11-01): on a confirmed RED incident the agent
itself sends the dispatch package — picture included — with NO
human verify step; human review is the post-hoc audit flag
(assessment.requires_human_review, kept true). The agency policy
setting TRIO_CREW_HUMAN_VERIFY (default off) holds the package
for verify instead of sending it.

Run with the queue suite, from the repo root:

    python3 -m unittest discover -s tests/queue-python -v

Offline throughout: assess/fetch/dispatch seams are stubbed, the
dispatch target is never contacted.
"""
import io
import os
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
QUEUE_DIR = os.path.join(REPO, "server", "queue")

_TMP = tempfile.mkdtemp(prefix="trio-auto-dispatch-tests-")
os.environ["TRIO_STORE"] = "local"
os.environ["TRIO_LOCAL_DB"] = os.path.join(_TMP, "auto-dispatch-local.db")
os.environ["TRIO_JOB_NS"] = "trio-test"
os.environ.pop("SPARK_API_KEY", None)
os.environ.pop("TRIO_SPARK_VIA_HELPER", None)

sys.path.insert(0, QUEUE_DIR)

import crew  # noqa: E402
import crew_records  # noqa: E402
import evidence  # noqa: E402
from test_crew import ALL_CAMS, CAM_A, FRAME, ScriptedAssessor  # noqa: E402

# The confirmed-RED script: patrol flags, review confirms, the
# investigation lenses and neighbours come back baseline.
RED_SCRIPT = {
    "vigiles": ["person down", "person down", "normal activity"],
    "ignis": ["no hazard visible"],
    "medicus": ["normal activity"],
}


def _jpeg_bytes():
    """A real decodable JPEG (the evidence crop path needs one)."""
    from PIL import Image
    buf = io.BytesIO()
    Image.new("RGB", (200, 200), (170, 170, 170)).save(buf, "JPEG")
    return buf.getvalue()


def _make_crew(tmp, assessor, frame=FRAME, detector=None,
               human_verify=None):
    records = crew_records.CrewRecords(
        directory=os.path.join(tmp, "crew-data"))
    dispatched = []

    def dispatch(package):
        dispatched.append(package)
        return {"receipt_id": "sim-test123", "simulated": True}

    crew_obj = crew.Crew(records, assessor, lambda camera: frame,
                         dispatch, cameras=ALL_CAMS,
                         detector=detector, human_verify=human_verify)
    return crew_obj, records, dispatched


class AutoDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=_TMP)
        # The policy env vars belong to these tests only: start
        # every test with both unset, whatever the shell carried.
        self._saved_env = {k: os.environ.get(k)
                           for k in (crew.HUMAN_VERIFY_ENV,
                                     crew.DISPATCH_URL_ENV)}
        for key in self._saved_env:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_red_auto_dispatches_with_picture_and_crop(self):
        # A real JPEG + an injected detector, so the flagged path
        # captures a face crop alongside the flagged frame.
        frame = _jpeg_bytes()
        detector = lambda data: [{"x": 60, "y": 60, "w": 64, "h": 64}]
        crew_obj, records, dispatched = _make_crew(
            self.tmp, ScriptedAssessor(RED_SCRIPT), frame=frame,
            detector=detector)
        out = crew_obj.check_camera(CAM_A, "vigiles")
        # Sent by the agent, no human action anywhere in the flow.
        self.assertEqual(out["outcome"], "dispatched-simulated")
        self.assertEqual(len(dispatched), 1)
        package = dispatched[0]
        self.assertIs(package["simulated"], True)
        self.assertEqual(package["dispatch_mode"], "auto")
        self.assertIs(package["human_verify"], False)
        # The picture: the flagged frame reference plus the
        # evidence crop reference the flagged path captured.
        picture = package["picture"]
        self.assertIn("flag-frame", picture["frame"])
        self.assertIsNotNone(picture["evidence_crop"])
        self.assertIn("face-crop", picture["evidence_crop"])
        files = {f["ref"] for f in
                 records.list_incidents()[0]["evidence"]["files"]}
        self.assertIn(picture["frame"], files)
        self.assertIn(picture["evidence_crop"], files)
        # The audit flag survives the change: the brief's contract
        # field and the package flag both stay true — as the
        # post-hoc audit marker, not a gate on the send above.
        self.assertIs(
            package["brief"]["assessment"]["requires_human_review"],
            True)
        self.assertIs(package["requires_human_review"], True)

    def test_red_auto_dispatch_picture_without_crop(self):
        # No detector finds a face (the fake frame never decodes
        # for the production path): the picture still carries the
        # flagged frame, and the crop is honestly None.
        crew_obj, records, dispatched = _make_crew(
            self.tmp, ScriptedAssessor(RED_SCRIPT))
        out = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(out["outcome"], "dispatched-simulated")
        self.assertEqual(len(dispatched), 1)
        picture = dispatched[0]["picture"]
        self.assertIn("flag-frame", picture["frame"])
        self.assertIsNone(picture["evidence_crop"])

    def test_yellow_never_dispatches(self):
        assessor = ScriptedAssessor({"vigiles": ["energetic movement"]})
        crew_obj, records, dispatched = _make_crew(self.tmp, assessor)
        out = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(out["outcome"], "flagged-yellow-review")
        self.assertEqual(dispatched, [])
        incident = records.list_incidents()[0]
        self.assertEqual(incident["status"], "yellow-review")
        self.assertNotIn("dispatch",
                         [s["step"] for s in incident["timeline"]])


class HumanVerifyPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(dir=_TMP)
        self._saved_env = {k: os.environ.get(k)
                           for k in (crew.HUMAN_VERIFY_ENV,
                                     crew.DISPATCH_URL_ENV)}
        for key in self._saved_env:
            os.environ.pop(key, None)

    def tearDown(self):
        for key, value in self._saved_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_policy_on_holds_package_instead_of_sending(self):
        crew_obj, records, dispatched = _make_crew(
            self.tmp, ScriptedAssessor(RED_SCRIPT), human_verify=True)
        out = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(out["outcome"], "held-for-verify")
        # The dispatcher was never called.
        self.assertEqual(dispatched, [])
        incident = records.list_incidents()[0]
        self.assertEqual(incident["status"], "held-for-verify")
        # The package was still built (brief + bolo on record) and
        # the held dispatch step carries it for the verify.
        steps = [s["step"] for s in incident["timeline"]]
        self.assertIn("brief", steps)
        held = [s for s in incident["timeline"]
                if s["step"] == "dispatch"][0]
        self.assertIs(held["held"], True)
        self.assertEqual(held["package"]["incident_id"],
                         out["incident_id"])
        self.assertEqual(held["package"]["dispatch_mode"],
                         "held-for-verify")
        self.assertIn("flag-frame", held["package"]["picture"]["frame"])

    def test_policy_env_flag_parsing_and_env_hold(self):
        self.assertFalse(crew.human_verify_required())
        for value in ("1", "true", "yes", "on", "ON"):
            with unittest.mock.patch.dict(
                    os.environ, {crew.HUMAN_VERIFY_ENV: value}):
                self.assertTrue(crew.human_verify_required(), value)
        with unittest.mock.patch.dict(
                os.environ, {crew.HUMAN_VERIFY_ENV: "off"}):
            self.assertFalse(crew.human_verify_required())
        # A crew that reads the setting from the env holds too.
        with unittest.mock.patch.dict(
                os.environ, {crew.HUMAN_VERIFY_ENV: "on"}):
            crew_obj, records, dispatched = _make_crew(
                self.tmp, ScriptedAssessor(RED_SCRIPT))
            out = crew_obj.check_camera(CAM_A, "vigiles")
        self.assertEqual(out["outcome"], "held-for-verify")
        self.assertEqual(dispatched, [])


class DispatchUrlPolicyTests(unittest.TestCase):
    def test_env_dispatch_url_non_loopback_refused(self):
        # The verify policy never widens the target: a non-loopback
        # URL from the env is refused exactly like a literal one.
        with unittest.mock.patch.dict(
                os.environ,
                {crew.DISPATCH_URL_ENV:
                 "https://api.emergency.example/911"}):
            with self.assertRaises(crew.DispatchBoundaryError):
                crew.dispatch_url()
        with unittest.mock.patch.dict(
                os.environ,
                {crew.DISPATCH_URL_ENV:
                 "http://127.0.0.1:8935/dispatch-simulated"}):
            self.assertEqual(crew.dispatch_url(),
                             "http://127.0.0.1:8935/dispatch-simulated")
        with unittest.mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(crew.DISPATCH_URL_ENV, None)
            self.assertEqual(crew.dispatch_url(),
                             crew.DEFAULT_DISPATCH_URL)


class PictureRefsTests(unittest.TestCase):
    def test_picture_refs_selection(self):
        self.assertEqual(evidence.picture_refs(None),
                         {"frame": None, "evidence_crop": None})
        self.assertEqual(evidence.picture_refs([]),
                         {"frame": None, "evidence_crop": None})
        files = [
            {"ref": "evidence/i/investigation-frame-c-aa.jpg",
             "kind": "investigation-frame"},
            {"ref": "evidence/i/flag-frame-c-bb.jpg",
             "kind": "flag-frame"},
            {"ref": "evidence/i/face-crop-c-cc.jpg",
             "kind": "face-crop"},
            {"ref": "evidence/i/face-crop-c-dd.jpg",
             "kind": "face-crop"},
        ]
        picture = evidence.picture_refs(files)
        # The flag frame wins over investigation frames; the
        # first captured crop is the package's evidence crop.
        self.assertEqual(picture["frame"],
                         "evidence/i/flag-frame-c-bb.jpg")
        self.assertEqual(picture["evidence_crop"],
                         "evidence/i/face-crop-c-cc.jpg")


if __name__ == "__main__":
    unittest.main()
