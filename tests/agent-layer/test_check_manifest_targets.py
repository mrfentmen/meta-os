"""Fixture test for check-manifest-targets.sh: static only, no VM.

Clean tree exits 0; `sh -n` passes; a GHOST row fails via a shadow tree in
tmp (script derives ROOT from $0, so script + manifest.py + unit/desktop
dirs are copied into tmp and one fake TARGETS row appended). Subprocess
sh; stdlib only.
"""
import os
import shutil
import subprocess
import tempfile
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_SCRIPT = os.path.join(_REPO, "agent-layer", "check-manifest-targets.sh")
_MANIFEST = os.path.join(_REPO, "agent-layer", "manifest.py")
_UNITS = os.path.join(_REPO, "agent-layer", "units")
_DESK = os.path.join(_REPO, "agent-layer", "desktop-entries")


def _run(*args):
    return subprocess.run(["sh"] + list(args),
                          capture_output=True, text=True)


class TestCheckManifestTargets(unittest.TestCase):
    def test_clean_exits_zero(self):
        r = _run(_SCRIPT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_syntax_ok(self):
        r = _run("-n", _SCRIPT)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    @unittest.skipUnless(os.path.isfile(_MANIFEST), "manifest.py missing")
    def test_ghost_detected(self):
        tmp = tempfile.mkdtemp(prefix="oc2-mftargets-")
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        al = os.path.join(tmp, "agent-layer")
        os.makedirs(os.path.join(al, "units"))
        os.makedirs(os.path.join(al, "desktop-entries"))
        shadow = os.path.join(al, "check-manifest-targets.sh")
        shutil.copy(_SCRIPT, shadow)
        mf = os.path.join(al, "manifest.py")
        shutil.copy(_MANIFEST, mf)
        for src, dst in ((_UNITS, os.path.join(al, "units")),
                         (_DESK, os.path.join(al, "desktop-entries"))):
            for name in sorted(os.listdir(src)):
                s = os.path.join(src, name)
                if os.path.isfile(s):
                    shutil.copy(s, os.path.join(dst, name))
        with open(mf, "a", encoding="utf-8") as fh:
            fh.write('    "agent-layer/units/zz-ghost-oc2.service",\n')
        r = _run(shadow)
        self.assertNotEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn("GHOST", r.stdout)
        self.assertIn("zz-ghost-oc2", r.stdout)


if __name__ == "__main__":
    unittest.main()
