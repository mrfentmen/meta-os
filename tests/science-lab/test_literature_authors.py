"""Literature author tests (CB2-120..121). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import literature  # noqa: E402


class AuthorTests(unittest.TestCase):
    def test_single_string_and_list_both_normalise_to_a_list(self):
        self.assertEqual(literature.normalize_authors("Ada Lovelace"),
                         ["Ada Lovelace"])
        self.assertEqual(
            literature.normalize_authors(["Ada Lovelace", "Grace Hopper"]),
            ["Ada Lovelace", "Grace Hopper"])

    def test_whitespace_only_author_is_dropped(self):
        self.assertEqual(
            literature.normalize_authors(["Ada", "   ", "\t", "Grace"]),
            ["Ada", "Grace"])


if __name__ == "__main__":
    unittest.main()
