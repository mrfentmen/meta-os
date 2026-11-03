"""Step-chain limit tests (CB2-138..139). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning_chain  # noqa: E402


def linked(count):
    steps = []
    for i in range(count):
        step = {"id": "s%d" % i, "type": "brief"}
        if i:
            step["parent_id"] = "s%d" % (i - 1)
        steps.append(step)
    return steps


class ChainLimitTests(unittest.TestCase):
    def test_documented_depth_is_allowed_and_one_more_is_refused(self):
        reasoning_chain.build_step_chain(linked(reasoning_chain.MAX_CHAIN_DEPTH))
        with self.assertRaisesRegex(reasoning_chain.ChainError, "depth"):
            reasoning_chain.build_step_chain(
                linked(reasoning_chain.MAX_CHAIN_DEPTH + 1))

    def test_empty_chain_has_documented_form_and_rebuilds(self):
        payload = reasoning_chain.chain_to_dict([])
        self.assertEqual(payload,
                         {"kind": "reasoning-step-chain", "steps": []})
        self.assertEqual(reasoning_chain.chain_from_dict(payload), [])
        self.assertEqual(reasoning_chain.traverse_chain(payload), [])


if __name__ == "__main__":
    unittest.main()
