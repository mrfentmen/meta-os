"""Section 9 (tasks 81-90): OS-showable outputs, generated from records.

stdlib unittest only. Run from repo root:
    python3 -m unittest discover -s tests/science-lab -v
"""
import hashlib
import json
import os
import sys
import tempfile
import unittest
import zipfile

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_LAB = os.path.join(_REPO, "os", "worlds", "science-lab")
if _LAB not in sys.path:
    sys.path.insert(0, _LAB)

import export  # noqa: E402
import ladder  # noqa: E402
import ledger  # noqa: E402


def _read_json(path):
    with open(str(path), "r", encoding="utf-8") as fh:
        return json.load(fh)


class TestSessionExport(unittest.TestCase):
    def test_export_writes_guarded_session_json(self):
        with tempfile.TemporaryDirectory() as td:
            doc = export.export_session("CYCLE-EXAMPLE-001",
                                        exports_dir=td)
            path = os.path.join(td, "CYCLE-EXAMPLE-001.json")
            self.assertTrue(os.path.exists(path))
            back = _read_json(path)
            self.assertEqual(back["cycle_id"], "CYCLE-EXAMPLE-001")
            self.assertTrue(back["claims"], "export must carry claims")
            for claim in back["claims"]:
                self.assertLessEqual(int(claim["level"]),
                                     int(claim["recorded_level"]),
                                     claim.get("claim_id"))
                # The guard itself: display above recorded refuses.
                with self.assertRaises(ValueError):
                    ladder.assert_export_allowed(claim["recorded_level"],
                                                 int(claim["level"]) + 1)

    def test_export_unknown_cycle_refuses(self):
        with self.assertRaises(FileNotFoundError):
            export.export_session("NOPE-NO-CYCLE",
                                  exports_dir=tempfile.gettempdir(),
                                  write=False)


class TestDisplayData(unittest.TestCase):
    def test_colours_from_records(self):
        rows = export.display_data("CYCLE-EXAMPLE-001")
        self.assertTrue(rows)
        for row in rows:
            for key in ("level", "colour", "basis"):
                self.assertIn(key, row)
            self.assertEqual(row["colour"],
                             export.COLOUR_BANDS[row["level"]])
            self.assertTrue(row["basis"].strip())

    def test_band_table(self):
        self.assertEqual(export.colour_for(0), "grey")
        self.assertEqual(export.colour_for(1), "blue")
        self.assertEqual(export.colour_for(2), "green")
        self.assertEqual(export.colour_for(3), "teal")
        for level in (4, 5, 6):
            self.assertIn("human-only", export.colour_for(level))
        with self.assertRaises(ValueError):
            export.colour_for(7)


class TestSpecimens(unittest.TestCase):
    def test_molecules_are_viz_not_sources(self):
        report = export.check_specimens()
        self.assertGreater(report["files_checked"], 0)
        # Honest gap: viz geometry carries no citation/locator/claim.
        self.assertEqual(report["passed"], [])
        self.assertTrue(report["failed"])
        self.assertIn("NOT", report["gap"])
        self.assertIn("viz", report["gap"])


class TestDeptSummaryBoard(unittest.TestCase):
    def test_files_exist_and_counts_agree(self):
        dept = _read_json(os.path.join(_LAB, "records", "exports",
                                       "dept_summary.json"))
        board = _read_json(os.path.join(_LAB, "records", "exports",
                                        "board.json"))
        cycles_on_disk = len([n for n in os.listdir(
            os.path.join(_LAB, "records", "cycles"))
            if n.endswith(".json")])
        self.assertEqual(board["cycles"], cycles_on_disk)
        dept_cycles = sum(d["cycles"]
                          for d in dept["departments"].values())
        self.assertEqual(dept_cycles, board["cycles"])
        self.assertIn("chemistry", dept["departments"])
        self.assertIsInstance(board["claims_by_level"], dict)


class TestExportHonesty(unittest.TestCase):
    def test_audit_clean(self):
        result = export.audit_exports()
        self.assertGreater(result["claims_checked"], 0)
        self.assertEqual(result["violations"], [])

    def test_audit_catches_over_level(self):
        with tempfile.TemporaryDirectory() as td:
            with open(os.path.join(td, "BAD.json"), "w",
                      encoding="utf-8") as fh:
                json.dump({"claims": [{"claim_id": "BAD-1",
                                       "statement": "bad",
                                       "level": 3, "recorded_level": 1,
                                       "basis": "b"}]}, fh)
            result = export.audit_exports(exports_dir=td)
            self.assertEqual(len(result["violations"]), 1)


class TestRegenDrill(unittest.TestCase):
    def test_regen_identical(self):
        result = export.regen_drill()
        self.assertGreater(result["compared"], 0)
        self.assertTrue(result["identical"], result["diffs"])


class TestArchive(unittest.TestCase):
    def test_archive_hashed(self):
        with tempfile.TemporaryDirectory() as td:
            result = export.archive_cycle("CYCLE-EXAMPLE-001",
                                          archive_dir=td)
            self.assertTrue(os.path.exists(result["zip"]))
            with open(result["zip"], "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            self.assertEqual(digest, result["sha256"])
            with open(result["sha_file"], "r",
                      encoding="utf-8") as fh:
                self.assertIn(digest, fh.read())
            with zipfile.ZipFile(result["zip"], "r") as zf:
                names = zf.namelist()
            self.assertIn("cycles/CYCLE-EXAMPLE-001.json", names)
            self.assertIn("manifest.json", names)

    def test_committed_archives_verify(self):
        adir = os.path.join(_LAB, "records", "archive")
        for cid in ("CYCLE-EXAMPLE-001", "DRESS-REHEARSAL-001"):
            zp = os.path.join(adir, "%s.zip" % cid)
            sp = os.path.join(adir, "%s.sha256" % cid)
            self.assertTrue(os.path.exists(zp), zp)
            with open(zp, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            self.assertIn(digest, open(sp, encoding="utf-8").read())


class TestReviewPage(unittest.TestCase):
    def test_review_exists_and_renders_cycle(self):
        page = os.path.join(_REPO, "labs", "science-lab-review",
                            "index.html")
        self.assertTrue(os.path.exists(page))
        text = open(page, encoding="utf-8").read()
        self.assertIn("CYCLE-EXAMPLE-001", text)
        self.assertIn("export.py --review", text)
        self.assertIn('data-level="2"', text)
        self.assertIn("never higher", text)


class TestSignOff(unittest.TestCase):
    def test_outputs_name_sources(self):
        result = export.sign_off()
        self.assertTrue(result["outputs"])
        self.assertTrue(result["sources"])
        self.assertIn("records/exports/board.json", result["outputs"])
        self.assertIn("records/ledger.jsonl", result["sources"])


if __name__ == "__main__":
    unittest.main()
