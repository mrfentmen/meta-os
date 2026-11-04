#!/usr/bin/env python3
"""Unit tests for eval/surveyor/surveyor_eval.py.

Run: python3 -m unittest test_surveyor_eval -v  (from eval/surveyor/)
or:  python3 -m unittest discover -s eval/surveyor -v
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from surveyor_eval import (  # noqa: E402
    base_reading, evaluate, run_scenarios, sensor_sane,
)


class TestPublishRules(unittest.TestCase):
    def test_scenario_table_all_pass(self):
        rows = run_scenarios()
        failures = [name for name, ok, _, _ in rows if not ok]
        self.assertEqual(failures, [])

    def test_stuck_sensor_not_sane(self):
        history = [base_reading(value=34.0),
                   base_reading(value=34.0, time_min=90)]
        self.assertFalse(sensor_sane(base_reading(value=34.0,
                                                  time_min=80), history))

    def test_sane_sensor_in_range(self):
        self.assertTrue(sensor_sane(base_reading(), []))

    def test_second_hand_labelled_never_publishes_alone(self):
        result = evaluate([base_reading(source="second-hand")])
        self.assertEqual(len(result["published"]), 0)

    def test_no_dispatch_without_cluster(self):
        readings = [base_reading(),
                    base_reading(device_id="node-2", device_class="node",
                                 value=34.5, time_min=110)]
        result = evaluate(readings)
        self.assertEqual(result["dispatched"], [])

    def test_cluster_counts_only_confirmed(self):
        # Three readings, but only two agree -> no cluster, no dispatch.
        readings = [base_reading(device_id="d1"),
                    base_reading(device_id="d2", value=34.5, time_min=105),
                    base_reading(device_id="d3", value=44.0, time_min=110)]
        result = evaluate(readings)
        self.assertEqual(result["clusters"], [])
        self.assertEqual(result["dispatched"], [])


if __name__ == "__main__":
    unittest.main()
