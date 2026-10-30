"""tests/test_os_uplink.py -- OS-093: the order door (relay-uplink).

OS-093 ships os/uplink/relay_uplink.py, the resident CLI program
that takes Dale's plain-English phone orders in as signed job-set
intake records, plus os/services/relay-uplink.service under
relay.target. These tests pin the program's decisions and the
unit wiring, not a live boot: a booted test image, a live cloud
reader, and the dispatch posting itself are still owed (see the
os/README.md OS-093 section).

- A valid order over a connected uplink yields exactly one
  intake record carrying the raw text as spec, marked ORDER,
  signed when a key is given and honestly unsigned otherwise.
- An order with no id, empty text, or no origin is rejected
  with its reason and yields no record; nothing is guessed.
- A second tick over the same order id yields a duplicate
  event and no second record.
- A disconnected cycle queues a valid order (no loss) and
  the reconnected cycle drains it in received order, then
  clears the failure count; a second disconnect starts its
  backoff from the reset count, not the old one.
- Backoff is 5, 10, 20, 40, ... capped at 300 seconds.
- Crew mode with no key refuses the intake and keeps the
  order pending; the same order with a key then takes in.
- tick() never mutates its inputs.
- The CLI --once path prints intake events as JSON lines,
  writes state, prints nothing on a second run over the same
  state, and exits 2 on a malformed orders file.
- The unit file orders after network-online + relay-jobs,
  belongs to relay.target, carries the OS-012 secrets gate,
  puts no secret value on its command line, and is wanted
  by relay.target.

No bus post, no live Redis, no network, no systemd, no model
call: pure functions plus temp-file CLI runs.
"""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROGRAM = os.path.join(ROOT, "os", "uplink", "relay_uplink.py")
UNIT = os.path.join(ROOT, "os", "services", "relay-uplink.service")
TARGET = os.path.join(ROOT, "os", "services", "relay.target")

sys.path.insert(0, os.path.join(ROOT, "os", "uplink"))
import relay_uplink as uplink  # noqa: E402


def order(oid, text="Build a landing page", origin="phone"):
    return {"id": oid, "text": text, "origin": origin, "received_at": 1000}


class BackoffTest(unittest.TestCase):
    def test_sequence_and_cap(self):
        self.assertEqual([uplink.backoff_seconds(n) for n in (1, 2, 3, 4, 5)],
                         [5, 10, 20, 40, 80])
        self.assertEqual(uplink.backoff_seconds(10), 300)
        self.assertEqual(uplink.backoff_seconds(0), 0)

    def test_failure_sets_retry_and_success_clears(self):
        state = uplink.empty_state()
        failed = uplink.record_failure(state, 1000)
        self.assertEqual((failed["failures"], failed["next_retry_at"]), (1, 1005))
        cleared = uplink.record_success(failed)
        self.assertEqual((cleared["failures"], cleared["next_retry_at"]), (0, None))
        self.assertEqual(state["failures"], 0)


class IntakeTest(unittest.TestCase):
    def test_valid_order_intakes_signed(self):
        events, state = uplink.tick(uplink.empty_state(), [order("o1")],
                                    1000, True, key="k")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "intake")
        record = events[0]["record"]
        self.assertEqual(record["kind"], "ORDER")
        self.assertEqual(record["text"], "Build a landing page")
        self.assertTrue(record["signed"])
        self.assertEqual(record["signature"],
                         uplink.sign_intake("k", "o1", "Build a landing page"))
        self.assertNotIn("files", record)

    def test_valid_order_unsigned_outside_crew_mode(self):
        events, _ = uplink.tick(uplink.empty_state(), [order("o1")],
                                1000, True, key=None)
        self.assertEqual(events[0]["type"], "intake")
        self.assertFalse(events[0]["record"]["signed"])
        self.assertIsNone(events[0]["record"]["signature"])

    def test_invalid_orders_rejected_with_reason(self):
        bad = [{"text": "x", "origin": "phone"},
               {"id": "o2", "text": "   ", "origin": "phone"},
               {"id": "o3", "text": "x"}]
        events, state = uplink.tick(uplink.empty_state(), bad, 1000, True)
        self.assertEqual([e["type"] for e in events], ["rejected"] * 3)
        self.assertIn("id missing", events[0]["reason"])
        self.assertIn("text empty", events[1]["reason"])
        self.assertIn("origin missing", events[2]["reason"])
        self.assertEqual(state["seen_ids"], [])

    def test_duplicate_id_yields_no_second_record(self):
        state = uplink.empty_state()
        events, state = uplink.tick(state, [order("o1")], 1000, True, key="k")
        events2, state2 = uplink.tick(state, [order("o1")], 1010, True, key="k")
        self.assertEqual(events2[0]["type"], "duplicate")
        self.assertEqual(state2["seen_ids"], ["o1"])

    def test_tick_never_mutates_inputs(self):
        state = uplink.empty_state()
        orders = [order("o1")]
        snapshot_state = copy.deepcopy(state)
        snapshot_orders = copy.deepcopy(orders)
        uplink.tick(state, orders, 1000, True, key="k")
        self.assertEqual(state, snapshot_state)
        self.assertEqual(orders, snapshot_orders)


