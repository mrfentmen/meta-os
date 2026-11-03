"""Focused tests for code-wave Section 2 (CB-011..CB-020).

One light module, offline: local SQLite store, no Upstash, no model
call, no network. Where the existing suite already covers a task the
test here pins the exact property the task names.
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
import unittest.mock

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(REPO, "server", "queue"))

import crew  # noqa: E402
import crew_records  # noqa: E402
import judge  # noqa: E402
import models  # noqa: E402
import patrol  # noqa: E402
import trio_store  # noqa: E402

_TMP = tempfile.mkdtemp(prefix="code100-section2-")


def store(name):
    return trio_store.LocalSqliteStore(os.path.join(_TMP, name))


class CB011AssessmentRoundTripTests(unittest.TestCase):
    """CB-011: a v2 assessment survives write/read byte for byte."""

    ASSESSMENT = {
        "product": "ignis",
        "timestamp": "2026-11-02T12:00:00.000Z",
        "observations": [{
            "category": "visible smoke",
            "description": "grey smoke from a doorway",
            "evidence": "upper left of frame",
            "confidence": None,
        }],
        "assessment": {
            "category": "visible smoke",
            "summary": "smoke visible",
            "uncertainty": ["source not visible"],
            "requires_human_review": True,
        },
        "processing": {"model": "muse-spark-1.3", "latency_ms": 41},
    }

    def test_exact_bytes_survive_write_and_read(self):
        s = store("cb011.db")
        raw = json.dumps(self.ASSESSMENT, separators=(",", ":")).encode()
        s.set_body("trio:cb011:assessment", raw.decode())
        self.assertEqual(s.get("trio:cb011:assessment").encode(), raw)
        self.assertEqual(json.loads(raw), self.ASSESSMENT)


class CB012DuplicateIncidentTests(unittest.TestCase):
    """CB-012: a duplicate incident id is refused, original untouched."""

    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="cb012-", dir=_TMP)
        self.records = crew_records.CrewRecords(self.dir)
        self.original = {"id": "inc-1", "status": "flagged",
                         "timeline": [{"step": "patrol"}]}
        self.records.create_incident(self.original)

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_duplicate_refused_and_original_untouched(self):
        with self.assertRaises(ValueError) as caught:
            self.records.create_incident(
                {"id": "inc-1", "status": "cleared", "timeline": []})
        self.assertIn("inc-1", str(caught.exception))
        kept = self.records.get_incident("inc-1")
        self.assertEqual(kept["status"], "flagged")
        self.assertEqual(kept["timeline"], [{"step": "patrol"}])


class CB013EmptyJudgePromptTests(unittest.TestCase):
    """CB-013: no observations still yields a valid prompt."""

    def test_empty_readings_do_not_crash_or_invent(self):
        text = judge.build_judge_prompt("vigiles", {}, {})
        self.assertIn("First reading: {}", text)
        self.assertIn("Second reading: {}", text)
        self.assertIn("police", text)
        self.assertNotIn("person down", text)


class CB014VerdictProseTests(unittest.TestCase):
    """CB-014: prose around the JSON is tolerated; garbage is not."""

    def test_markdown_fence_and_prose_are_unwrapped(self):
        reply = (
            "Here is my ruling.\n```json\n"
            '{"verdict": "confirm", "category": "person down",'
            ' "reasons": ["both readings agree"]}\n'
            "```\nThat is all.")
        verdict, category, reasons = judge.parse_verdict(reply)
        self.assertEqual(verdict, "confirmed")
        self.assertEqual(category, "person down")
        self.assertEqual(reasons, ["both readings agree"])

    def test_garbage_raises(self):
        for bad in ("no json here", "```\nnot json\n```", "{broken"):
            with self.assertRaises(ValueError, msg=bad):
                judge.parse_verdict(bad)


class CB015ReserveFloorTests(unittest.TestCase):
    """CB-015: the patrol reserve floor refuses a call at the line."""

    class FakeRecords:
        def __init__(self):
            self.events = []
            self.statuses = []

        def append_event(self, event):
            self.events.append(event)

        def write_status(self, status):
            self.statuses.append(status)

    def patrol_with_remaining(self, remaining):
        p = object.__new__(patrol.Patrol)
        p.reserve_usd = 5.0
        p.guardrail_status = lambda: {
            "calls": 10, "est_cost_usd": 70.0,
            "test_budget_usd": 75.0, "remaining_usd": remaining,
        }
        return p

    def test_floor_is_inclusive(self):
        with unittest.mock.patch.object(patrol.spark_guardrail, "check"):
            for remaining, expected in ((4.99, False), (5.0, False),
                                        (5.01, True)):
                ok, status = self.patrol_with_remaining(remaining)._budget()
                self.assertEqual(ok, expected, remaining)
                self.assertEqual(status["remaining_usd"], remaining)

    def test_paused_cycle_writes_the_receipt_event(self):
        p = self.patrol_with_remaining(4.0)
        p._paused = False
        p.records = self.FakeRecords()
        p.camera_source = "fake"
        p.cameras = []
        p.interval_s = 20.0
        p._counts = {"checks": 0}
        p._last_id = None
        with unittest.mock.patch.object(patrol.spark_guardrail, "check"):
            self.assertEqual(p.run_cycle(), {"outcome": "paused-budget"})
        self.assertEqual(len(p.records.events), 1)
        event = p.records.events[0]
        self.assertEqual(event["state"], "paused-budget")
        self.assertIn("reserve", event["reason"])
        self.assertEqual(p.records.statuses[-1]["state"], "paused-budget")


class CB016DivisionIsolationTests(unittest.TestCase):
    """CB-016: one division's job is invisible under another's key space."""

    def test_namespace_isolates_jobs(self):
        s = store("cb016.db")
        env = {"id": "job-1", "kind": "trio-assessment", "version": 1,
               "product": "vigiles",
               "timestamp": "2026-11-02T00:00:00.000Z"}
        with unittest.mock.patch.object(trio_store, "NS", "trio-vigiles"):
            trio_store.JobStore(s).submit(env)
        with unittest.mock.patch.object(trio_store, "NS", "trio-ignis"):
            self.assertEqual(trio_store.JobStore(s).job_fields("job-1"), {})
        with unittest.mock.patch.object(trio_store, "NS", "trio-vigiles"):
            self.assertEqual(
                trio_store.JobStore(s).job_fields("job-1")["status"], "open")


class CB017SamShapeTests(unittest.TestCase):
    """CB-017: box-only, mask-only, and empty SAM output."""

    def test_box_only_has_no_mask(self):
        rec = models.parse_sam_text(
            "<|box;x1=8;y1=0;x2=599;y2=354;w=600;h=470|>")
        self.assertIsNone(rec["mask"])
        self.assertEqual(rec["region"]["x"], 13)

    def test_mask_only_raises_because_a_region_needs_a_box(self):
        with self.assertRaises(ValueError):
            models.parse_sam_text("<|mask;x=0;y=0;data=abc|>")

    def test_empty_raises(self):
        with self.assertRaises(ValueError):
            models.parse_sam_text("")


class CB018ReceiptValidationTests(unittest.TestCase):
    """CB-018: a receipt with no model id fails validation loudly."""

    def valid(self):
        return {"ts": "2026-11-02T00:00:00Z", "kind": "chat:muse-wonder-1.0",
                "model": "muse-wonder-1.0", "surface": "chat",
                "usage": {"input_tokens": 1, "output_tokens": 1},
                "latency_ms": 12, "est_cost_usd": None}

    def test_valid_receipt_passes(self):
        line = self.valid()
        self.assertIs(models.validate_receipt(line), line)

    def test_missing_model_field_is_named(self):
        line = self.valid()
        del line["model"]
        with self.assertRaises(ValueError) as caught:
            models.validate_receipt(line)
        self.assertIn("model", str(caught.exception))

    def test_blank_model_id_is_refused(self):
        with self.assertRaises(ValueError) as caught:
            models.validate_receipt(self.valid() | {"model": "  "})
        self.assertIn("model id", str(caught.exception))

    def test_file_validator_names_the_bad_line(self):
        path = os.path.join(_TMP, "cb018-receipts.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            f.write(json.dumps(self.valid()) + "\n")
            bad = self.valid()
            del bad["model"]
            f.write(json.dumps(bad) + "\n")
        with self.assertRaises(ValueError) as caught:
            models.validate_receipts(path)
        self.assertIn("line 2", str(caught.exception))
        self.assertIn("model", str(caught.exception))


class CB020DispatchGuardSweepTests(unittest.TestCase):
    """CB-020: every non-loopback dispatch shape is refused."""

    BAD = (
        "http://192.168.1.9:8935/dispatch-simulated",
        "https://api.emergency.example/911",
        "http://127.0.0.1.evil.example/dispatch-simulated",
        "http://127.0.0.1@evil.example/dispatch-simulated",
        "http://evil.example@127.0.0.1@other.example/dispatch-simulated",
        "http://evil.example#@127.0.0.1/dispatch-simulated",
        "http://2130706433/dispatch-simulated",
        "http://[::2]/dispatch-simulated",
    )

    def test_every_non_loopback_shape_is_refused(self):
        for url in self.BAD:
            with self.subTest(url=url):
                with self.assertRaises(crew.DispatchBoundaryError):
                    crew.check_dispatch_url(url)

    def test_loopback_shapes_are_allowed(self):
        for url in ("http://127.0.0.1:8935/dispatch-simulated",
                    "http://localhost:8935/dispatch-simulated",
                    "http://[::1]:8935/dispatch-simulated"):
            with self.subTest(url=url):
                self.assertEqual(crew.check_dispatch_url(url), url)


if __name__ == "__main__":
    unittest.main()
