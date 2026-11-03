"""Fixture test for verify-dropin-desktop.sh: static only, no VM.

Copies agent-layer/desktop-entries to tmp, builds a matching manifest in
MANIFEST.md row format, then: clean install verifies (exit 0); a tampered
.desktop fails; a deleted mimeapps fails. Subprocess sh only; stdlib only.
"""
import hashlib
import os
import shutil
import subprocess
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_DROP = os.path.join(_REPO, "agent-layer", "desktop-entries")
_SCRIPT = os.path.join(_REPO, "agent-layer", "verify-dropin-desktop.sh")


def _sha(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


class TestVerifyDropinDesktop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="oc2-desktop-")
        self.appdir = os.path.join(self.tmp, "applications")
        os.mkdir(self.appdir)
        for name in sorted(os.listdir(_DROP)):
            shutil.copy(os.path.join(_DROP, name),
                        os.path.join(self.appdir, name))
        self.mimeapps = os.path.join(self.tmp, "mimeapps.list")
        shutil.copy(os.path.join(_DROP, "mimeapps.list"), self.mimeapps)
        self.manifest = os.path.join(self.tmp, "MANIFEST.md")
        with open(self.manifest, "w", encoding="utf-8") as fh:
            for name in sorted(os.listdir(_DROP)):
                fh.write("- `agent-layer/desktop-entries/%s` sha256 `%s`\n"
                         % (name, _sha(os.path.join(self.appdir, name))))

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _run(self):
        return subprocess.run(["sh", _SCRIPT, self.manifest,
                               self.appdir, self.mimeapps],
                              capture_output=True, text=True)

    def test_clean_verifies(self):
        r = self._run()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_tampered_desktop_fails(self):
        with open(os.path.join(self.appdir, "mousepad.desktop"),
                  "a", encoding="utf-8") as fh:
            fh.write("\n# tampered\n")
        self.assertNotEqual(self._run().returncode, 0)

    def test_missing_mimeapps_fails(self):
        os.unlink(self.mimeapps)
        self.assertNotEqual(self._run().returncode, 0)


if __name__ == "__main__":
    unittest.main()
