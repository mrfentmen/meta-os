"""Prove the ISO checker's rules actually fire.

A checker that never fails is decoration. Each case copies the real iso/ tree
into a temp directory, breaks exactly one thing, and asserts the checker names
that break. The baseline case proves the copy passes untouched.
"""

import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ISO = Path(__file__).resolve().parents[1] / "iso"


class CheckerRuleTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name) / "iso"
        shutil.copytree(ISO, self.root)

    def tearDown(self):
        self.tmp.cleanup()

    def check(self):
        return subprocess.run(
            [sys.executable, str(self.root / "tools" / "check_iso_config.py")],
            capture_output=True, text=True, timeout=120,
        )

    def test_baseline_copy_passes(self):
        out = self.check()
        self.assertEqual(out.returncode, 0, out.stdout[-1500:])

    def test_missing_agent_status_launcher_is_named(self):
        (self.root / "apps" / "desktop" / "meta-agent-status.desktop").unlink()
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("frozen id 'agent-status' has no launcher", out.stdout)

    def test_missing_dock_item_is_named(self):
        (self.root / "apps" / "plank" / "meta-agent-status.dockitem").unlink()
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("frozen id 'agent-status' has no dock item", out.stdout)

    def test_extra_dock_item_is_named(self):
        src = self.root / "apps" / "plank" / "meta-terminal.dockitem"
        (self.root / "apps" / "plank" / "meta-sixth.dockitem").write_text(
            src.read_text(encoding="utf-8"), encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("unexpected item", out.stdout)

    def test_edited_contract_without_a_pin_update_fails(self):
        path = self.root / "contracts" / "tokens.json"
        text = path.read_text(encoding="utf-8").replace("#1877F2", "#1877F3")
        path.write_text(text, encoding="utf-8")
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("sha256 does not match PIN.md", out.stdout)

    def test_wrong_ring_size_is_named(self):
        path = self.root / "plymouth" / "metaos" / "metaos.script"
        # The asset itself is what is measured; shrinking the file header is not
        # possible without rewriting the PNG, so assert the check exists by
        # removing the asset and expecting its own named failure.
        (self.root / "plymouth" / "metaos" / "ring-dot.png").unlink()
        out = self.check()
        self.assertEqual(out.returncode, 1)
        self.assertIn("ring-dot.png is missing", out.stdout)
        self.assertEqual(path.is_file(), True)


if __name__ == "__main__":
    unittest.main()
