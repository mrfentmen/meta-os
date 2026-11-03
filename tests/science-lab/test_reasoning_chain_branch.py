"""Step-chain branch tests (CB2-147..148). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning_chain  # noqa: E402


def branch():
    return [
        {"id": "root", "type": "brief"},
        {"id": "b", "type": "hypothesis", "parent_id": "root"},
        {"id": "a", "type": "hypothesis", "parent_id": "root"},
        {"id": "a1", "type": "decomposition", "parent_id": "a"},
    ]


class BranchTests(unittest.TestCase):
    def test_two_children_are_both_kept_and_visited_once(self):
        chain = branch()
        order = reasoning_chain.traverse_chain(chain)
        self.assertEqual(sorted(order), ["a", "a1", "b", "root"])
        self.assertEqual(len(order), len(set(order)))
        self.assertEqual(reasoning_chain.chain_children(chain, "root"),
                         ["a", "b"])

    def test_traversal_is_deterministic(self):
        self.assertEqual(reasoning_chain.traverse_chain(branch()),
                         reasoning_chain.traverse_chain(branch()))


if __name__ == "__main__":
    unittest.main()
