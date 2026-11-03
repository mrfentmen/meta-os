"""OC2 desktop-entries drop-in validator: static only, no VM.

Checks the ONE-directory handoff OC1 copies (agent-layer/desktop-entries/):
- every .desktop parses, has Type/Name/Exec, has TryExec, no secrets
- degraded-off entries (evince) carry NoDisplay=true
- meta-agent-status.desktop is a byte-copy of Bond's iso/apps/desktop/ file
- mimeapps.list maps exactly text/plain, image/png, image/jpeg,
  application/pdf; every mapped desktop exists in this dir; no browser types
"""
import configparser
import os
import re
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_DROP = os.path.join(_REPO, "agent-layer", "desktop-entries")
_BOND_STATUS = os.path.join(_REPO, "iso", "apps", "desktop",
                            "meta-agent-status.desktop")

EXPECTED = (
    "mousepad.desktop",
    "ristretto.desktop",
    "atril.desktop",
    "evince.desktop",
    "thunar.desktop",
    "meta-agent-status.desktop",
)

MIME_EXPECTED = {
    "text/plain": "mousepad.desktop",
    "image/png": "ristretto.desktop",
    "image/jpeg": "ristretto.desktop",
    "application/pdf": "atril.desktop",
}


def _load_desktop(path):
    p = configparser.ConfigParser(interpolation=None, strict=True)
    p.optionxform = str
    # configparser requires a section header; .desktop files have one.
    p.read(path, encoding="utf-8")
    return p


class TestDesktopEntries(unittest.TestCase):
    def test_all_expected_files_present(self):
        for name in EXPECTED + ("mimeapps.list", "README.md"):
            self.assertTrue(os.path.isfile(os.path.join(_DROP, name)), name)

    def test_desktops_parse_and_have_required_keys(self):
        for name in EXPECTED:
            with self.subTest(name=name):
                d = _load_desktop(os.path.join(_DROP, name))
                self.assertIn("Desktop Entry", d.sections(), name)
                sec = d["Desktop Entry"]
                for key in ("Type", "Name", "Exec"):
                    self.assertIn(key, sec, f"{name}:{key}")
                self.assertEqual(sec["Type"], "Application", name)
                # TryExec gate: every OC2-authored entry must declare it.
                # meta-agent-status is a byte-copy of Bond's file (no
                # TryExec upstream) — exempt, covered by test below.
                if name == "meta-agent-status.desktop":
                    continue
                self.assertIn("TryExec", sec, f"{name}:TryExec")
                self.assertTrue(sec["TryExec"].strip(), f"{name}:TryExec empty")

    def test_degraded_off_entry_hidden(self):
        d = _load_desktop(os.path.join(_DROP, "evince.desktop"))
        sec = d["Desktop Entry"]
        self.assertEqual(sec.get("NoDisplay"), "true",
                         "evince is degraded-off until Hana acks")
        for name in ("mousepad.desktop", "ristretto.desktop",
                     "atril.desktop", "thunar.desktop",
                     "meta-agent-status.desktop"):
            sec2 = _load_desktop(os.path.join(_DROP, name))["Desktop Entry"]
            self.assertNotEqual(sec2.get("NoDisplay"), "true", name)

    def test_meta_agent_status_matches_bond(self):
        mine = open(os.path.join(_DROP, "meta-agent-status.desktop"),
                    "rb").read()
        bond = open(_BOND_STATUS, "rb").read()
        self.assertEqual(mine, bond, "must stay a byte-copy of Bond's file")

    def test_exec_targets_sane(self):
        allowed = {"mousepad", "ristretto", "atril", "evince", "thunar",
                   "meta-agent-status"}
        for name in EXPECTED:
            with self.subTest(name=name):
                exe = _load_desktop(os.path.join(_DROP, name))["Desktop Entry"]["Exec"]
                base = exe.split()[0].split("/")[-1]
                self.assertIn(base, allowed, f"{name}:Exec={exe}")

    def test_mimeapps_exact_coverage(self):
        mapped = {}
        for line in open(os.path.join(_DROP, "mimeapps.list"),
                         encoding="utf-8"):
            line = line.strip()
            if not line or line.startswith(("#", "[")):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                mapped[k.strip()] = v.strip()
        self.assertEqual(mapped, MIME_EXPECTED)
        for desktop in mapped.values():
            self.assertTrue(os.path.isfile(os.path.join(_DROP, desktop)),
                            f"mapped file missing: {desktop}")
        self.assertNotIn("text/html", mapped)

    def test_no_secrets_in_dropin(self):
        blob = ""
        for name in EXPECTED + ("mimeapps.list", "README.md"):
            with open(os.path.join(_DROP, name), errors="replace") as fh:
                blob += fh.read() + "\n"
        for pat in (r"sk-[A-Za-z0-9]{20,}",
                     r"BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY",
                     r"SPARK_API_KEY\s*=",
                     r"(?i)\b(password|passwd)\s*="):
            self.assertIsNone(re.search(pat, blob), pat)


if __name__ == "__main__":
    unittest.main()
