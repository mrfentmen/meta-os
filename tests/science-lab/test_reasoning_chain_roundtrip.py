"""Step-chain round-trip (CB2-133). Pure."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import reasoning_chain  # noqa: E402


class ChainRoundTripTests(unittest.TestCase):
    def test_built_chain_round_trips_through_its_dict(self):
        built = reasoning_chain.build_step_chain([
            {"id": "a", "type": "brief"},
            {"id": "b", "type": "hypothesis", "parent_id": "a"},
        ])
        payload = reasoning_chain.chain_to_dict(built)
        self.assertEqual(reasoning_chain.chain_from_dict(payload), built)


if __name__ == "__main__":
    unittest.main()
