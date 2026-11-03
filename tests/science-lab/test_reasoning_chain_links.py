"""Step-chain link tests (CB2-130..132). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning_chain  # noqa: E402


def steps():
    return [
        {"id": "brief", "type": "brief"},
        {"id": "hyp", "type": "hypothesis", "parent_id": "brief"},
        {"id": "decomp", "type": "decomposition", "parent_id": "hyp"},
    ]


class ChainLinkTests(unittest.TestCase):
    def test_three_linked_steps_keep_parent_pointers(self):
        built = reasoning_chain.build_step_chain(steps())
        self.assertEqual([s["id"] for s in built],
                         ["brief", "hyp", "decomp"])
        self.assertEqual([s["parent_id"] for s in built],
                         [None, "brief", "hyp"])

    def test_cycle_is_rejected(self):
        bad = [
            {"id": "a", "type": "brief", "parent_id": "b"},
            {"id": "b", "type": "critique", "parent_id": "a"},
        ]
        with self.assertRaisesRegex(reasoning_chain.ChainError, "cycle"):
            reasoning_chain.build_step_chain(bad)

    def test_missing_parent_is_named(self):
        bad = [{"id": "a", "type": "brief", "parent_id": "ghost"}]
        with self.assertRaisesRegex(reasoning_chain.ChainError, "ghost"):
            reasoning_chain.build_step_chain(bad)


if __name__ == "__main__":
    unittest.main()
