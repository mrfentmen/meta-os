"""Tests for tools/validate_science_schemas.py (CB2-362..364)."""

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "validate_science_schemas", ROOT / "tools" / "validate_science_schemas.py"
)
mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mod)


class SchemasWellFormed(unittest.TestCase):
    def test_all_five_load_with_top_level_keys(self):
        schemas = mod.load_schemas()
        self.assertEqual(len(schemas), 5)
        for name, doc in schemas.items():
            self.assertEqual(mod.check_schema(name, doc), [], name)

    def test_missing_top_level_key_is_reported(self):
        findings = mod.check_schema("fixture.schema.json", {"type": "object", "properties": {}})
        self.assertTrue(any("$schema" in f for f in findings), findings)
        self.assertTrue(any("$id" in f for f in findings), findings)

    def test_cycle_phase_enum_matches_cycle_py(self):
        self.assertEqual(mod.check_cycle_enum(mod.load_schemas()), [])

    def test_hypothesis_required_fields_are_parser_fields(self):
        self.assertEqual(mod.check_hypothesis_required(mod.load_schemas()), [])

    def test_real_tree_has_no_findings(self):
        self.assertEqual(mod.check_all(), [])

    def test_main_exits_zero_on_real_tree(self):
        self.assertEqual(mod.main([]), 0)


if __name__ == "__main__":
    unittest.main()
