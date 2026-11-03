"""Tests for tools/readme_data_index.py (CB2-493)."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "readme_data_index", ROOT / "tools" / "readme_data_index.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class ReadmeDataIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "a.json").write_text(
            json.dumps({"name": "Alpha", "status": "VERIFIED", "proof": "docs/a.md"}),
            encoding="utf-8",
        )
        (self.dir / "b.json").write_text(
            json.dumps({"name": "Beta", "status": "UNIMPLEMENTED", "proof": "docs/b.md"}),
            encoding="utf-8",
        )
        (self.dir / "broken.json").write_text("{nope", encoding="utf-8")
        (self.dir / "notes.txt").write_text("skip", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_rows_are_sorted_and_txt_skipped(self):
        result = mod.scan(self.dir)
        self.assertEqual([r["file"] for r in result["rows"]], ["a.json", "b.json"])
        self.assertEqual(len(result["errors"]), 1)
        self.assertTrue(result["errors"][0].startswith("broken.json:"), result["errors"])

    def test_render_has_name_status_and_proof_columns(self):
        text = mod.render(mod.scan(self.dir))
        self.assertIn("| Program | Status | Proof |", text)
        self.assertIn("| Alpha | VERIFIED | docs/a.md |", text)
        self.assertIn("| Beta | UNIMPLEMENTED | docs/b.md |", text)

    def test_real_directory_renders_every_program(self):
        result = mod.scan(ROOT / "docs" / "readme-data")
        self.assertEqual(result["errors"], [])
        names = [r["name"] for r in result["rows"]]
        self.assertIn("Meta Imperium", names)
        self.assertIn("Meta OS kernel", names)
        self.assertGreaterEqual(len(names), 16)


if __name__ == "__main__":
    unittest.main()
