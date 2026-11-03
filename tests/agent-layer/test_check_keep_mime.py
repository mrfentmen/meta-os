"""Fixture test for check-keep-mime.sh: static only, no VM.

Clean tree exits 0 (the pdf evince-vs-atril split is an expected-with-note
MISMATCH, not failure); `sh -n` passes; an uncovered drop-in desktop fails
via a shadow tree in tmp (script paths are ROOT-derived from $0, so the
script itself is copied into the tmp tree). Subprocess sh; stdlib only.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_SCRIPT = os.path.join(_REPO, "agent-layer", "check-keep-mime.sh")
_KEEP = os.path.join(_REPO, "os-build", "metaos1-base", "packages.txt")
_CANON = os.path.join(_REPO, "os-build", "metaos1-base",
                      "defaults", "mimeapps.list")
_DROP = os.path.join(_REPO, "agent-layer", "desktop-entries",
                     "mimeapps.list")


def _run(*args):
    return subprocess.run(["sh"] + list(args),
                          capture_output=True, text=True)


class TestCheckKeepMime(unittest.TestCase):
    def test_clean_exits_zero(self):
        r = _run(_SCRIPT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_syntax_ok(self):
        r = _run("-n", _SCRIPT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_output_has_match_and_expected_pdf_note(self):
        r = _run(_SCRIPT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("MATCH", r.stdout)
        self.assertIn("application/pdf", r.stdout)
        self.assertIn("expected", r.stdout)

    def test_uncovered_desktop_fails(self):
        tmp = tempfile.mkdtemp(prefix="oc2-keepmime-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        al = os.path.join(tmp, "agent-layer")
        base = os.path.join(tmp, "os-build", "metaos1-base", "defaults")
        os.makedirs(al)
        os.makedirs(base)
        os.mkdir(os.path.join(al, "desktop-entries"))
        shadow = os.path.join(al, "check-keep-mime.sh")
        shutil.copy(_SCRIPT, shadow)
        open(os.path.join(al, "install.sh"), "w").close()
        shutil.copy(_KEEP, os.path.join(tmp, "os-build", "metaos1-base",
                                        "packages.txt"))
        shutil.copy(_CANON, os.path.join(base, "mimeapps.list"))
        drop = os.path.join(al, "desktop-entries", "mimeapps.list")
        shutil.copy(_DROP, drop)
        with open(drop, "a", encoding="utf-8") as fh:
            fh.write("application/x-fake=fakedesk.desktop\n")
        r = _run(shadow)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("fakedesk", r.stdout)


if __name__ == "__main__":
    unittest.main()
