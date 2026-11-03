"""Missing cases for the Python watchman (B218).

The existing `test_os_watchman.py` covers the wake/nudge decisions, the
counter-free rule, dedupe, and the `--once` CLI. This file covers the
refusal and boundary cases it does not:

- `normalize_agents` as a list (not a dict), with missing nicks,
  unregistered records, and non-dict entries;
- `is_sleeping` at the exact threshold, with a future heartbeat, and with
  non-numeric heartbeat values;
- `addressed_to` falling back from an empty `addressed_to` to `to`, and
  refusing a non-dict;
- `tick` with a non-list jobs input, and with a non-string status;
- the state-file merge preserving prior rung keys and sorting them;
- no state file being created when a cycle produces no events;
- the CLI usage refusals (`--interval <= 0`, negative stale window) and
  the missing-input-files read as empty.

No network, no bus, no model call: pure functions plus temp-file runs.
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "os", "watchman"))

import relay_watchman  # noqa: E402

NOW = 1000000
STALE = 300


class NormalizeAgentsMissingTest(unittest.TestCase):
    def test_list_form_drops_bad_records_and_unregistered(self):
        agents = [
            {"nick": "hana", "heartbeat_at": 10},
            {"heartbeat_at": 20},                 # no nick
            "not-a-record",                       # not a dict
            {"nick": "milo", "registered": False},  # not local
            {"nick": "", "heartbeat_at": 30},     # empty nick
            {"nick": "  ", "heartbeat_at": 40},   # whitespace nick
        ]
        out = relay_watchman.normalize_agents(agents)
        self.assertEqual(set(out), {"hana"})
        self.assertEqual(out["hana"]["nick"], "hana")

    def test_dict_form_drops_unregistered_and_keeps_nick(self):
        out = relay_watchman.normalize_agents(
            {"hana": {"heartbeat_at": 1},
             "milo": {"registered": False}})
        self.assertEqual(set(out), {"hana"})
        self.assertEqual(out["hana"]["nick"], "hana")

    def test_unknown_input_type_is_empty_not_an_error(self):
        for value in (None, 5, "hana"):
            self.assertEqual(relay_watchman.normalize_agents(value), {})


class IsSleepingBoundaryTest(unittest.TestCase):
    def test_exact_threshold_is_not_stale(self):
        agent = {"heartbeat_at": NOW - STALE}
        self.assertFalse(relay_watchman.is_sleeping(agent, NOW, STALE))

    def test_one_second_past_threshold_is_stale(self):
        agent = {"heartbeat_at": NOW - STALE - 1}
        self.assertTrue(relay_watchman.is_sleeping(agent, NOW, STALE))

    def test_future_heartbeat_is_not_stale(self):
        self.assertFalse(relay_watchman.is_sleeping(
            {"heartbeat_at": NOW + 1000}, NOW, STALE))

    def test_non_numeric_heartbeat_counts_as_never_seen(self):
        for value in (True, False, "100", [], {}):
            self.assertTrue(relay_watchman.is_sleeping(
                {"heartbeat_at": value}, NOW, STALE), repr(value))


class AddressedToMissingTest(unittest.TestCase):
    def test_empty_addressed_to_falls_back_to_legacy_to(self):
        self.assertEqual(
            relay_watchman.addressed_to({"addressed_to": "   ",
                                         "to": "milo"}), "milo")

    def test_both_empty_is_unaddressed(self):
        self.assertIsNone(relay_watchman.addressed_to(
            {"addressed_to": "", "to": "  "}))

    def test_non_dict_is_unaddressed(self):
        for value in (None, [], "hana"):
            self.assertIsNone(relay_watchman.addressed_to(value))


class TickInputMissingTest(unittest.TestCase):
    def test_non_list_jobs_is_empty_output(self):
        for value in (None, {}, "jobs", 7):
            self.assertEqual(
                relay_watchman.tick(value, {}, set(), NOW,
                                    heartbeat_stale_seconds=STALE),
                ([], []))

    def test_non_string_status_never_rings(self):
        events, keys = relay_watchman.tick(
            [{"id": "1", "status": None, "addressed_to": "hana"},
             {"id": "2", "status": 1, "addressed_to": "hana"}],
            {"hana": {"heartbeat_at": None}}, set(), NOW,
            heartbeat_stale_seconds=STALE)
        self.assertEqual((events, keys), ([], []))

    def test_lexicographically_odd_status_is_silent(self):
        events, _ = relay_watchman.tick(
            [{"id": "1", "status": "OPEN", "addressed_to": "hana"}],
            {"hana": {"heartbeat_at": None}}, set(), NOW,
            heartbeat_stale_seconds=STALE)
        self.assertEqual(events, [])


class StateMergeMissingTest(unittest.TestCase):
    def _paths(self, jobs, agents, state=None):
        tmp = tempfile.mkdtemp()
        jobs_path = os.path.join(tmp, "jobs.json")
        agents_path = os.path.join(tmp, "agents.json")
        state_path = os.path.join(tmp, "state.json")
        with open(jobs_path, "w", encoding="utf-8") as fh:
            json.dump(jobs, fh)
        with open(agents_path, "w", encoding="utf-8") as fh:
            json.dump(agents, fh)
        if state is not None:
            with open(state_path, "w", encoding="utf-8") as fh:
                json.dump(state, fh)
        return jobs_path, agents_path, state_path

    def test_prior_rung_keys_survive_and_output_is_sorted(self):
        jobs_path, agents_path, state_path = self._paths(
            [{"id": "7", "status": "open", "addressed_to": "hana"}],
            {"hana": {"heartbeat_at": None}},
            {"rung": ["wake:old", "nudge:4:100"]})
        events = relay_watchman._run_once(
            jobs_path, agents_path, state_path, NOW, STALE)
        self.assertEqual([e["kind"] for e in events], ["wake"])
        with open(state_path, encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["rung"],
                         ["nudge:4:100", "wake:7", "wake:old"])

    def test_no_events_leaves_no_state_file(self):
        jobs_path, agents_path, state_path = self._paths([], {})
        events = relay_watchman._run_once(
            jobs_path, agents_path, state_path, NOW, STALE)
        self.assertEqual(events, [])
        self.assertFalse(os.path.exists(state_path))

    def test_non_string_rung_entries_are_ignored(self):
        jobs_path, agents_path, state_path = self._paths(
            [{"id": "7", "status": "open", "addressed_to": "hana"}],
            {"hana": {"heartbeat_at": None}},
            {"rung": ["wake:old", 4, None]})
        relay_watchman._run_once(
            jobs_path, agents_path, state_path, NOW, STALE)
        with open(state_path, encoding="utf-8") as fh:
            state = json.load(fh)
        self.assertEqual(state["rung"], ["wake:7", "wake:old"])


class CliUsageMissingTest(unittest.TestCase):
    def _argv(self, *extra):
        tmp = tempfile.mkdtemp()
        return ["--once",
                "--jobs-file", os.path.join(tmp, "jobs.json"),
                "--agents-file", os.path.join(tmp, "agents.json"),
                "--now", str(NOW)] + list(extra)

    def test_zero_or_negative_interval_exits_2(self):
        self.assertEqual(relay_watchman.main(self._argv("--interval", "0")), 2)
        self.assertEqual(relay_watchman.main(self._argv("--interval", "-5")), 2)

    def test_negative_stale_window_exits_2(self):
        self.assertEqual(
            relay_watchman.main(
                self._argv("--heartbeat-stale-seconds", "-1")), 2)

    def test_missing_input_files_read_as_empty_with_exit_0(self):
        self.assertEqual(relay_watchman.main(self._argv()), 0)


if __name__ == "__main__":
    unittest.main()
