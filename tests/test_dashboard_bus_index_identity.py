"""DSH-026: there is exactly one dashboard page, and it does not drift.

The invariant used to be `diff bus.html index.html` empty — two files that had
to stay byte-identical. index.html then became an app hub (a Launchpad-style
list of pages the dock already lists) while bus.html stayed the dashboard, so
the two diverged and this suite went red. On 2026-11-04 the hub was deleted:
index.html is gone from the tree, and the invariant is now the *absence* of a
second copy rather than equality with one. bus.html is the dashboard.

Run: python3 -m pytest tests/test_dashboard_bus_index_identity.py -q
"""

import os
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUS = os.path.join(REPO, "bus.html")
# The path the deleted duplicate used to live at. It must never come back: a
# second copy of a 233 KB page is exactly how the two drifted apart before.
INDEX = os.path.join(REPO, "index.html")


class BusIndexIdentityTest(unittest.TestCase):
    def test_bus_exists_and_is_nonempty(self):
        self.assertTrue(os.path.isfile(BUS), "bus.html missing")
        self.assertGreater(os.path.getsize(BUS), 0, "bus.html is empty")

    def test_index_html_is_gone(self):
        # One dashboard page. If this fails, someone restored the duplicate or
        # the old hub, and the two will drift again.
        self.assertFalse(os.path.exists(INDEX),
                         "index.html must not exist; bus.html is the dashboard")
        self.assertFalse(os.path.exists(INDEX + ".html"),
                         "index.html.html must not exist either")

    def test_no_other_copy_of_the_dashboard(self):
        # A copy under another name is the same drift. Anything byte-identical
        # to bus.html at the repo root would be a second dashboard page.
        size = os.path.getsize(BUS)
        with open(BUS, "rb") as f:
            bus = f.read()
        twins = []
        for name in sorted(os.listdir(REPO)):
            if not name.endswith(".html") or name == "bus.html":
                continue
            path = os.path.join(REPO, name)
            if not os.path.isfile(path) or os.path.getsize(path) != size:
                continue
            with open(path, "rb") as f:
                if f.read() == bus:
                    twins.append(name)
        self.assertEqual(twins, [], "duplicate dashboard page(s): %s" % twins)


if __name__ == "__main__":
    unittest.main()
