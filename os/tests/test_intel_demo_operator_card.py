"""DEM-016: the watchdog operator role and its failover card.

DEM-016's acceptance is two written things: the operator role
in the DEMO.md crew list, and manual commands on the failover
card. These tests pin both in place: DEMO.md names Milo as
watchdog operator and points at the card, and the card names
the three commands whose outputs were verified when the card
was written (silent-failure drill, catch measurement, single
tick) plus the two honest limits (never bus-post; the CLI
ticks snapshots, live-room reading waits on FND-014). The
drill scripts themselves are already pinned by their own test
files; this file pins the card, not the drills.
"""

import unittest

CARD = "intel/evals/demo_operator_card.md"
DEMO = "plan/DEMO.md"


class DemoOperatorCardTest(unittest.TestCase):
    def test_crew_list_names_milo_operator_and_card(self):
        with open(DEMO) as handle:
            demo = handle.read()
        self.assertIn("watchdog operator", demo)
        self.assertIn("intel/evals/demo_operator_card.md", demo)
        self.assertIn("DEM-016", demo)

    def test_card_lists_all_three_verified_commands(self):
        with open(CARD) as handle:
            card = handle.read()
        self.assertIn("python3 intel/drills/demo_silent_failure.py", card)
        self.assertIn("demo_silent_failure drill: PASS", card)
        self.assertIn("python3 intel/drills/demo_catch_time.py", card)
        self.assertIn("3/3 rehearsals under 90s", card)
        self.assertIn("python3 intel/watchdog.py --once", card)
        self.assertIn("watchdog: 0 alert(s)", card)

    def test_card_states_both_honest_limits(self):
        with open(CARD) as handle:
            card = handle.read()
        self.assertIn("Never post to the bus", card)
        self.assertIn("FND-014", card)
        self.assertIn("recorded fallback", card)


if __name__ == "__main__":
    unittest.main()