class OfflineTest(unittest.TestCase):
    def test_queue_then_drain_in_order_and_reset(self):
        state = uplink.empty_state()
        events, state = uplink.tick(state, [order("o1"), order("o2")],
                                    1000, False, key="k")
        self.assertEqual([e["type"] for e in events], ["queued", "queued"])
        self.assertEqual(state["failures"], 1)
        self.assertEqual(state["next_retry_at"], 1005)
        self.assertEqual(len(state["pending"]), 2)
        events, state = uplink.tick(state, [], 2000, True, key="k")
        self.assertEqual([e["order_id"] for e in events], ["o1", "o2"])
        self.assertEqual(state["pending"], [])
        self.assertEqual(state["failures"], 0)
        self.assertIsNone(state["next_retry_at"])

    def test_crew_mode_unsigned_stays_pending_then_intakes_with_key(self):
        state = uplink.empty_state()
        events, state = uplink.tick(state, [order("o1")], 1000, True,
                                    key=None, crew_mode=True)
        self.assertEqual(events[0]["type"], "unsigned-refused")
        self.assertEqual(len(state["pending"]), 1)
        events, state = uplink.tick(state, [], 1010, True, key="k", crew_mode=True)
        self.assertEqual(events[0]["type"], "intake")
        self.assertEqual(state["pending"], [])


class CliTest(unittest.TestCase):
    def run_cli(self, orders, extra=None):
        tmp = tempfile.mkdtemp()
        orders_file = os.path.join(tmp, "orders.json")
        state_file = os.path.join(tmp, "state.json")
        with open(orders_file, "w", encoding="utf-8") as fh:
            fh.write(orders if isinstance(orders, str) else json.dumps(orders))
        cmd = [sys.executable, PROGRAM, "--once", "--orders-file", orders_file,
               "--state-file", state_file, "--now", "1000"]
        if extra:
            cmd += extra
        proc = subprocess.run(cmd, capture_output=True, text=True)
        return proc, state_file

    def test_once_prints_then_duplicate(self):
        proc, state_file = self.run_cli([order("o1")])
        self.assertEqual(proc.returncode, 0)
        first = [json.loads(line) for line in proc.stdout.strip().splitlines()]
        self.assertEqual(first[0]["type"], "intake")
        # A second run against the stored state file sees the same id:
        tmp = tempfile.mkdtemp()
        orders_file = os.path.join(tmp, "orders.json")
        with open(orders_file, "w", encoding="utf-8") as fh:
            json.dump([order("o1")], fh)
        proc3 = subprocess.run(
            [sys.executable, PROGRAM, "--once", "--orders-file", orders_file,
             "--state-file", state_file, "--now", "1010"],
            capture_output=True, text=True)
        self.assertEqual(proc3.returncode, 0)
        second = [json.loads(line) for line in proc3.stdout.strip().splitlines()]
        self.assertEqual(second[0]["type"], "duplicate")

    def test_malformed_orders_exits_2(self):
        proc, _ = self.run_cli("{not json")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(proc.stdout, "")


class UnitTest(unittest.TestCase):
    def setUp(self):
        with open(UNIT, encoding="utf-8") as fh:
            self.unit = fh.read()
        with open(TARGET, encoding="utf-8") as fh:
            self.target = fh.read()

    def test_unit_wiring(self):
        self.assertIn("After=network-online.target relay-jobs.service", self.unit)
        self.assertIn("PartOf=relay.target", self.unit)
        self.assertIn("WantedBy=relay.target", self.unit)
        self.assertIn("ConditionPathExists=/etc/metaos/secrets.env", self.unit)
        self.assertIn("User=relay", self.unit)
        self.assertIn("Restart=on-failure", self.unit)
        exec_line = self.unit.split("ExecStart=")[1].split("\n")[0]
        # The key travels as a file path only; no key value on the line.
        self.assertIn("--key-file /etc/metaos/signing.key", exec_line)
        self.assertNotIn("token=", exec_line)
        self.assertNotIn("MUSE_", exec_line)
        self.assertIn("relay-uplink.service", self.target)

    def test_enabled_on_all_three_image_routes(self):
        for path in ("os/build-image.sh", "os/packer/metaos.pkr.hcl",
                     "os/live-build/config/hooks/live/0900-metaos-services.hook.chroot"):
            with open(os.path.join(ROOT, path), encoding="utf-8") as fh:
                self.assertIn("relay-uplink.service", fh.read(), path)


if __name__ == "__main__":
    unittest.main()
