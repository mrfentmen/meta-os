"""Tests for tools/kernel_census.py (CB2-439..440)."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import kernel_census  # noqa: E402


class KernelCensus(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tree = Path(self.tmp.name)
        (self.tree / "src").mkdir()
        (self.tree / "src" / "main.rs").write_text("fn main() {}\n// two\n", encoding="utf-8")
        (self.tree / "src" / "sched.rs").write_text("let a = 1;", encoding="utf-8")
        (self.tree / "src" / "notes.py").write_text("print(1)\n", encoding="utf-8")
        (self.tree / "target").mkdir()
        (self.tree / "target" / "build.rs").write_text("ignored\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_filter_counts_rs_only(self):
        result = kernel_census.census(self.tree)
        self.assertEqual([f["path"] for f in result["files"]], ["src/main.rs", "src/sched.rs"])
        self.assertEqual(result["total_lines"], 3)
        self.assertEqual(result["skipped"], 1)

    def test_extension_filter_is_configurable(self):
        result = kernel_census.census(self.tree, (".py",))
        self.assertEqual([f["path"] for f in result["files"]], ["src/notes.py"])
        self.assertEqual(result["skipped"], 2)

    def test_build_dirs_are_ignored(self):
        paths = [f["path"] for f in kernel_census.census(self.tree)["files"]]
        self.assertFalse(any(p.startswith("target/") for p in paths), paths)

    def test_line_count_without_trailing_newline(self):
        self.assertEqual(kernel_census.count_lines(self.tree / "src" / "sched.rs"), 1)
        self.assertEqual(kernel_census.count_lines(self.tree / "src" / "main.rs"), 2)


if __name__ == "__main__":
    unittest.main()
