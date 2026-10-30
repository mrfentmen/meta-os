"""Notification system: store records + intel.notify service/CLI.

Covers the durable half of the notification system (Del order
2026-10-28): validated notify records in the store keyspace,
dedupe-while-open, the open -> acknowledged -> resolved
lifecycle, history queries, the NOTIFY line format, and the
CLI (including --post, which is the only posting path and is
owned by the caller per the WDG-015 posting rule).
"""
import sys

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
from intel import notify as inotify  # noqa: E402
from intel import store as istore  # noqa: E402


class KeyLayoutTest(RelayTestCase):
    def test_key_shapes(self):
        self.assertEqual(istore.notify_key("ntf-abc"),
                         "muse-bus:intel:notify:ntf-abc")
        self.assertEqual(istore.notify_index_key(),
                         "muse-bus:intel:notify:index")


class WriteReadTest(RelayTestCase):
    def test_round_trip(self):
        rec = istore.write_notify(
            "overseer", "warning", "Job 12 stalled", topic="jobs",
            target="mrfentmen", room="1", dedupe_key="job-12-stall",
            now=1000)
        self.assertTrue(rec["id"].startswith("ntf-"))
        self.assertEqual(rec["status"], "open")
        self.assertEqual(rec["count"], 1)
        self.assertEqual(rec["room"], "1")
        self.assertEqual(istore.get_notify(rec["id"]), rec)

    def test_validation_rejects_bad_severity(self):
        with self.assertRaises(ValueError):
            istore.write_notify("overseer", "loud", "text", now=1000)

    def test_validation_rejects_empty_text(self):
        with self.assertRaises(ValueError):
            istore.write_notify("overseer", "info", "", now=1000)


class DedupeTest(RelayTestCase):
    def test_renotify_while_open_bumps_count(self):
        first = istore.write_notify(
            "watchman", "critical", "milo silent", topic="crew",
            dedupe_key="milo-silent", now=1000)
        second = istore.write_notify(
            "watchman", "critical", "milo silent", topic="crew",
            dedupe_key="milo-silent", now=1600)
        self.assertEqual(first["id"], second["id"])
        self.assertEqual(second["count"], 2)
        self.assertEqual(second["created_at"], 1000)
        self.assertEqual(second["last_seen"], 1600)
        self.assertEqual(second["status"], "open")

    def test_clock_skew_returns_existing_unchanged(self):
        first = istore.write_notify(
            "watchman", "info", "tick", dedupe_key="tick", now=2000)
        again = istore.write_notify(
            "watchman", "info", "tick", dedupe_key="tick", now=1500)
        self.assertEqual(again, first)

    def test_resolved_then_renotify_starts_fresh(self):
        first = istore.write_notify(
            "jobs", "info", "done", dedupe_key="job-9", now=1000)
        istore.resolve_notify(first["id"], now=1100)
        fresh = istore.write_notify(
            "jobs", "info", "done", dedupe_key="job-9", now=2000)
        self.assertEqual(fresh["id"], first["id"])
        self.assertEqual(fresh["status"], "open")
        self.assertEqual(fresh["count"], 1)
        self.assertEqual(fresh["created_at"], 2000)


class LifecycleTest(RelayTestCase):
    def test_ack_then_resolve(self):
        rec = istore.write_notify("os", "warning", "disk low",
                                  dedupe_key="disk", now=1000)
        acked = istore.acknowledge_notify(rec["id"], by="pax", now=1200)
        self.assertEqual(acked["status"], "acknowledged")
        self.assertEqual(acked["acknowledged_by"], "pax")
        self.assertEqual(acked["acknowledged_at"], 1200)
        # idempotent
        self.assertEqual(
            istore.acknowledge_notify(rec["id"], by="pax", now=1300),
            acked)
        done = istore.resolve_notify(rec["id"], now=1400)
        self.assertEqual(done["status"], "resolved")
        self.assertEqual(done["resolved_at"], 1400)
        self.assertEqual(istore.resolve_notify(rec["id"], now=1500), done)

    def test_ack_resolved_raises(self):
        rec = istore.write_notify("os", "info", "x", dedupe_key="x",
                                  now=1000)
        istore.resolve_notify(rec["id"], now=1100)
        with self.assertRaises(ValueError):
            istore.acknowledge_notify(rec["id"], now=1200)

    def test_missing_record_is_none(self):
        self.assertIsNone(istore.acknowledge_notify("ntf-nope"))
        self.assertIsNone(istore.resolve_notify("ntf-nope"))


