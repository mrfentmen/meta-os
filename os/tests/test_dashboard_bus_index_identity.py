#!/usr/bin/env python3
"""DSH-026: bus.html and index.html are the same file (repo invariant).

Spec section 0 states the rule: after every dashboard change,
`diff bus.html index.html` must be empty. Earlier dashboard tests pin
this incidentally (each asserts text equality so its own panel check
covers both files); this file is DSH-026's own acceptance test, so
the invariant itself fails the suite if it ever breaks, regardless
of which panel change broke it.

Byte comparison, not text comparison: the two files must be
identical down to line endings and trailing bytes, because the
viewer is deployed as a single static file and a "same text, different
bytes" pair would still be two builds. No viewer code is changed here
— DSH-026 is the invariant, not a panel — so there is no JS to
node --check and no new timer or posting path.
"""
import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
INDEX = os.path.join(REPO, "index.html")


class BusIndexIdentityTest(unittest.TestCase):
    def test_files_exist_and_nonempty(self):
        for path in (BUS, INDEX):
            self.assertTrue(os.path.isfile(path), "%s missing" % path)
            self.assertGreater(os.path.getsize(path), 0,
                               "%s is empty" % path)

    def test_byte_identical(self):
        with open(BUS, "rb") as f:
            bus = f.read()
        with open(INDEX, "rb") as f:
            index = f.read()
        self.assertEqual(bus, index,
                         "bus.html and index.html differ (DSH-026 invariant)")

    def test_same_size(self):
        # Redundant with byte equality by construction, but it names
        # the cheapest check a deploy script can run (cmp -s / wc -c)
        # before falling back to a full diff.
        self.assertEqual(os.path.getsize(BUS), os.path.getsize(INDEX),
                         "bus.html and index.html sizes differ")


if __name__ == "__main__":
    unittest.main()
