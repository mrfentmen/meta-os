"""intel/store.py: key layout + record round-trips (FND-004)."""
import json
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
from intel import store as istore  # noqa: E402


class KeyLayoutTest(RelayTestCase):
    def test_key_shapes(self):
        self.assertEqual(
            istore.brief_key("build", 1730000000),
            "muse-bus:intel:brief:build:1730000000")
        self.assertEqual(
            istore.brief_key("", 1730000000),
            "muse-bus:intel:brief:main:1730000000")
        self.assertEqual(
            istore.alert_key("a-17"), "muse-bus:intel:alert:a-17")
        self.assertEqual(
            istore.dispatch_key("d-3"), "muse-bus:intel:dispatch:d-3")
        self.assertEqual(istore.wd_key("pax"), "muse-bus:intel:wd:pax")
        self.assertEqual(istore.wd_beat_key(), "muse-bus:intel:wd:beat")
        self.assertEqual(istore.spend_key(), "muse-bus:intel:spend")

    def test_room_is_cleaned(self):
        self.assertEqual(
            istore.brief_key("Build Room!", 5),
            "muse-bus:intel:brief:buildroom:5")


class RecordRoundTripTest(RelayTestCase):
    def test_brief_round_trip(self):
        rec = {"room": "build", "kind": "morning", "text": "All quiet."}
        key = istore.put_brief("build", 1730000000, rec)
        self.assertEqual(key, "muse-bus:intel:brief:build:1730000000")
        self.assertEqual(istore.get_brief("build", 1730000000), rec)
        self.assertIn(key, self.fake.strings)

    def test_brief_missing_is_none(self):
        self.assertIsNone(istore.get_brief("build", 1))

    def test_alert_round_trip(self):
        rec = {"kind": "stall", "nick": "milo", "status": "open"}
        istore.put_alert("a-1", rec)
        self.assertEqual(istore.get_alert("a-1"), rec)
        self.assertIsNone(istore.get_alert("a-2"))

    def test_dispatch_round_trip(self):
        rec = {"goal": "ship it", "jobs": [1, 2], "status": "draft"}
        istore.put_dispatch("d-9", rec)
        self.assertEqual(istore.get_dispatch("d-9"), rec)
        self.assertIsNone(istore.get_dispatch("d-10"))


class WatchdogStateTest(RelayTestCase):
    def test_wd_round_trip(self):
        now = int(self.fake.now())
        istore.wd_beat("milo", last_seen=now, last_progress=now - 60,
                       claimed_jobs=[7, 9])
        self.assertEqual(istore.wd_get("milo"), {
            "last_seen": now,
            "last_progress": now - 60,
            "claimed_jobs": ["7", "9"],
        })

    def test_wd_partial_update_keeps_other_fields(self):
        istore.wd_beat("milo", last_seen=100, last_progress=90,
                       claimed_jobs=[3])
        istore.wd_beat("milo", last_progress=95)
        state = istore.wd_get("milo")
        self.assertEqual(state["last_seen"], 100)
        self.assertEqual(state["last_progress"], 95)
        self.assertEqual(state["claimed_jobs"], ["3"])

    def test_wd_missing_is_none(self):
        self.assertIsNone(istore.wd_get("ghost"))

    def test_wd_beat_requires_a_field(self):
        with self.assertRaises(ValueError):
            istore.wd_beat("milo")


class SpendLedgerTest(RelayTestCase):
    def test_spend_round_trip_and_total(self):
        e1 = {"ts": 100, "lane_feature": "brief", "tokens_in": 10,
              "tokens_out": 20, "est_cost": 0.5}
        e2 = {"ts": 200, "lane_feature": "dispatch", "tokens_in": 30,
              "tokens_out": 40, "est_cost": 0.25}
        istore.record_spend(e1)
        istore.record_spend(e2)
        self.assertEqual(istore.spend_entries(), [e1, e2])
        self.assertEqual(istore.spend_total(), 0.75)
        self.assertEqual(
            len(self.fake.lists["muse-bus:intel:spend"]), 2)

    def test_spend_empty(self):
        self.assertEqual(istore.spend_entries(), [])
        self.assertEqual(istore.spend_total(), 0.0)


class SelfBeatTest(RelayTestCase):
    def test_self_beat_writes_ts_key_with_ttl(self):
        # WDG-016 acceptance, store half: the beat key exists after
        # a beat, carries the tick ts in the dashboard's {ts}
        # shape, and expires on its own after the TTL so a dead
        # watchdog can never look alive.
        self.fake.t = 1000000.0
        now = int(self.fake.now())
        key = istore.wd_self_beat(now)
        self.assertEqual(key, "muse-bus:intel:wd:beat")
        raw = self.fake.api_get(f"get/{key}")
        self.assertEqual(json.loads(raw)["result"],
                         json.dumps({"ts": now}, sort_keys=True))
        self.assertEqual(istore.wd_self_beat_age(now), 0)
        self.fake.advance(40)
        self.assertEqual(istore.wd_self_beat_age(), 40)
        self.fake.advance(300)
        self.assertIsNone(istore.wd_self_beat_age())

    def test_self_beat_age_is_none_without_a_beat(self):
        # No beat, no invented age: the dashboard's "not read
        # yet" state, not a zero.
        self.assertIsNone(istore.wd_self_beat_age())