class QueryTest(RelayTestCase):
    def test_filters(self):
        istore.write_notify("a", "info", "one", room="1",
                            dedupe_key="k1", now=1000)
        istore.write_notify("b", "critical", "two", room="1",
                            target="milo", dedupe_key="k2", now=2000)
        istore.write_notify("c", "info", "three", room="main",
                            dedupe_key="k3", now=3000)
        self.assertEqual(len(istore.query_notify()), 3)
        self.assertEqual(len(istore.query_notify(room="1")), 2)
        self.assertEqual(
            len(istore.query_notify(severity="critical")), 1)
        self.assertEqual(len(istore.query_notify(target="milo")), 1)
        self.assertEqual(len(istore.query_notify(since=2000)), 2)
        self.assertEqual(len(istore.query_notify(status="open")), 3)
        self.assertEqual(len(istore.query_notify(status="resolved")), 0)


class ServiceTest(RelayTestCase):
    def test_notify_returns_record_and_line(self):
        record, line = inotify.notify(
            "overseer", "warning", "Job 12 stalled", topic="jobs",
            target="mrfentmen", room="1", dedupe_key="j12", now=1000)
        self.assertEqual(
            line, f"NOTIFY:{record['id']} warning [jobs] "
                  "@mrfentmen Job 12 stalled")

    def test_line_flattens_newlines(self):
        record, line = inotify.notify(
            "os", "info", "line one\nline two", dedupe_key="nl",
            now=1000)
        self.assertNotIn("\n", line)

    def test_untargeted_line_has_no_mention(self):
        record, line = inotify.notify(
            "os", "info", "hello", dedupe_key="h", now=1000)
        self.assertEqual(
            line, f"NOTIFY:{record['id']} info [general] hello")


class CliTest(RelayTestCase):
    def test_send_list_ack_resolve(self):
        rc_, out, err = self.run_cli(
            inotify.main,
            ["send", "overseer", "critical", "Bridge down",
             "--topic", "relay", "--dedupe-key", "bridge"])
        self.assertEqual(rc_, 0, err)
        self.assertIn("NOTIFY:", out)
        nid = out.split()[0]

        rc_, out, err = self.run_cli(inotify.main, ["list"])
        self.assertEqual(rc_, 0, err)
        self.assertIn(nid, out)

        rc_, out, err = self.run_cli(
            inotify.main, ["ack", nid, "--by", "pax"])
        self.assertEqual(rc_, 0, err)
        self.assertIn("acknowledged", out)

        rc_, out, err = self.run_cli(inotify.main, ["resolve", nid])
        self.assertEqual(rc_, 0, err)
        self.assertIn("resolved", out)

        rc_, out, err = self.run_cli(inotify.main, ["ack", "ntf-nope"])
        self.assertEqual(rc_, 2)
        self.assertIn("NOT_FOUND", err)

    def test_send_post_pushes_line_to_room(self):
        rc_, out, err = self.run_cli(
            inotify.main,
            ["send", "pax", "info", "hello room", "--room", "1",
             "--post", "--dedupe-key", "hello-1"])
        self.assertEqual(rc_, 0, err)
        pushed = self.pushes_to("muse-bus:room:1")
        self.assertEqual(len(pushed), 1)
        self.assertIn("NOTIFY:", pushed[0])
        self.assertIn("hello room", pushed[0])
