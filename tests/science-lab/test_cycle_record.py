"""Cycle record tests (CB2-159, 174). Offline."""
import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_LAB = os.path.join(os.path.dirname(os.path.dirname(_HERE)),
                    "os", "worlds", "science-lab")
sys.path.insert(0, _LAB)

import cycle  # noqa: E402


class CycleRecordTests(unittest.TestCase):
    def test_new_cycle_carries_state_and_validates(self):
        record = cycle.new_cycle("C1", "Does X change Y?")
        for key in ("cycle_id", "phase", "inputs", "outputs", "gate_state"):
            self.assertIn(key, record)
        self.assertEqual(cycle.validate_cycle_against_schema(record), [])

    def test_cycle_round_trips_through_its_dict_form(self):
        record = cycle.new_cycle("C2", "Does X change Y?")
        rebuilt = cycle.cycle_from_dict(cycle.cycle_to_dict(record))
        self.assertEqual(rebuilt, record)


if __name__ == "__main__":
    unittest.main()
