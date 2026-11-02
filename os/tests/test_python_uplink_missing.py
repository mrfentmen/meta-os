"""Missing cases for the Python uplink (B220).

`test_os_uplink.py` covers the happy intake, the three rejection reasons,
backoff, queue-then-drain, crew mode with no key, input immutability, and
the `--once` path. This file covers the edges it does not:

- non-dict orders and non-string / falsy ids, including the current
  truthiness rule that accepts a whitespace-only id;
- a duplicate inside one batch, and a duplicate already pending while
  disconnected;
- an invalid pending record rejected and dropped on reconnect;
- crew mode with an empty-string key;
- state fields the caller owns but `tick` does not copy;
- a missing `received_at` staying `None`;
- the backoff cap at a very large failure count;
- CLI refusals: an orders file holding an object, and an unreadable key
  file.

No network, no bus, no model call: pure functions plus temp-file runs.
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "os", "uplink"))

import relay_uplink  # noqa: E402

NOW = 1000


def order(oid, text="Build a landing page", origin="phone", **extra):
    record = {"id": oid, "text": text, "origin": origin}
    record.update(extra)
    return record


class ValidateOrderMissingTest(unittest.TestCase):
    def test_non_dict_is_refused(self):
        for value in (None, [], "order", 7):
            self.assertEqual(relay_uplink.validate_order(value),
                             (False, "order is not an object"))

    def test_falsy_ids_are_missing_but_whitespace_is_accepted(self):
        self.assertEqual(relay_uplink.validate_order(order(0)),
                         (False, "order id missing"))
        self.assertEqual(relay_uplink.validate_order(order(False)),
                         (False, "order id missing"))
        # Current truthiness rule: " " is a non-empty string.
        self.assertEqual(relay_uplink.validate_order(order(" ")),
                         (True, ""))

    def test_non_string_text_is_empty(self):
        for value in (5, None, ["x"]):
            self.assertEqual(
                relay_uplink.validate_order(order("o1", text=value)),
                (False, "order text empty"))

    def test_falsy_origin_is_missing(self):
        self.assertEqual(relay_uplink.validate_order(order("o1", origin=0)),
                         (False, "order origin missing"))


class DuplicateMissingTest(unittest.TestCase):
    def test_duplicate_inside_one_batch_makes_one_record(self):
        state = relay_uplink.empty_state()
        events, state = relay_uplink.tick(
            state, [order("o1"), order("o1")], NOW, True, key="k")
        self.assertEqual([e["type"] for e in events],
                         ["intake", "duplicate"])
        self.assertEqual(state["seen_ids"], ["o1"])

    def test_disconnected_duplicate_of_pending_is_not_queued_twice(self):
        state = relay_uplink.empty_state()
        state["pending"] = [order("o1")]
        events, state = relay_uplink.tick(
            state, [order("o1")], NOW, False, key="k")
        self.assertEqual([e["type"] for e in events], ["duplicate"])
        self.assertEqual(len(state["pending"]), 1)

    def test_invalid_pending_record_is_rejected_and_dropped_on_drain(self):
        state = relay_uplink.empty_state()
        state["pending"] = [{"id": "bad", "text": "   ", "origin": "phone"}]
        events, state = relay_uplink.tick(
            state, [], NOW, True, key="k")
        self.assertEqual([e["type"] for e in events], ["rejected"])
        self.assertEqual(state["pending"], [])
        self.assertEqual(state["seen_ids"], [])


class CrewModeMissingTest(unittest.TestCase):
    def test_empty_string_key_is_still_unsigned(self):
        state = relay_uplink.empty_state()
        events, state = relay_uplink.tick(
            state, [order("o1")], NOW, True, key="", crew_mode=True)
        self.assertEqual(events[0]["type"], "unsigned-refused")
        self.assertEqual(len(state["pending"]), 1)


class StateShapeMissingTest(unittest.TestCase):
    def test_caller_owned_extra_state_fields_are_dropped(self):
        state = relay_uplink.empty_state()
        state["note"] = "caller-owned"
        _events, new_state = relay_uplink.tick(
            state, [], NOW, True, key="k")
        self.assertNotIn("note", new_state)
        self.assertEqual(set(new_state),
                         {"seen_ids", "pending", "failures", "next_retry_at"})

    def test_missing_state_keys_fall_back_to_defaults(self):
        events, new_state = relay_uplink.tick(
            {}, [order("o1")], NOW, True, key="k")
        self.assertEqual(events[0]["type"], "intake")
        self.assertEqual(new_state["failures"], 0)
        self.assertIsNone(new_state["next_retry_at"])


class RecordShapeMissingTest(unittest.TestCase):
    def test_missing_received_at_stays_none(self):
        events, _ = relay_uplink.tick(
            relay_uplink.empty_state(), [order("o1")], NOW, True, key="k")
        self.assertIsNone(events[0]["record"]["received_at"])

    def test_backoff_stays_capped_at_large_failure_counts(self):
        self.assertEqual(relay_uplink.backoff_seconds(1000), 300)
        self.assertEqual(relay_uplink.backoff_seconds(10 ** 6), 300)


class CliMissingTest(unittest.TestCase):
    def _run(self, orders_text, extra=None):
        tmp = tempfile.mkdtemp()
        orders_file = os.path.join(tmp, "orders.json")
        state_file = os.path.join(tmp, "state.json")
        with open(orders_file, "w", encoding="utf-8") as fh:
            fh.write(orders_text)
        argv = ["--once", "--orders-file", orders_file,
                "--state-file", state_file, "--now", str(NOW)]
        return relay_uplink.main(argv + list(extra or []))

    def test_orders_file_holding_an_object_exits_2(self):
        self.assertEqual(self._run("{}"), 2)

    def test_orders_file_holding_a_string_exits_2(self):
        self.assertEqual(self._run('"orders"'), 2)

    def test_unreadable_key_file_returns_2(self):
        tmp = tempfile.mkdtemp()
        missing = os.path.join(tmp, "no-key")
        self.assertEqual(self._run("[]", ["--key-file", missing]), 2)


if __name__ == "__main__":
    unittest.main()
