"""Tests for tools/schema_index.py (CB2-375)."""

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("schema_index", ROOT / "tools" / "schema_index.py")
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class SchemaIndex(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "schemas").mkdir()
        (self.root / "schemas" / "thing.schema.json").write_text(
            json.dumps({"$id": "lab/thing.schema.json", "type": "object"}), encoding="utf-8"
        )
        (self.root / "server").mkdir()
        (self.root / "server" / "thing_validate.py").write_text("# validator\n", encoding="utf-8")
        (self.root / "server" / "notes.txt").write_text("ignore me\n", encoding="utf-8")
        (self.root / "node_modules").mkdir()
        (self.root / "node_modules" / "skip.schema.json").write_text("{}", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_scan_finds_schema_and_validator_only(self):
        entries = mod.scan(self.root)
        self.assertEqual(
            [(e["path"], e["kind"]) for e in entries],
            [("schemas/thing.schema.json", "schema"), ("server/thing_validate.py", "validator")],
        )

    def test_schema_record_uses_id_and_validator_uses_stem(self):
        entries = {e["path"]: e["record"] for e in mod.scan(self.root)}
        self.assertEqual(entries["schemas/thing.schema.json"], "lab/thing.schema.json")
        self.assertEqual(entries["server/thing_validate.py"], "thing")

    def test_render_is_a_markdown_table_with_both_rows(self):
        text = mod.render(mod.scan(self.root))
        self.assertIn("| Path | Kind | Record |", text)
        self.assertIn("`schemas/thing.schema.json`", text)
        self.assertIn("`server/thing_validate.py`", text)

    def test_skip_dirs_are_ignored(self):
        paths = [e["path"] for e in mod.scan(self.root)]
        self.assertFalse(any(p.startswith("node_modules/") for p in paths), paths)

    def test_real_repo_scan_finds_the_science_schemas(self):
        entries = mod.scan(ROOT)
        paths = {e["path"] for e in entries}
        self.assertIn("os/worlds/science-lab/schemas/cycle.schema.json", paths)
        self.assertIn("server/queue/receipt_validate.py", paths)


if __name__ == "__main__":
    unittest.main()
