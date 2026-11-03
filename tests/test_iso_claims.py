"""Tests for iso/tools/check_claims.py.

Each case builds a tiny tree with a doc, some files, and a claims file, so the
tool is tested against claims it has to compute rather than against the repo's
current numbers.
"""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "iso" / "tools" / "check_claims.py"


def run(root, claims):
    return subprocess.run(
        [sys.executable, str(TOOL), "--root", str(root), "--claims", str(claims)],
        capture_output=True, text=True, timeout=60)


class ClaimsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "docs").mkdir()
        (self.root / "widgets").mkdir()
        for name in ("one", "two"):
            (self.root / "widgets" / name).write_text("", encoding="utf-8")
        self.claims = self.root / "claims.json"
        self.write_claims([{
            "id": "widgets", "doc": "docs/a.md",
            "pattern": "we ship (\\d+) widgets", "source": "glob:widgets/*",
        }])

    def tearDown(self):
        self.tmp.cleanup()

    def write_claims(self, claims):
        self.claims.write_text(json.dumps(claims), encoding="utf-8")

    def test_a_true_claim_passes(self):
        (self.root / "docs" / "a.md").write_text("we ship 2 widgets\n", encoding="utf-8")
        out = run(self.root, self.claims)
        self.assertEqual(out.returncode, 0, out.stdout)
        self.assertIn("CLAIMS: OK", out.stdout)

    def test_a_stale_claim_fails_and_names_both_numbers(self):
        (self.root / "docs" / "a.md").write_text("we ship 2 widgets\n", encoding="utf-8")
        (self.root / "widgets" / "three").write_text("", encoding="utf-8")
        out = run(self.root, self.claims)
        self.assertEqual(out.returncode, 1)
        self.assertIn("STALE", out.stdout)
        self.assertIn("says 2", out.stdout)
        self.assertIn("tree has 3", out.stdout)

    def test_a_disappeared_claim_is_missing_not_ok(self):
        (self.root / "docs" / "a.md").write_text("we ship widgets\n", encoding="utf-8")
        out = run(self.root, self.claims)
        self.assertEqual(out.returncode, 1)
        self.assertIn("MISSING", out.stdout)

    def test_word_numbers(self):
        (self.root / "docs" / "a.md").write_text("we ship two widgets\n", encoding="utf-8")
        self.write_claims([{
            "id": "widgets", "doc": "docs/a.md",
            "pattern": "we ship (\\w+) widgets", "source": "glob:widgets/*",
            "kind": "word",
        }])
        self.assertEqual(run(self.root, self.claims).returncode, 0)

    def test_line_numbers_point_at_the_claim(self):
        (self.root / "docs" / "a.md").write_text("intro\n\nwe ship 2 widgets\n", encoding="utf-8")
        out = run(self.root, self.claims)
        self.assertIn("docs/a.md:3", out.stdout)

    def test_a_missing_document_is_missing(self):
        out = run(self.root, self.claims)
        self.assertEqual(out.returncode, 1)
        self.assertIn("document does not exist", out.stdout)

    def test_a_broken_claims_file_is_refused(self):
        self.claims.write_text("{not json", encoding="utf-8")
        self.assertEqual(run(self.root, self.claims).returncode, 2)

    def test_the_repo_itself_is_clean(self):
        out = subprocess.run([sys.executable, str(TOOL)], capture_output=True,
                             text=True, timeout=180)
        self.assertEqual(out.returncode, 0, out.stdout)


if __name__ == "__main__":
    unittest.main()
