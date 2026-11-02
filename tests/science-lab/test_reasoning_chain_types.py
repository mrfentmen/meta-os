"""Step-chain type tests (CB2-142..143). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning_chain  # noqa: E402


class ChainTypeTests(unittest.TestCase):
    def test_unknown_type_is_rejected(self):
        with self.assertRaisesRegex(reasoning_chain.ChainError, "unknown type"):
            reasoning_chain.build_step_chain(
                [{"id": "a", "type": "teleport"}])

    def test_every_documented_type_is_accepted(self):
        for step_type in reasoning_chain.CHAIN_STEP_TYPES:
            built = reasoning_chain.build_step_chain(
                [{"id": "s", "type": step_type}])
            self.assertEqual(built[0]["type"], step_type)


if __name__ == "__main__":
    unittest.main()
