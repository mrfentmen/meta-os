"""Drop-in proposal lock: the OC2 mimeapps drop-in must differ from Hana's
canonical file in EXACTLY one mapping (pdf: evince -> atril) and nowhere
else. Reads Hana's file, never edits it. Static only, no VM.
"""
import os
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO = os.path.dirname(os.path.dirname(_HERE))
_CANON = os.path.join(_REPO, "os-build", "metaos1-base", "defaults",
                      "mimeapps.list")
_DROP = os.path.join(_REPO, "agent-layer", "desktop-entries", "mimeapps.list")


def _mappings(path):
    mapped = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith(("#", "[")):
                continue
            if "=" in line:
                k, v = line.split("=", 1)
                mapped[k.strip()] = v.strip()
    return mapped


class TestMimeappsProposalLock(unittest.TestCase):
    def test_differs_only_on_pdf(self):
        canon = _mappings(_CANON)
        drop = _mappings(_DROP)
        self.assertEqual(set(canon) | set(drop),
                         {"text/plain", "image/png", "image/jpeg",
                          "application/pdf"})
        for t in ("text/plain", "image/png", "image/jpeg"):
            self.assertEqual(drop[t], canon[t], t)
        self.assertEqual(canon["application/pdf"], "evince.desktop")
        self.assertEqual(drop["application/pdf"], "atril.desktop")

    def test_no_browser_type_in_either(self):
        for path in (_CANON, _DROP):
            with self.subTest(path=path):
                self.assertNotIn("text/html", _mappings(path))


if __name__ == "__main__":
    unittest.main()
