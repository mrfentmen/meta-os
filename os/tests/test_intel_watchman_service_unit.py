"""OS-122 follow-up: relay-watchman-watch.service unit shape (Milo lane).

The unit file is the only new artifact that can be checked on this VM: there
is no test image, so boot activation and a systemd restart stay owed and the
unit header says so. What is pinned here is that the unit execs the real
service-loop entry point with the production snapshot dir, orders after the
watchman it watches, restarts on failure per the OS-034 contract, and states
its machine-list gap instead of silently watching zero machines.
"""

import os
import unittest

UNIT_PATH = os.path.join("os", "services", "relay-watchman-watch.service")
SERVICE_PATH = os.path.join("intel", "watchman_service.py")


def _unit_lines():
    with open(UNIT_PATH) as handle:
        return handle.read().splitlines()


def _directive(lines, name):
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("#"):
            continue
        if stripped.startswith(name + "="):
            return stripped[len(name) + 1:]
    return None


class WatchmanWatchUnitTest(unittest.TestCase):
    def test_exec_runs_service_loop_entry_point(self):
        exec_start = _directive(_unit_lines(), "ExecStart")
        self.assertIsNotNone(exec_start)
        self.assertIn("/opt/relay/intel/watchman_service.py", exec_start)
        self.assertIn("--snapshot-dir /run/metaos", exec_start)
        self.assertIn("--machines ${WATCHMAN_WATCH_MACHINES}", exec_start)

    def test_ordering_restart_and_identity(self):
        lines = _unit_lines()
        self.assertIn("relay-watchman.service",
                      _directive(lines, "After"))
        self.assertEqual("on-failure", _directive(lines, "Restart"))
        self.assertEqual("relay", _directive(lines, "User"))
        self.assertEqual("/opt/relay", _directive(lines, "WorkingDirectory"))
        self.assertEqual("relay.target", _directive(lines, "WantedBy"))
        self.assertEqual("-/etc/metaos/watchman-watch.env",
                         _directive(lines, "EnvironmentFile"))

    def test_header_states_machine_list_gap_and_proof_gap(self):
        with open(UNIT_PATH) as handle:
            text = handle.read()
        folded = " ".join(text.replace("#", "").split())
        self.assertIn("no machine-naming convention exists", folded)
        self.assertIn("not a live watcher", folded)
        self.assertIn("NOT proven here", text)
        self.assertIn("relay.target wants", text)

    def test_service_module_points_at_unit(self):
        with open(SERVICE_PATH) as handle:
            text = handle.read()
        self.assertIn("relay-watchman-watch.service", text)
        self.assertNotIn("not a systemd unit in this repo", text)

    def test_no_em_dash_in_unit_file(self):
        with open(UNIT_PATH) as handle:
            text = handle.read()
        self.assertNotIn("\u2014", text)
        self.assertNotIn("\u2013", text)


if __name__ == "__main__":
    unittest.main()
