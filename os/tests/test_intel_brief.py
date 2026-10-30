"""intel/brief.py: brief section extractors (Hana lane, BRF-004/005/006).

Pure-function tests: no network, no Redis, no Spark. Fixtures here
are hand-written snapshot dicts in the shape documented in
intel/brief.py. The acceptance check against Buffy's busy fixture
(FND-023) is still pending — that fixture is not in this repo yet —
so these tests prove the extractor logic on planted data, and the
busy-fixture check must still be run when it lands.
"""

import sys
import unittest

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from intel import brief  # noqa: E402


class DecisionsTest(unittest.TestCase):
    def test_three_planted_decisions_found_in_order(self):
        snapshot = {"messages": [
            {"nick": "pax", "text": "hello, working on the plan"},
            {"nick": "pax", "text": "DECISION: ship the brief panel first"},
            {"nick": "milo", "text": "DONE: watchdog loop runs on the stall fixture"},
            {"nick": "rowan", "text": "just checking the viewer"},
            {"nick": "pax", "text": "BLOCKED: dispatch needs the Spark endpoint"},
        ]}
        got = brief.extract_decisions(snapshot)
        self.assertEqual(len(got), 3)
        self.assertEqual(got[0]["kind"], "decision")
        self.assertEqual(got[0]["text"], "ship the brief panel first")
        self.assertEqual(got[0]["nick"], "pax")
        self.assertEqual(got[1]["kind"], "done")
        self.assertEqual(got[1]["text"],
                         "watchdog loop runs on the stall fixture")
        self.assertEqual(got[2]["kind"], "blocked")
        self.assertEqual(got[2]["text"],
                         "dispatch needs the Spark endpoint")

    def test_bus_string_messages_also_work(self):
        snapshot = {"messages": [
            "pax: DECISION: freeze the wire format today",
            "milo: nothing to report",
        ]}
        got = brief.extract_decisions(snapshot)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["nick"], "pax")
        self.assertEqual(got[0]["text"], "freeze the wire format today")

    def test_no_markers_means_no_decisions(self):
        snapshot = {"messages": [
            {"nick": "pax", "text": "we should probably decide soon"},
        ]}
        self.assertEqual(brief.extract_decisions(snapshot), [])

    def test_empty_snapshot_is_empty_not_an_error(self):
        self.assertEqual(brief.extract_decisions({}), [])
        self.assertEqual(brief.extract_decisions(None), [])


class BlockedTest(unittest.TestCase):
    def test_blocked_reasons_verbatim_character_for_character(self):
        snapshot = {"jobs": [
            {"id": "3", "title": "dispatch poster", "status": "claimed",
             "claim": "pax", "note": "working"},
            {"id": "7", "title": "spark client", "status": "blocked",
             "note": "waiting on the real Spark endpoint, not a fake one"},
            {"id": "9", "title": "brief panel", "status": "blocked",
             "note": "needs the frozen payload contract (BRF-042)"},
            {"id": "11", "title": "watchdog loop", "status": "done",
             "note": "finished"},
        ]}
        got = brief.extract_blocked(snapshot)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0]["id"], "7")
        self.assertEqual(
            got[0]["reason"],
            "waiting on the real Spark endpoint, not a fake one")
        self.assertEqual(got[1]["reason"],
                         "needs the frozen payload contract (BRF-042)")

    def test_blocked_job_without_note_gets_empty_reason(self):
        snapshot = {"jobs": [
            {"id": "5", "title": "mystery job", "status": "blocked"},
        ]}
        got = brief.extract_blocked(snapshot)
        self.assertEqual(got, [{"id": "5", "title": "mystery job",
                                "reason": ""}])

    def test_no_blocked_jobs_is_empty(self):
        self.assertEqual(brief.extract_blocked({"jobs": []}), [])
        self.assertEqual(brief.extract_blocked({}), [])


class OwnersTest(unittest.TestCase):
    def test_claim_nick_maps_to_titles_in_order(self):
        snapshot = {"jobs": [
            {"id": "2", "title": "brief panel", "status": "claimed",
             "claim": "rowan", "claimed_at": 1000,
             "last_progress_at": 1500},
            {"id": "3", "title": "dispatch poster", "status": "claimed",
             "claim": "pax", "claimed_at": 1100},
            {"id": "4", "title": "watchdog loop", "status": "claimed",
             "claim": "rowan", "claimed_at": 1200,
             "last_progress_at": 1600},
            {"id": "5", "title": "open job", "status": "open"},
            {"id": "6", "title": "blocked job", "status": "blocked"},
        ]}
        got = brief.extract_owners(snapshot)
        self.assertEqual(len(got), 2)
        self.assertEqual(got[0]["nick"], "rowan")
        self.assertEqual(
            [(j["id"], j["title"]) for j in got[0]["jobs"]],
            [("2", "brief panel"), ("4", "watchdog loop")])
        self.assertEqual(got[0]["jobs"][0]["last_progress_age"], 1500)
        self.assertEqual(got[1]["nick"], "pax")
        # No last_progress_at in the tree yet: falls back to claim time.
        self.assertEqual(got[1]["jobs"][0]["last_progress_age"], 1100)

    def test_unclaimed_jobs_are_never_assigned(self):
        snapshot = {"jobs": [
            {"id": "5", "title": "open job", "status": "open"},
        ]}
        self.assertEqual(brief.extract_owners(snapshot), [])

    def test_done_job_with_lingering_claim_is_not_owned(self):
        snapshot = {"jobs": [
            {"id": "2", "title": "brief panel", "status": "done",
             "claim": "rowan"},
        ]}
        self.assertEqual(brief.extract_owners(snapshot), [])


class TemplateBriefTest(unittest.TestCase):
    def test_template_brief_marked_and_readable_without_llm(self):
        snapshot = {
            "messages": [
                {"nick": "pax",
                 "text": "DECISION: ship the brief panel first"},
            ],
            "jobs": [
                {"id": "2", "title": "brief panel", "status": "claimed",
                 "claim": "rowan", "claimed_at": 1000},
                {"id": "7", "title": "spark client", "status": "blocked",
                 "note": "waiting on the real Spark endpoint"},
            ],
            "alerts": [{"id": "ALERT-1", "summary": "stall on job 2"}],
        }
        text = brief.compose_template_brief(snapshot)
        self.assertTrue(text.startswith("TEMPLATE"))
        self.assertIn("ship the brief panel first", text)
        self.assertIn("brief panel", text)
        self.assertIn("waiting on the real Spark endpoint", text)
        self.assertIn("ALERT-1", text)
        # No Spark call is made: this function takes only a snapshot
        # and returns plain text; there is no transport to kill.
        self.assertNotIn("Spark", text.split("\n", 1)[1].replace(
            "waiting on the real Spark endpoint", ""))


class MultilingualSafetyTest(unittest.TestCase):
    # BRF-021: briefs stay English even when bus chatter contains
    # other languages. The eval case is mixed-language CHATTER
    # (no decision/blocked markers): chatter never enters a brief,
    # because only structured facts (markers, jobs, alerts) do.
    # A job title or blocked reason that must be named is still
    # quoted exactly as recorded (BRF-005 verbatim rule wins over
    # translation); that exception is stated in prompt rule 6 and
    # is not covered by this chatter-only case.
    FOREIGN_LINES = [
        "Bonjour, je travaille sur le tableau de bord",
        "Hola, estoy revisando el panel del equipo",
        "Ich pruefe gerade die Aufgabenliste",
    ]

    def _snapshot_with_foreign_chatter(self):
        messages = [{"nick": nick, "text": text} for nick, text in [
            ("rowan", self.FOREIGN_LINES[0]),
            ("milo", self.FOREIGN_LINES[1]),
            ("del", self.FOREIGN_LINES[2]),
            ("pax", "DECISION: ship the brief panel first"),
        ]]
        return {
            "messages": messages,
            "jobs": [
                {"id": "2", "title": "brief panel", "status": "claimed",
                 "claim": "rowan", "claimed_at": 1000},
                {"id": "7", "title": "spark client", "status": "blocked",
                 "note": "waiting on the real Spark endpoint"},
            ],
            "alerts": [{"id": "ALERT-1", "summary": "stall on job 2"}],
        }

    def test_foreign_chatter_never_enters_the_brief(self):
        text = brief.compose_template_brief(
            self._snapshot_with_foreign_chatter())
        for line in self.FOREIGN_LINES:
            self.assertNotIn(line, text)
        # The English facts still land: decision, job, reason, alert.
        self.assertIn("ship the brief panel first", text)
        self.assertIn("brief panel", text)
        self.assertIn("waiting on the real Spark endpoint", text)
        self.assertIn("ALERT-1", text)
        for heading in ["Decisions", "In flight", "Owners",
                        "Blocked and why", "Watch items"]:
            self.assertIn(heading, text)

    def test_foreign_chatter_only_yields_english_sections(self):
        snapshot = {"messages": [
            {"nick": "rowan", "text": self.FOREIGN_LINES[0]},
            {"nick": "milo", "text": self.FOREIGN_LINES[1]},
        ]}
        text = brief.compose_template_brief(snapshot)
        for line in self.FOREIGN_LINES:
            self.assertNotIn(line, text)
        self.assertIn("Nothing reported in this window", text)


class EmptyRoomTest(unittest.TestCase):
    def test_empty_snapshot_yields_no_activity_yet_no_jobs(self):
        text = brief.compose_template_brief({})
        self.assertIn("no activity yet", text)
        # Manifest of job names that must NOT appear: the brief
        # invents nothing, so none of these real repo job titles
        # may show up in an empty-room brief.
        for title in ["brief panel", "dispatch poster",
                      "watchdog loop", "spark client"]:
            self.assertNotIn(title, text)
        text2 = brief.compose_template_brief(
            {"messages": [], "jobs": [], "alerts": []})
        self.assertIn("no activity yet", text2)


class TrimmedHistoryTest(unittest.TestCase):
    def test_truncated_window_states_its_start_point_up_front(self):
        snapshot = {
            "source_window": ("2026-10-26 08:00 ET onward "
                              "(history before this point is not "
                              "in this window)"),
            "window_truncated": True,
            "messages": [
                {"nick": "pax",
                 "text": "DECISION: ship the brief panel first"},
            ],
            "jobs": [],
        }
        text = brief.compose_template_brief(snapshot)
        window_line = [line for line in text.splitlines()
                       if line.startswith("Window:")][0]
        self.assertIn("2026-10-26 08:00 ET", window_line)
        # The window line comes before the first section.
        self.assertLess(text.index(window_line),
                        text.index("Decisions"))

    def test_no_window_stated_is_said_plainly(self):
        snapshot = {"messages": [
            {"nick": "pax", "text": "DECISION: x"},
        ]}
        text = brief.compose_template_brief(snapshot)
        self.assertIn("Window: not stated in this snapshot", text)


class RedactionTest(unittest.TestCase):
    def test_planted_fake_token_absent_and_redacted_marker_present(self):
        fake_token = "ghp_" + "a" * 36
        snapshot = {"jobs": [
            {"id": "7", "title": "spark client", "status": "blocked",
             "note": f"key leaked in a note: {fake_token}"},
        ]}
        text = brief.compose_template_brief(snapshot)
        self.assertNotIn(fake_token, text)
        self.assertIn("[redacted]", text)
        self.assertIn("spark client", text)

    def test_named_assignment_and_bearer_redacted(self):
        text = brief.redact_secrets(
            "api_key=supersecret123 and Bearer abcdefghij123456")
        self.assertNotIn("supersecret123", text)
        self.assertNotIn("abcdefghij123456", text)
        self.assertIn("[redacted]", text)

    def test_commit_hash_is_not_redacted(self):
        commit = "a" * 40
        text = brief.redact_secrets(f"DONE: 3 {commit}")
        self.assertIn(commit, text)


class StalenessTest(unittest.TestCase):
    def test_age_seconds_grows_with_fake_clock(self):
        record = {"generated_at": 1000}
        self.assertEqual(brief.brief_age_seconds(record, now=1000), 0)
        self.assertEqual(brief.brief_age_seconds(record, now=4600),
                         3600)
        # Older than 2 hours (7200 seconds) is the stale line.
        self.assertGreater(
            brief.brief_age_seconds(record, now=1000 + 7201), 7200)

    def test_missing_generated_at_gives_no_age(self):
        self.assertIsNone(brief.brief_age_seconds({}))
        self.assertIsNone(
            brief.brief_age_seconds({"generated_at": "yesterday"}))


class WindowCapTest(unittest.TestCase):
    def test_message_count_cap_keeps_last_500(self):
        messages = [{"nick": "pax", "text": f"message {i}", "ts": 2000 + i}
                    for i in range(600)]
        capped = brief.cap_snapshot_window(
            {"messages": messages}, max_messages=500, max_hours=None,
            now=3000)
        self.assertEqual(len(capped["messages"]), 500)
        self.assertEqual(capped["messages"][0]["text"], "message 100")
        self.assertEqual(capped["source_window"]["messages_dropped"],
                         100)
        self.assertEqual(capped["source_window"]["messages_kept"], 500)

    def test_time_cap_drops_messages_older_than_24h(self):
        messages = [
            {"nick": "pax", "text": "old", "ts": 1000},
            {"nick": "pax", "text": "recent", "ts": 90000},
        ]
        capped = brief.cap_snapshot_window(
            {"messages": messages}, max_messages=500, max_hours=24,
            now=100000)
        self.assertEqual([m["text"] for m in capped["messages"]],
                         ["recent"])

    def test_cap_record_names_values_in_brief_window_line(self):
        capped = brief.cap_snapshot_window(
            {"messages": [{"nick": "pax", "text": "hi", "ts": 1000}]},
            now=2000)
        text = brief.compose_template_brief(capped)
        self.assertIn("last 500 messages", text)
        self.assertIn("last 24 hours", text)


class SchemaTest(unittest.TestCase):
    def test_valid_brief_record_passes(self):
        record = {
            "room": "build-relay-intel",
            "generated_at": 1793000000,
            "kind": "morning",
            "sections": {name: [] for name in brief.BRIEF_SECTIONS},
            "source_window": "last 24 hours",
            "model": "template",
            "spend_id": None,
        }
        self.assertEqual(brief.validate_brief_record(record), [])

    def test_invalid_record_lists_each_bad_field(self):
        record = {
            "room": "",
            "generated_at": "yesterday",
            "kind": "evening",
            "sections": {"Decisions": "not a list"},
            "source_window": 42,
            "model": "",
            "spend_id": 7,
        }
        errors = brief.validate_brief_record(record)
        self.assertTrue(any("room" in e for e in errors))
        self.assertTrue(any("generated_at" in e for e in errors))
        self.assertTrue(any("kind" in e for e in errors))
        self.assertTrue(any("sections" in e for e in errors))
        self.assertTrue(any("source_window" in e for e in errors))
        self.assertTrue(any("model" in e for e in errors))
        self.assertTrue(any("spend_id" in e for e in errors))

    def test_cap_dict_source_window_is_valid(self):
        record = {
            "room": "main",
            "generated_at": 1793000000,
            "kind": "ondemand",
            "sections": {name: [] for name in brief.BRIEF_SECTIONS},
            "source_window": {"max_messages": 500, "max_hours": 24,
                              "messages_kept": 12, "messages_dropped": 0},
            "model": "template",
            "spend_id": None,
        }
        self.assertEqual(brief.validate_brief_record(record), [])


class BudgetTest(unittest.TestCase):
    def test_budgets_are_the_fnd034_values(self):
        self.assertEqual(brief.BRIEF_BUDGETS["morning"], 220)
        self.assertEqual(brief.BRIEF_BUDGETS["onjoin"], 150)
        self.assertEqual(brief.BRIEF_BUDGETS["ondemand"], 300)

    def test_brief_over_budget_fails(self):
        long_text = "word " * 221
        self.assertTrue(brief.brief_exceeds_budget("morning", long_text))
        self.assertFalse(brief.brief_exceeds_budget("ondemand", long_text))

    def test_brief_at_budget_passes(self):
        self.assertFalse(
            brief.brief_exceeds_budget("morning", "word " * 220))


class ComposerTest(unittest.TestCase):
    class _FakeClient:
        def __init__(self, text=None, error=None):
            self.text = text
            self.error = error

        def complete(self, prompt, system=None, lane_feature=None):
            if self.error is not None:
                raise self.error
            return self.text

    def test_spark_path_stays_within_budget_and_keeps_sections(self):
        spark_text = (
            "Decisions\n- ship the panel\n\n"
            "In flight\n- 1 panel work\n\n"
            "Owners\n- rowan: panel work\n\n"
            "Blocked and why\n- nothing blocked\n\n"
            "Watch items\n- none\n" + "word " * 300)
        client = self._FakeClient(text=spark_text)
        snap = {"messages": [{"nick": "pax", "text": "DECISION: ship"}],
                "jobs": []}
        text = brief.compose_brief(snap, kind="morning", client=client)
        self.assertLessEqual(len(text.split()), 220)
        for section in ("Decisions", "In flight", "Owners",
                        "Blocked and why"):
            self.assertIn(section, text)

    def test_spark_failure_falls_back_to_template(self):
        client = self._FakeClient(error=RuntimeError("spark down"))
        snap = {"messages": [{"nick": "pax", "text": "DECISION: ship"}],
                "jobs": []}
        text = brief.compose_brief(snap, kind="morning", client=client)
        self.assertTrue(text.startswith("TEMPLATE"))

    def test_no_client_falls_back_and_stays_within_budget(self):
        jobs = [{"id": str(i), "title": "busy job with a long title here",
                 "status": "claimed", "claim": "pax", "claimed_at": 1000}
                for i in range(20)]
        snap = {"messages": [], "jobs": jobs, "alerts": []}
        text = brief.compose_brief(snap, kind="morning", client=None)
        self.assertTrue(text.startswith("TEMPLATE"))
        self.assertLessEqual(len(text.split()), 220)


class StoreTest(unittest.TestCase):
    def setUp(self):
        sys.path.insert(0, "tests")
        from fake_redis import FakeUpstash
        import relay_common as rc
        self.fake = FakeUpstash()
        self._old_get = rc.api_get
        self._old_post = rc.api_post
        rc.api_get = self.fake.api_get
        rc.api_post = self.fake.api_post

    def tearDown(self):
        import relay_common as rc
        rc.api_get = self._old_get
        rc.api_post = self._old_post

    def _record(self, ts=1793000000):
        return {
            "room": "build",
            "generated_at": ts,
            "kind": "morning",
            "sections": {name: [] for name in brief.BRIEF_SECTIONS},
            "source_window": "last 24 hours",
            "model": "template",
            "spend_id": None,
        }

    def test_store_and_retrieve_by_id(self):
        record = self._record()
        key = brief.store_brief("build", record)
        self.assertEqual(key, "muse-bus:intel:brief:build:1793000000")
        self.assertEqual(brief.get_brief("build", 1793000000), record)

    def test_list_shows_kind_and_generated_at(self):
        brief.store_brief("build", self._record(1793000000))
        brief.store_brief("build", self._record(1793000100))
        entries = brief.list_briefs("build")
        self.assertEqual([(e["ts"], e["kind"], e["generated_at"])
                          for e in entries],
                         [(1793000000, "morning", 1793000000),
                          (1793000100, "morning", 1793000100)])

    def test_invalid_record_is_not_stored(self):
        record = self._record()
        record["kind"] = "evening"
        with self.assertRaises(ValueError):
            brief.store_brief("build", record)
        self.assertEqual(brief.list_briefs("build"), [])


class RegenerationGuardTest(unittest.TestCase):
    """BRF-028: same room + window inside 5 min returns the stored
    brief, with no new Spark call and no new spend ledger entry."""

    def setUp(self):
        sys.path.insert(0, "tests")
        from fake_redis import FakeUpstash
        import relay_common as rc
        self.fake = FakeUpstash()
        self._old_get = rc.api_get
        self._old_post = rc.api_post
        self._old_push = rc.bus_push
        rc.api_get = self.fake.api_get
        rc.api_post = self.fake.api_post
        rc.bus_push = self.fake.bus_push

    def tearDown(self):
        import relay_common as rc
        rc.api_get = self._old_get
        rc.api_post = self._old_post
        rc.bus_push = self._old_push

    class _CountingClient:
        """Fake Spark client that also writes one spend entry per
        call, the way the real Spark client records spend."""

        def __init__(self):
            self.calls = 0

        def complete(self, prompt, system=None, lane_feature=None):
            from intel import store
            self.calls += 1
            store.record_spend({"ts": 1793000000, "lane_feature": "brief",
                                "tokens_in": None, "tokens_out": None,
                                "est_cost": None, "usage": "unreported"})
            return ("Decisions\n- ship the panel\n\nIn flight\n- none\n\n"
                    "Owners\n- none\n\nBlocked and why\n- none\n\n"
                    "Watch items\n- none\n")

    def _snapshot(self):
        return {"messages": [{"nick": "pax",
                              "text": "DECISION: ship the panel"}],
                "jobs": []}

    def test_second_call_inside_5min_returns_same_id_no_new_call(self):
        from intel import store
        client = self._CountingClient()
        text1, record1 = brief.generate_brief(
            self._snapshot(), "build", kind="ondemand",
            now=1793000000, client=client)
        self.assertEqual(client.calls, 1)
        self.assertEqual(len(store.spend_entries()), 1)
        text2, record2 = brief.generate_brief(
            self._snapshot(), "build", kind="ondemand",
            now=1793000100, client=client)
        self.assertEqual(record2["generated_at"],
                         record1["generated_at"])
        self.assertEqual(text2, text1)
        self.assertEqual(client.calls, 1)
        self.assertEqual(len(store.spend_entries()), 1)
        self.assertEqual(len(brief.list_briefs("build")), 1)

    def test_call_after_5min_generates_a_fresh_brief(self):
        client = self._CountingClient()
        _text1, record1 = brief.generate_brief(
            self._snapshot(), "build", kind="ondemand",
            now=1793000000, client=client)
        _text2, record2 = brief.generate_brief(
            self._snapshot(), "build", kind="ondemand",
            now=1793000301, client=client)
        self.assertNotEqual(record2["generated_at"],
                            record1["generated_at"])
        self.assertEqual(client.calls, 2)
        self.assertEqual(len(brief.list_briefs("build")), 2)

    def test_different_window_is_not_a_guard_hit(self):
        client = self._CountingClient()
        _text1, record1 = brief.generate_brief(
            self._snapshot(), "build", kind="ondemand",
            now=1793000000, client=client)
        _text2, record2 = brief.generate_brief(
            self._snapshot(), "build", kind="ondemand", since="2h",
            now=1793000100, client=client)
        self.assertNotEqual(record2["generated_at"],
                            record1["generated_at"])
        self.assertEqual(client.calls, 2)

    def test_old_record_without_text_renders_from_sections(self):
        record = {
            "room": "build",
            "generated_at": 1793000000,
            "kind": "ondemand",
            "sections": {name: [] for name in brief.BRIEF_SECTIONS},
            "source_window": {"max_messages": 500, "max_hours": 24,
                              "messages_kept": 1, "messages_dropped": 0},
            "model": "template",
            "spend_id": None,
        }
        record["sections"]["Decisions"] = ["decision: ship the panel"]
        brief.store_brief("build", record)
        client = self._CountingClient()
        text, found = brief.generate_brief(
            self._snapshot(), "build", kind="ondemand",
            now=1793000100, client=client)
        self.assertEqual(found["generated_at"], 1793000000)
        self.assertEqual(client.calls, 0)
        self.assertIn("ship the panel", text)

    def test_no_stored_brief_means_no_guard_hit(self):
        self.assertIsNone(brief.find_recent_brief(
            "build", "ondemand",
            {"max_messages": 500, "max_hours": 24,
             "messages_kept": 1, "messages_dropped": 0},
            now=1793000000))


class MorningScheduleTest(unittest.TestCase):
    def test_next_run_is_same_day_before_8am_et(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        # 2026-10-26 07:00 ET
        now = int(datetime(2026, 10, 26, 7, 0,
                           tzinfo=ZoneInfo("America/New_York"))
                  .timestamp())
        run = brief.next_morning_run(now)
        run_dt = datetime.fromtimestamp(run, tz=ZoneInfo("America/New_York"))
        self.assertEqual((run_dt.day, run_dt.hour), (26, 8))

    def test_next_run_is_next_day_after_8am_et(self):
        from datetime import datetime
        from zoneinfo import ZoneInfo
        now = int(datetime(2026, 10, 26, 9, 0,
                           tzinfo=ZoneInfo("America/New_York"))
                  .timestamp())
        run = brief.next_morning_run(now)
        run_dt = datetime.fromtimestamp(run, tz=ZoneInfo("America/New_York"))
        self.assertEqual((run_dt.day, run_dt.hour), (27, 8))

    def test_dry_run_at_fake_clock_produces_brief_without_storing(self):
        snap = {"messages": [{"nick": "pax", "text": "DECISION: ship"}],
                "jobs": []}
        text, record = brief.generate_morning_brief(
            snap, "build", now=1793000000, dry_run=True)
        self.assertIn("Decisions", text)
        self.assertEqual(record["generated_at"], 1793000000)
        self.assertEqual(record["kind"], "morning")
        self.assertEqual(brief.validate_brief_record(record), [])


    def test_morning_brief_today_runs_now_not_tomorrow(self):
        import time as _time
        snap = {"messages": [{"nick": "pax", "text": "DECISION: ship"}],
                "jobs": []}
        before = int(_time.time())
        text, record = brief.morning_brief_today(snap, "build",
                                                 dry_run=True)
        after = int(_time.time())
        self.assertTrue(before <= record["generated_at"] <= after)
        self.assertIn("Decisions", text)


class ParseSinceTest(unittest.TestCase):
    def test_hours_minutes_days(self):
        self.assertEqual(brief.parse_since("2h"), 2.0)
        self.assertEqual(brief.parse_since("30m"), 0.5)
        self.assertEqual(brief.parse_since("7d"), 168.0)
        self.assertEqual(brief.parse_since("1h30m"), 1.5)
        self.assertEqual(brief.parse_since(3), 3.0)

    def test_invalid_values_raise(self):
        for bad in ["yesterday", "0h", "", "2x", "h", "-2h"]:
            with self.assertRaises(ValueError, msg=bad):
                brief.parse_since(bad)


class SinceWindowTest(unittest.TestCase):
    def _snapshot(self):
        return {"messages": [
            {"nick": "pax", "text": "DECISION: old call from hours ago",
             "ts": 1000},
            {"nick": "pax", "text": "DECISION: recent call in window",
             "ts": 99000},
        ], "jobs": []}

    def test_since_2h_brief_excludes_old_decision_everywhere(self):
        text, record = brief.generate_brief(
            self._snapshot(), "build", kind="ondemand", since="2h",
            now=100000, dry_run=True)
        self.assertIn("recent call in window", text)
        self.assertNotIn("old call from hours ago", text)
        self.assertIn("last 2 hours", text)
        self.assertEqual(record["kind"], "ondemand")
        self.assertEqual(record["source_window"]["max_hours"], 2.0)
        decisions = record["sections"]["Decisions"]
        self.assertEqual(len(decisions), 1)
        self.assertIn("recent call in window", decisions[0])

    def test_since_on_morning_brief_scopes_the_same_way(self):
        text, record = brief.generate_brief(
            self._snapshot(), "build", kind="morning", since="2h",
            now=100000, dry_run=True)
        self.assertNotIn("old call from hours ago", text)
        self.assertEqual(record["kind"], "morning")
        self.assertEqual(record["source_window"]["max_hours"], 2.0)

    def test_double_cap_keeps_the_true_drop_count(self):
        messages = [{"nick": "pax", "text": f"message {i}",
                     "ts": 2000 + i} for i in range(600)]
        once = brief.cap_snapshot_window(
            {"messages": messages}, max_messages=500, max_hours=None,
            now=3000)
        twice = brief.cap_snapshot_window(
            once, max_messages=500, max_hours=None, now=3000)
        self.assertEqual(
            twice["source_window"]["messages_dropped"], 100)
        self.assertEqual(twice["source_window"]["messages_kept"], 500)


class OndemandCliTest(unittest.TestCase):
    def test_since_2h_run_on_fixture_produces_window_scoped_brief(self):
        import json
        import subprocess
        import sys as _sys
        import tempfile
        fixture = {"messages": [
            {"nick": "pax", "text": "DECISION: old call from hours ago",
             "ts": 1000},
            {"nick": "pax", "text": "DECISION: recent call in window",
             "ts": 99000},
        ], "jobs": []}
        with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False) as handle:
            json.dump(fixture, handle)
            path = handle.name
        proc = subprocess.run(
            [_sys.executable, "intel.py", "brief", "--ondemand",
             "--room", "build", "--since", "2h", "--snapshot", path,
             "--now", "100000", "--dry-run"],
            capture_output=True, text=True, timeout=60)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("recent call in window", proc.stdout)
        self.assertNotIn("old call from hours ago", proc.stdout)
        self.assertIn("last 2 hours", proc.stdout)

    def test_bad_since_is_a_cli_error_not_a_wrong_window(self):
        import json
        import subprocess
        import sys as _sys
        import tempfile
        with tempfile.NamedTemporaryFile(
                "w", suffix=".json", delete=False) as handle:
            json.dump({"messages": [], "jobs": []}, handle)
            path = handle.name
        proc = subprocess.run(
            [_sys.executable, "intel.py", "brief", "--ondemand",
             "--room", "build", "--since", "yesterday",
             "--snapshot", path, "--dry-run"],
            capture_output=True, text=True, timeout=60)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("invalid --since", proc.stderr)


class FailureCopyTest(unittest.TestCase):
    def test_constants_cover_all_three_cases_as_one_liners(self):
        self.assertEqual(set(brief.BRIEF_FAILURE_COPY),
                         {"unavailable", "spark_down", "no_data"})
        for kind, line in brief.BRIEF_FAILURE_COPY.items():
            self.assertIsInstance(line, str)
            self.assertTrue(line.strip(), kind)
            self.assertNotIn("\n", line, kind)

    def test_failure_line_returns_each_copy_verbatim(self):
        for kind, line in brief.BRIEF_FAILURE_COPY.items():
            self.assertEqual(brief.brief_failure_line(kind), line)

    def test_unknown_failure_kind_fails_loudly(self):
        with self.assertRaises(ValueError):
            brief.brief_failure_line("mystery")

    def test_spark_down_client_returns_spark_down_line(self):
        client = ComposerTest._FakeClient(
            error=RuntimeError("spark down"))
        snap = {"messages": [{"nick": "pax", "text": "DECISION: ship"}],
                "jobs": []}
        text = brief.compose_spark_brief(snap, kind="morning",
                                         client=client)
        self.assertEqual(text, brief.brief_failure_line("spark_down"))
        self.assertNotIn("TEMPLATE", text)

    def test_no_client_returns_spark_down_line(self):
        text = brief.compose_spark_brief({"messages": [], "jobs": []},
                                         kind="morning", client=None)
        self.assertEqual(text, brief.brief_failure_line("spark_down"))

    def test_empty_spark_reply_returns_spark_down_line(self):
        client = ComposerTest._FakeClient(text="")
        text = brief.compose_spark_brief({"messages": [], "jobs": []},
                                         kind="morning", client=client)
        self.assertEqual(text, brief.brief_failure_line("spark_down"))

    def test_spark_success_returns_brief_not_failure_line(self):
        client = ComposerTest._FakeClient(
            text="Decisions\n- ship the panel\n")
        text = brief.compose_spark_brief({"messages": [], "jobs": []},
                                         kind="morning", client=client)
        self.assertIn("ship the panel", text)
        for line in brief.BRIEF_FAILURE_COPY.values():
            self.assertNotEqual(text, line)


class CliFailureCopyTest(unittest.TestCase):
    """BRF-026 CLI surfaces, run in-process with the store reads
    mocked: the subprocess CLI tests cannot cover --show/--list
    without a live Redis surface, so these patch the brief
    module's reads and call intel.py main() directly."""

    def _load_cli(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "intel_cli", "intel.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def _run(self, cli, argv):
        import contextlib
        import io
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), \
                contextlib.redirect_stderr(err):
            code = cli.main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_show_missing_brief_prints_unavailable_line(self):
        from unittest import mock
        cli = self._load_cli()
        with mock.patch.object(brief, "get_brief",
                               return_value=None):
            code, _out, err = self._run(
                cli, ["brief", "--show", "--room", "build",
                      "--ts", "1793000000"])
        self.assertEqual(code, 1)
        self.assertIn(brief.brief_failure_line("unavailable"), err)

    def test_list_empty_room_prints_no_data_line(self):
        from unittest import mock
        cli = self._load_cli()
        with mock.patch.object(brief, "list_briefs",
                               return_value=[]):
            code, out, _err = self._run(
                cli, ["brief", "--list", "--room", "build"])
        self.assertEqual(code, 0)
        self.assertIn(brief.brief_failure_line("no_data"), out)


class WatchItemsTest(unittest.TestCase):
    def test_stall_fixture_alert_id_appears_in_brief(self):
        snap = {"messages": [], "jobs": [],
                "alerts": [{"id": "WD-STALL-3",
                            "summary": "job 3 stalled, no progress 30m"},
                           {"id": "", "summary": "no id, skipped"}]}
        items = brief.extract_watch_items(snap)
        self.assertEqual(items, [{"id": "WD-STALL-3",
                                  "summary": "job 3 stalled, no progress 30m"}])
        text = brief.compose_template_brief(snap)
        self.assertIn("WD-STALL-3", text)
        self.assertIn("job 3 stalled", text)


class OnjoinOfferTest(unittest.TestCase):
    """BRF-029: a present nick with no prior message gets an
    offer record only — no brief text, no store write, no post.
    Pure-function tests: the offer functions touch no Redis,
    no network, and no Spark, so these tests assert that shape
    directly (no brief id exists, nothing is generated)."""

    def test_new_nick_yields_one_offer_record(self):
        snapshot = {
            "messages": [
                {"nick": "pax", "text": "DECISION: ship the panel"},
                "milo: working on the watchdog",
            ],
            "presence": ["pax", "milo", "rowan"],
        }
        offers = brief.offer_onjoin_brief(snapshot, "build",
                                          now=1793000000)
        self.assertEqual(offers, [{
            "room": "build",
            "nick": "rowan",
            "kind": "onjoin",
            "status": "offered",
            "offered_at": 1793000000,
            "brief_generated": False,
            "brief_id": None,
        }])

    def test_nick_with_a_message_gets_no_offer(self):
        snapshot = {
            "messages": [{"nick": "rowan", "text": "hello"}],
            "presence": ["rowan"],
        }
        self.assertEqual(brief.detect_new_nicks(snapshot), [])
        self.assertEqual(
            brief.offer_onjoin_brief(snapshot, "build"), [])

    def test_bus_string_message_counts_as_prior_presence(self):
        snapshot = {
            "messages": ["rowan: just joined the room"],
            "presence": ["rowan", "buffy"],
        }
        self.assertEqual(brief.detect_new_nicks(snapshot),
                         ["buffy"])

    def test_claim_or_caps_alone_do_not_count_as_presence(self):
        snapshot = {
            "messages": [],
            "jobs": [{"id": "1", "title": "panel", "status": "claimed",
                      "claim": "rowan"}],
            "caps": {"rowan": {"caps": "build"}},
            "presence": ["rowan"],
        }
        self.assertEqual(brief.detect_new_nicks(snapshot),
                         ["rowan"])

    def test_no_presence_or_messages_means_no_offers(self):
        self.assertEqual(brief.detect_new_nicks({}), [])
        self.assertEqual(brief.detect_new_nicks(None), [])
        self.assertEqual(
            brief.offer_onjoin_brief({}, "build"), [])
        snapshot = {"messages": [{"nick": "pax", "text": "hi"}],
                    "presence": ["pax", "pax", ""]}
        self.assertEqual(brief.detect_new_nicks(snapshot), [])


class ReadmeBriefingSectionTest(unittest.TestCase):
    """BRF-030: intel/README.md carries the briefing engine section.

    A cold reader must be able to run a brief from that section
    alone, so the section's presence is guarded here: inputs,
    prompts, budgets, fallback, and the eval pointer must all be
    named, plus the exact CLI commands the runbook documents.
    The cold-reader confirmation by Buffy (the acceptance check)
    is still owed — this test guards the text, not her verdict.
    """

    def _readme(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                             "intel", "README.md")
        with open(path) as handle:
            return handle.read()

    def test_briefing_engine_section_names_all_parts(self):
        text = self._readme()
        self.assertIn("## Briefing engine", text)
        for heading in ("### Inputs", "### Prompts", "### Budgets",
                        "### Fallback and failure copy",
                        "### Running it", "### Eval pointer"):
            self.assertIn(heading, text)

    def test_runbook_commands_are_documented(self):
        text = self._readme()
        self.assertIn("brief --morning --room", text)
        self.assertIn("brief --ondemand --room", text)
        self.assertIn("brief --list --room", text)
        self.assertIn("brief --show --room", text)
        self.assertIn("220", text)
        self.assertIn("TEMPLATE", text)
        self.assertIn("brief_rubric.md", text)


class PromptsExplainerTest(unittest.TestCase):
    """DOC-011: intel/prompts/README.md explains the prompts."""

    def _explainer(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                             "intel", "prompts", "README.md")
        with open(path) as handle:
            return handle.read()

    def test_explainer_names_all_brief_prompts_and_budgets(self):
        text = self._explainer()
        for name in ("brief_morning.md", "brief_onjoin.md",
                     "brief_ondemand.md", "dispatch.md"):
            self.assertIn(name, text)
        for budget in ("220", "150", "300"):
            self.assertIn(budget, text)

    def test_explainer_states_brief_v2_and_the_wiring_gap(self):
        # BRF-019 re-pointed this test: brief v2 files now exist,
        # so the explainer must name them, and the wiring gap
        # (prompt files not wired to the composer) still stands.
        text = self._explainer()
        self.assertIn("brief_morning_v2.md", text)
        self.assertIn("brief_onjoin_v2.md", text)
        self.assertIn("not wired", text.lower())


class BriefGalleryTest(unittest.TestCase):
    # DOC-014: the gallery holds three real generated briefs
    # (quiet, busy, stall), each with a one-line annotation, and
    # each brief in the gallery is the template composer's output,
    # not hand-typed prose. The gallery test regenerates the busy
    # brief from its snapshot and checks the gallery carries it.
    def _gallery(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "docs", "briefs-gallery.md")
        with open(path) as handle:
            return handle.read()

    def test_gallery_has_three_template_briefs_with_annotations(self):
        text = self._gallery()
        self.assertGreaterEqual(text.count("TEMPLATE"), 3)
        for heading in ("Quiet", "Busy", "Stall"):
            self.assertIn(heading, text)
        for annotation in ("not an error",
                           "one page",
                           "not a status dump"):
            self.assertIn(annotation, text)

    def test_gallery_busy_brief_matches_regenerated_output(self):
        snapshot = {
            "source_window": "2026-10-26 08:00 ET onward, "
                             "last 24 hours",
            "messages": [
                {"nick": "pax",
                 "text": "DECISION: ship the brief panel first"},
                {"nick": "del",
                 "text": "DECISION: freeze the demo fixture at noon"},
                {"nick": "milo",
                 "text": "DONE: watchdog loop passes its checks"},
            ],
            "jobs": [
                {"id": "2", "title": "brief panel", "status": "claimed",
                 "claim": "rowan", "claimed_at": 1000},
                {"id": "3", "title": "dispatch poster",
                 "status": "claimed", "claim": "pax",
                 "claimed_at": 1000},
                {"id": "7", "title": "spark client", "status": "blocked",
                 "note": "waiting on the real Spark endpoint"},
            ],
            "alerts": [{"id": "ALERT-1", "summary": "stall on job 2"}],
        }
        regenerated = brief.compose_template_brief(snapshot)
        gallery = self._gallery()
        for line in regenerated.strip().splitlines():
            if line.strip():
                self.assertIn(line, gallery)

    def test_gallery_states_its_template_and_fixture_limits(self):
        text = self._gallery()
        self.assertIn("TEMPLATE briefs, not", text)
        self.assertIn("hand-written", text)


class BootBriefSpecTest(unittest.TestCase):
    # OS-048: the boot brief spec sits beside the brief prompts,
    # states the boot brief is the morning format (not a new
    # format) with its three carried-over inputs mapped to the
    # morning sections, names the later boot tasks without doing
    # them, and carries a hand-checked template example that the
    # test regenerates from its fixture snapshot.
    def _spec(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "brief_boot.md")
        with open(path) as handle:
            return handle.read()

    def _snapshot(self):
        return {
            "source_window": "boot window: previous shutdown "
                             "2026-10-26 22:00 ET to boot "
                             "2026-10-27 02:00 ET, last 500 messages "
                             "or last 24 hours, whichever is smaller",
            "messages": [
                {"nick": "pax",
                 "text": "DECISION: freeze the demo fixture at noon"},
                {"nick": "milo",
                 "text": "DONE: watchdog boot check passes"},
                {"nick": "del",
                 "text": "DECISION: carry the open jobs into "
                         "the morning"},
            ],
            "jobs": [
                {"id": "5", "title": "brief panel", "status": "claimed",
                 "claim": "rowan", "claimed_at": 1000},
                {"id": "6", "title": "dispatch poster", "status": "open"},
                {"id": "7", "title": "watchdog loop", "status": "blocked",
                 "note": "needs the stall fixture from Buffy"},
            ],
            "alerts": [{"id": "ALERT-BOOT-1",
                        "summary": "watchdog saw a slow boot check "
                                   "during boot"}],
        }

    def test_spec_says_morning_format_not_new_format(self):
        text = self._spec()
        self.assertIn("NOT a new", text)
        self.assertIn("morning brief format", text)
        for section in ("Decisions", "In flight", "Owners",
                        "Blocked and why", "Watch items"):
            self.assertIn(section, text)

    def test_spec_maps_all_three_carried_over_inputs(self):
        text = self._spec()
        self.assertIn("Overnight decisions", text)
        self.assertIn("Jobs in flight at shutdown", text)
        self.assertIn("watchdog saw during boot", text)

    def test_spec_names_later_boot_tasks_without_doing_them(self):
        text = self._spec()
        for task in ("OS-049", "OS-050", "OS-051", "OS-052",
                     "OS-062", "OS-079", "OS-127"):
            self.assertIn(task, text)

    def test_example_matches_regenerated_template_brief(self):
        regenerated = brief.compose_template_brief(self._snapshot())
        spec = self._spec()
        for line in regenerated.strip().splitlines():
            if line.strip():
                self.assertIn(line, spec)
        self.assertLessEqual(len(regenerated.split()), 220)


class ColdStartHonestyTest(unittest.TestCase):
    # OS-050: the boot brief states its data window and never
    # implies history the machine does not have. An empty-history
    # fixture produces a brief that says the window is empty;
    # a brief with content but no stated window keeps the plain
    # "not stated" line and invents no shutdown story.
    def _spec_and_rubric(self):
        import os
        base = os.path.join(os.path.dirname(__file__), "..")
        with open(os.path.join(base, "intel", "prompts",
                                "brief_boot.md")) as handle:
            spec = handle.read()
        with open(os.path.join(base, "intel", "evals",
                                "brief_rubric.md")) as handle:
            rubric = handle.read()
        return spec, rubric

    def test_rule_is_in_prompt_and_rubric(self):
        spec, rubric = self._spec_and_rubric()
        self.assertIn("Cold-start honesty rule", spec)
        self.assertIn("Window: empty", spec)
        self.assertIn("OS-050 cold-start honesty", rubric)

    def test_empty_history_brief_says_window_is_empty(self):
        for snapshot in ({}, {"messages": [], "jobs": [],
                              "alerts": []}):
            text = brief.compose_template_brief(snapshot)
            self.assertIn("Window: empty", text)
            self.assertIn("no activity yet", text)
            for title in ["brief panel", "dispatch poster",
                          "watchdog loop", "spark client"]:
                self.assertNotIn(title, text)

    def test_capped_window_that_kept_nothing_says_window_is_empty(self):
        snapshot = {
            "source_window": {"max_messages": 500, "max_hours": 24,
                              "messages_kept": 0, "messages_dropped": 3},
            "messages": [], "jobs": [], "alerts": [],
        }
        text = brief.compose_template_brief(snapshot)
        self.assertIn("The window is empty.", text)
        self.assertIn("no activity yet", text)

    def test_content_without_window_invents_no_shutdown_story(self):
        snapshot = {"messages": [
            {"nick": "pax", "text": "DECISION: ship the brief panel"},
        ]}
        text = brief.compose_template_brief(snapshot)
        self.assertIn("Window: not stated in this snapshot", text)
        self.assertNotIn("shutdown", text.lower())
        self.assertNotIn("carried over", text.lower())


class PreviousSessionDigestTest(unittest.TestCase):
    # OS-051: the boot brief opens with a one-line digest of
    # the previous session — last brief time, jobs completed,
    # open threads — derived from stored state, and says
    # nothing about a previous session when there is no record.
    def _record(self):
        return {"last_brief_at": "2026-10-26 22:00 ET",
                "jobs_completed": ["brief panel", "dispatch poster"],
                "open_threads": ["watchdog loop"]}

    def _snapshot(self):
        return {
            "source_window": "boot window: previous shutdown "
                             "2026-10-26 22:00 ET to boot "
                             "2026-10-27 02:00 ET",
            "messages": [
                {"nick": "pax",
                 "text": "DECISION: freeze the demo fixture at noon"},
            ],
            "jobs": [
                {"id": "5", "title": "brief panel", "status": "claimed",
                 "claim": "rowan"},
                {"id": "7", "title": "watchdog loop", "status": "blocked",
                 "note": "needs the stall fixture from Buffy"},
            ],
            "previous_session": self._record(),
        }

    def test_digest_line_is_one_line_with_all_three_parts(self):
        line = brief.previous_session_digest(self._record())
        self.assertEqual(
            line,
            "Previous session: last brief 2026-10-26 22:00 ET, "
            "2 jobs completed (brief panel; dispatch poster), "
            "1 open thread (watchdog loop)")
        self.assertNotIn("\n", line)

    def test_empty_lists_count_zero_with_no_parentheses(self):
        line = brief.previous_session_digest(
            {"last_brief_at": "2026-10-26 22:00 ET",
             "jobs_completed": [], "open_threads": []})
        self.assertEqual(
            line,
            "Previous session: last brief 2026-10-26 22:00 ET, "
            "0 jobs completed, 0 open threads")

    def test_no_record_or_no_time_means_no_digest(self):
        self.assertIsNone(brief.previous_session_digest(None))
        self.assertIsNone(brief.previous_session_digest({}))
        self.assertIsNone(brief.previous_session_digest(
            {"jobs_completed": ["brief panel"]}))

    def test_boot_brief_opens_with_digest_after_window_line(self):
        text = brief.compose_template_brief(self._snapshot(), boot=True)
        lines = text.splitlines()
        self.assertEqual(lines[0], "TEMPLATE")
        self.assertTrue(lines[1].startswith("Window:"))
        self.assertEqual(lines[2],
                         brief.previous_session_digest(self._record()))

    def test_non_boot_brief_never_carries_digest(self):
        text = brief.compose_template_brief(self._snapshot())
        self.assertNotIn("Previous session", text)

    def test_boot_brief_without_record_says_nothing_about_it(self):
        snapshot = self._snapshot()
        del snapshot["previous_session"]
        text = brief.compose_template_brief(snapshot, boot=True)
        self.assertNotIn("Previous session", text)
        self.assertNotIn("last time", text.lower())

    def test_empty_boot_window_still_carries_digest(self):
        snapshot = {"previous_session": self._record()}
        text = brief.compose_template_brief(snapshot, boot=True)
        self.assertIn("Window: empty", text)
        self.assertIn("no activity yet", text)
        self.assertIn("Previous session: last brief 2026-10-26 22:00 ET",
                      text)

    def test_build_from_stored_brief_and_shutdown_jobs(self):
        last_brief = {"room": "build", "generated_at": 1793000000,
                      "kind": "morning"}
        shutdown_jobs = [
            {"title": "brief panel", "status": "done"},
            {"title": "dispatch poster", "status": "done"},
            {"title": "watchdog loop", "status": "claimed"},
            {"title": "spark client", "status": "blocked"},
        ]
        record = brief.build_previous_session(last_brief, shutdown_jobs)
        self.assertEqual(record["last_brief_at"], "2026-10-26 03:33 ET")
        self.assertEqual(record["jobs_completed"],
                         ["brief panel", "dispatch poster"])
        # Blocked jobs are neither completed nor open threads.
        self.assertEqual(record["open_threads"], ["watchdog loop"])
        self.assertIsNone(brief.build_previous_session({}, shutdown_jobs))
        self.assertIsNone(brief.build_previous_session(None, shutdown_jobs))


class PreviousSessionRebootTest(unittest.TestCase):
    # OS-051 acceptance: the digest line is present and correct
    # across a reboot. The pre-reboot brief is really stored
    # (FakeUpstash, StoreTest pattern); the post-reboot boot
    # brief derives its previous-session record from that stored
    # brief plus the shutdown job list, and a second boot over
    # the same record yields the identical digest line.
    def setUp(self):
        sys.path.insert(0, "tests")
        from fake_redis import FakeUpstash
        import relay_common as rc
        self.fake = FakeUpstash()
        self._old_get = rc.api_get
        self._old_post = rc.api_post
        rc.api_get = self.fake.api_get
        rc.api_post = self.fake.api_post

    def tearDown(self):
        import relay_common as rc
        rc.api_get = self._old_get
        rc.api_post = self._old_post

    def test_digest_correct_across_reboot(self):
        record = {
            "room": "build",
            "generated_at": 1793000000,
            "kind": "morning",
            "sections": {name: [] for name in brief.BRIEF_SECTIONS},
            "source_window": "last 24 hours",
            "model": "template",
            "spend_id": None,
        }
        brief.store_brief("build", record)
        # Reboot: the stored brief is the previous session's
        # last brief; the shutdown job list is the session's
        # end state.
        last_brief = brief.get_brief("build", 1793000000)
        shutdown_jobs = [
            {"title": "brief panel", "status": "done"},
            {"title": "watchdog loop", "status": "open"},
        ]
        previous = brief.build_previous_session(last_brief, shutdown_jobs)
        snapshot = {
            "source_window": "boot window: previous shutdown "
                             "2026-10-26 22:00 ET to boot "
                             "2026-10-27 02:00 ET",
            "messages": [{"nick": "pax",
                          "text": "DECISION: resume after reboot"}],
            "jobs": [{"id": "7", "title": "watchdog loop",
                      "status": "open"}],
            "previous_session": previous,
        }
        first = brief.compose_template_brief(snapshot, boot=True)
        second = brief.compose_template_brief(snapshot, boot=True)
        expected = ("Previous session: last brief 2026-10-26 03:33 ET, "
                    "1 job completed (brief panel), "
                    "1 open thread (watchdog loop)")
        self.assertIn(expected, first)
        first_digest = [line for line in first.splitlines()
                        if line.startswith("Previous session")][0]
        second_digest = [line for line in second.splitlines()
                         if line.startswith("Previous session")][0]
        self.assertEqual(first_digest, second_digest)
        self.assertEqual(first_digest, expected)


class BootBriefEvalSetTest(unittest.TestCase):
    # OS-052: the boot brief eval set. Three seeded shutdown
    # states (clean, mid-job, post-crash), each a hand-written
    # snapshot whose previous-session record is derived with
    # build_previous_session from a stored last-brief time and a
    # shutdown job list, not typed by hand. Each generated
    # brief is a template brief (BRF-008): no Spark call runs,
    # because real Spark transport is still blocked. Each brief
    # is scored against the 8 rubric checks (BRF-015) plus the
    # OS-050 cold-start honesty check and the OS-051 digest
    # check. Acceptance is 3 of 3 briefs passing all of them;
    # a failure here is filed as a prompt fix task, not
    # hand-waved. A Spark-composed boot brief is scored
    # separately when real Spark transport lands.
    WINDOW = ("boot window: previous shutdown 2026-10-26 22:00 ET "
              "to boot 2026-10-27 02:00 ET, last 500 messages "
              "or last 24 hours, whichever is smaller")

    def _record(self, shutdown_jobs):
        # 1793066400 is 2026-10-26 22:00 ET, the previous
        # session's last brief time for all three states.
        record = brief.build_previous_session(
            {"generated_at": 1793066400}, shutdown_jobs)
        self.assertIsNotNone(record)
        return record

    def _fixtures(self):
        clean = {
            "source_window": self.WINDOW,
            "messages": [
                {"nick": "pax",
                 "text": "DECISION: freeze the demo fixture at noon"},
                {"nick": "milo",
                 "text": "DONE: watchdog boot check passes"},
            ],
            # Clean shutdown: every job done, nothing in flight,
            # nothing blocked, no alert. The boot snapshot itself
            # carries no current jobs, so every section but
            # Decisions reports nothing.
            "jobs": [],
            "alerts": [],
            "previous_session": self._record([
                {"title": "brief panel", "status": "done"},
                {"title": "dispatch poster", "status": "done"},
            ]),
        }
        mid_job = {
            "source_window": self.WINDOW,
            "messages": [
                {"nick": "pax",
                 "text": "DECISION: carry the open jobs into the morning"},
                {"nick": "milo",
                 "text": "DONE: watchdog boot check passes"},
            ],
            "jobs": [
                {"id": "5", "title": "brief panel", "status": "claimed",
                 "claim": "rowan", "claimed_at": 1000},
                {"id": "6", "title": "dispatch poster", "status": "open"},
            ],
            "alerts": [{"id": "ALERT-MID-1",
                        "summary": "watchdog saw a slow boot check "
                                   "during boot"}],
            "previous_session": self._record([
                {"title": "spark client", "status": "done"},
                {"title": "brief panel", "status": "claimed"},
            ]),
        }
        post_crash = {
            "source_window": self.WINDOW,
            "messages": [
                {"nick": "pax",
                 "text": "DECISION: restart after the crash"},
                {"nick": "milo",
                 "text": "BLOCKED: watchdog loop stopped at the crash"},
            ],
            "jobs": [
                {"id": "5", "title": "brief panel", "status": "claimed",
                 "claim": "rowan", "claimed_at": 1000},
                {"id": "7", "title": "watchdog loop", "status": "blocked",
                 "note": "needs the stall fixture from Buffy"},
            ],
            "alerts": [{"id": "ALERT-CRASH-1",
                        "summary": "watchdog saw the crash during boot"}],
            "previous_session": self._record([
                {"title": "dispatch poster", "status": "done"},
                {"title": "watchdog loop", "status": "claimed"},
            ]),
        }
        return (("clean", clean), ("mid-job", mid_job),
                ("post-crash", post_crash))

    def _section(self, text, heading):
        # The lines of one section, between its heading and the
        # next heading (or the end of the brief).
        lines = text.splitlines()
        start = lines.index(heading) + 1
        end = len(lines)
        for index in range(start, len(lines)):
            if lines[index] in brief.BRIEF_SECTIONS:
                end = index
                break
        return [line for line in lines[start:end] if line.strip()]

    def _score(self, snapshot, text):
        # Rubric check 1: all blocked named, by id, verbatim.
        blocked = brief.extract_blocked(snapshot)
        section = self._section(text, "Blocked and why")
        if blocked:
            for job in blocked:
                self.assertIn(
                    f"- {job['id']} {job['title']}: {job['reason']}",
                    section)
            self.assertEqual(len(section), len(blocked))
        else:
            self.assertEqual(section, ["Nothing blocked in this window"])
        # Rubric check 2: owners right, claimed jobs only.
        owners = brief.extract_owners(snapshot)
        section = self._section(text, "Owners")
        if owners:
            for owner in owners:
                titles = ", ".join(job["title"]
                                   for job in owner["jobs"])
                self.assertIn(f"- {owner['nick']}: {titles}", section)
            self.assertEqual(len(section), len(owners))
        else:
            self.assertEqual(section,
                             ["Nothing reported in this window"])
        # Rubric check 3: no invented facts. Every section line
        # is either a stated placeholder or carries a fact from
        # the snapshot (a decision text, a job title, a blocked
        # reason, an alert id and summary).
        placeholders = ("Nothing reported in this window",
                        "Nothing blocked in this window",
                        "Nothing to watch in this window")
        decisions = [item["text"]
                     for item in brief.extract_decisions(snapshot)]
        for line in self._section(text, "Decisions"):
            self.assertTrue(
                any(item in line for item in decisions),
                f"decision line with no source: {line}")
        in_flight = [job["title"]
                     for job in (snapshot.get("jobs") or [])
                     if job.get("status") in ("open", "claimed")]
        for line in self._section(text, "In flight"):
            self.assertTrue(
                line in placeholders
                or any(title in line for title in in_flight),
                f"in-flight line with no source: {line}")
        for line in self._section(text, "Watch items"):
            self.assertTrue(
                line in placeholders
                or any(item["id"] in line and item["summary"] in line
                       for item in brief.extract_watch_items(snapshot)),
                f"watch line with no source: {line}")
        # Rubric check 4: within the 220-word morning budget.
        self.assertLessEqual(len(text.split()), 220)
        # Rubric check 5: plain English, provisional test from
        # the rubric (no unexplained technical term in the brief).
        for term in ("daemon", "systemd", "async", "mutex",
                     "endpoint", "socket"):
            self.assertNotIn(term, text.lower())
        # Rubric check 6: window stated, with its start point.
        lines = text.splitlines()
        self.assertEqual(lines[0], "TEMPLATE")
        self.assertTrue(lines[1].startswith("Window:"))
        self.assertIn("previous shutdown 2026-10-26 22:00 ET",
                      lines[1])
        self.assertIn("boot 2026-10-27 02:00 ET", lines[1])
        # Rubric check 7: decisions real, every one from a marker.
        section = self._section(text, "Decisions")
        self.assertEqual(len(section), len(decisions))
        for line in section:
            self.assertTrue(any(item in line for item in decisions))
        # Rubric check 8: alerts linked, by id, exactly.
        alerts = brief.extract_watch_items(snapshot)
        section = self._section(text, "Watch items")
        if alerts:
            for item in alerts:
                self.assertIn(f"- {item['id']}: {item['summary']}",
                              section)
            self.assertEqual(len(section), len(alerts))
        else:
            self.assertEqual(section, ["Nothing to watch in this window"])
        # OS-050: the window bounds the brief, and the digest is
        # the only previous-session claim in it.
        self.assertEqual(text.count("Previous session"), 1)
        self.assertNotIn("last time", text.lower())
        # OS-051: the digest line opens the brief, right after
        # the window line and before Decisions, one line only.
        record = snapshot["previous_session"]
        self.assertEqual(lines[2],
                         brief.previous_session_digest(record))
        self.assertNotIn("\n", lines[2])

    def test_all_three_states_pass_the_rubric(self):
        for name, snapshot in self._fixtures():
            with self.subTest(state=name):
                text = brief.compose_template_brief(snapshot, boot=True)
                self._score(snapshot, text)

    def test_spec_names_the_eval_set(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "brief_boot.md")
        with open(path) as handle:
            spec = handle.read()
        self.assertIn("Boot brief eval set", spec)
        for state in ("clean", "mid-job", "post-crash"):
            self.assertIn(state, spec)


class RelayBriefServiceTest(unittest.TestCase):
    # OS-049: the relay-brief.service unit and the CLI boot
    # path it runs. The unit file's shape is guarded here;
    # the boot path is proven on a hand-written snapshot with
    # a fake store, including the guard bypass: a boot brief
    # is a new session's first brief, never a regeneration of
    # the previous session's brief. The 60-second timing on
    # the test image is NOT proven here (no test image in
    # this repo); the spec says so plainly.
    def setUp(self):
        sys.path.insert(0, "tests")
        from fake_redis import FakeUpstash
        import relay_common as rc
        self.fake = FakeUpstash()
        self._old_get = rc.api_get
        self._old_post = rc.api_post
        self._old_push = rc.bus_push
        rc.api_get = self.fake.api_get
        rc.api_post = self.fake.api_post
        rc.bus_push = self.fake.bus_push

    def tearDown(self):
        import relay_common as rc
        rc.api_get = self._old_get
        rc.api_post = self._old_post
        rc.bus_push = self._old_push

    def _unit_text(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "os", "services", "relay-brief.service")
        with open(path) as handle:
            return handle.read()

    def _snapshot(self):
        return {
            "source_window": "boot window: previous shutdown "
                             "2026-10-26 22:00 ET to boot "
                             "2026-10-27 02:00 ET",
            "messages": [{"nick": "pax",
                          "text": "DECISION: resume after reboot"}],
            "jobs": [{"id": "5", "title": "brief panel",
                      "status": "claimed", "claim": "rowan"}],
            "previous_session": {
                "last_brief_at": "2026-10-26 22:00 ET",
                "jobs_completed": ["brief panel"],
                "open_threads": ["watchdog loop"],
            },
        }

    def test_unit_is_oneshot_after_ready_gate(self):
        text = self._unit_text()
        self.assertIn("Type=oneshot", text)
        self.assertIn("After=relay-ready.service", text)
        self.assertIn("intel.py brief --boot", text)
        self.assertIn("User=relay", text)
        self.assertIn("WantedBy=relay.target", text)
        self.assertNotIn("Restart=on-failure", text)

    def test_boot_brief_stores_fresh_marked_brief(self):
        text, record = brief.generate_brief(
            self._snapshot(), "build", kind="morning",
            now=1793000100, boot=True)
        self.assertTrue(text.startswith("TEMPLATE"))
        self.assertIn("Previous session: last brief 2026-10-26 "
                      "22:00 ET, 1 job completed (brief panel), "
                      "1 open thread (watchdog loop)", text)
        self.assertTrue(record["boot"])
        self.assertEqual(brief.validate_brief_record(record), [])
        self.assertEqual(brief.get_brief("build", 1793000100),
                         record)

    def test_boot_brief_skips_regeneration_guard(self):
        first_text, first = brief.generate_brief(
            self._snapshot(), "build", kind="morning",
            now=1793000100, boot=True)
        second_text, second = brief.generate_brief(
            self._snapshot(), "build", kind="morning",
            now=1793000160, boot=True)
        self.assertEqual(second["generated_at"], 1793000160)
        self.assertNotEqual(second["generated_at"],
                            first["generated_at"])
        self.assertIn("Previous session: last brief", second_text)

    def test_non_boot_morning_still_uses_guard(self):
        first_text, first = brief.generate_brief(
            self._snapshot(), "build", kind="morning",
            now=1793000100)
        second_text, second = brief.generate_brief(
            self._snapshot(), "build", kind="morning",
            now=1793000160)
        self.assertEqual(second["generated_at"],
                         first["generated_at"])
        self.assertEqual(second_text, first_text)

    def test_spec_names_unit_and_its_proof_gap(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "brief_boot.md")
        with open(path) as handle:
            spec = handle.read()
        self.assertIn("OS-049", spec)
        self.assertIn("relay-brief.service", spec)
        self.assertIn("60-second", spec)
        self.assertIn("still owed", spec)


class SystemStateLinesTest(unittest.TestCase):
    # OS-062: the boot brief's drivers + tools + apps lines.
    # Three lines, in that order, from the snapshot's
    # "system_state" record, in boot briefs only. The gateway
    # line is the honesty case: a down gateway is said to be
    # down, never omitted, and unknown health is said to be
    # unknown, never guessed. NOT proven here: the lines
    # against live driver/gateway/loader state on the test
    # image — the driver contract (OS-053), the gateway
    # daemon (OS-058), and the skills loader (OS-065) have
    # not landed, so the caller that fills "system_state"
    # from live state is still owed (OS-066 integration);
    # these tests prove the rendering from a stated record,
    # the same fixture pattern as OS-048 through OS-052.
    STATE = {"drivers": ["muse-code"],
             "gateway_healthy": True,
             "skill_apps": ["briefing", "dispatch"]}

    def _snapshot(self, state=STATE, boot=True):
        snapshot = {
            "source_window": "boot window: previous shutdown "
                             "2026-10-26 22:00 ET to boot "
                             "2026-10-27 02:00 ET",
            "messages": [{"nick": "pax",
                          "text": "DECISION: resume after reboot"}],
            "jobs": [{"id": "5", "title": "brief panel",
                      "status": "claimed", "claim": "rowan"}],
        }
        if state is not None:
            snapshot["system_state"] = state
        return brief.compose_template_brief(snapshot, boot=boot)

    def test_lines_render_in_order_with_values(self):
        text = self._snapshot()
        lines = text.splitlines()
        self.assertEqual(lines[2:5], [
            "Drivers: muse-code available",
            "Tools: MCP gateway healthy",
            "Skill apps: briefing, dispatch mounted"])
        self.assertEqual(lines[5], "")
        self.assertEqual(lines[6], "Decisions")

    def test_gateway_down_is_said_not_omitted(self):
        state = dict(self.STATE, gateway_healthy=False)
        text = self._snapshot(state)
        self.assertIn("Tools: MCP gateway down", text)
        self.assertIn("cannot reach their tools", text)

    def test_missing_state_reports_not_reported(self):
        text = self._snapshot(None)
        self.assertIn("Drivers: not reported in this snapshot", text)
        self.assertIn("Tools: MCP gateway health not reported "
                      "in this snapshot", text)
        self.assertIn("Skill apps: not reported in this snapshot",
                      text)

    def test_empty_lists_report_none_not_invented(self):
        state = {"drivers": [], "gateway_healthy": True,
                 "skill_apps": []}
        text = self._snapshot(state)
        self.assertIn("Drivers: no drivers reported", text)
        self.assertIn("Skill apps: no skill apps mounted", text)

    def test_non_boot_brief_never_carries_system_lines(self):
        text = self._snapshot(boot=False)
        self.assertNotIn("Drivers:", text)
        self.assertNotIn("MCP gateway", text)
        self.assertNotIn("Skill apps:", text)

    def test_empty_boot_window_still_carries_system_lines(self):
        text = brief.compose_template_brief(
            {"system_state": self.STATE}, boot=True)
        self.assertIn("Drivers: muse-code available", text)
        self.assertIn("Tools: MCP gateway healthy", text)
        self.assertIn("Skill apps: briefing, dispatch mounted",
                      text)
        self.assertIn("no activity yet", text)

    def test_system_lines_survive_budget_trim(self):
        # Forty in-flight jobs push the untrimmed brief over
        # the 220-word morning budget, so the BRF-007 trim
        # runs; the system lines are not bullets, so the trim
        # must drop job bullets, never a system line.
        jobs = [{"id": str(index), "title": f"job {index}",
                 "status": "claimed", "claim": "rowan"}
                for index in range(40)]
        text = brief.compose_brief(
            {"source_window": "boot window",
             "messages": [{"nick": "pax",
                           "text": "DECISION: resume after reboot"}],
             "jobs": jobs,
             "system_state": self.STATE},
            kind="morning", boot=True)
        self.assertIn("Drivers: muse-code available", text)
        self.assertIn("Tools: MCP gateway healthy", text)
        self.assertIn("Skill apps: briefing, dispatch mounted",
                      text)
        self.assertLessEqual(len(text.split()), 220)

    def test_spec_names_os062_and_its_proof_gap(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "brief_boot.md")
        with open(path) as handle:
            spec = handle.read()
        self.assertIn("OS-062", spec)
        self.assertIn("Drivers:", spec)
        self.assertIn("MCP gateway", spec)
        self.assertIn("still owed", spec)


class EnvironmentLinesTest(unittest.TestCase):
    # OS-103: the launch environment lines for a boot brief.
    # Four lines, in that order, from the snapshot's
    # "environment" record, in boot briefs only, and only
    # when the snapshot carries the record. Every valued
    # line carries its age label, so a stale field is never
    # silently presented as current. NOT proven here: the
    # lines against live launch state — no caller in this
    # repo yet fills "environment" from git, the bus, the
    # job queue, or a budget config (Milo OS-085 has not
    # landed), so the budget line in practice reads not
    # reported until that config lands; these tests prove
    # the rendering from a stated record, the same fixture
    # pattern as OS-048 through OS-062.
    AS_OF = 1793093400  # 2026-10-27 05:30 ET.
    STATE = {"drivers": ["muse-code"],
             "gateway_healthy": True,
             "skill_apps": ["briefing", "dispatch"]}
    ENV = {"repo": {"branch": "main", "commit": "a6c190f",
                    "dirty": 0, "as_of": AS_OF},
           "bus": {"rooms": ["main"], "messages": 500,
                   "as_of": AS_OF},
           "jobs": [{"id": "5", "title": "brief panel",
                     "status": "claimed", "claim": "rowan"},
                    {"id": "6", "title": "dispatch poster",
                     "status": "open"}],
           "budget": {"lane": "HANA", "spent": 120, "cap": 300,
                      "as_of": AS_OF},
           "as_of": AS_OF}

    def _snapshot(self, env=ENV, boot=True):
        snapshot = {
            "source_window": "boot window: previous shutdown "
                             "2026-10-26 22:00 ET to boot "
                             "2026-10-27 02:00 ET",
            "messages": [{"nick": "pax",
                          "text": "DECISION: resume after reboot"}],
            "jobs": [{"id": "5", "title": "brief panel",
                      "status": "claimed", "claim": "rowan"}],
            "system_state": self.STATE,
        }
        if env is not None:
            snapshot["environment"] = env
        return brief.compose_template_brief(snapshot, boot=boot)

    def test_lines_render_in_order_with_values(self):
        text = self._snapshot()
        lines = text.splitlines()
        self.assertEqual(lines[5:9], [
            "Repo: main at a6c190f, clean "
            "(as of 2026-10-27 05:30 ET)",
            "Bus: 500 messages in room main "
            "(as of 2026-10-27 05:30 ET)",
            "Working now: rowan: brief panel "
            "(as of 2026-10-27 05:30 ET)",
            "Budget: HANA lane: 180 remaining of 300 cap "
            "(as of 2026-10-27 05:30 ET)"])
        self.assertEqual(lines[9], "")
        self.assertEqual(lines[10], "Decisions")

    def test_missing_fields_report_not_reported(self):
        text = self._snapshot({})
        self.assertIn("Repo state: not reported in this snapshot",
                      text)
        self.assertIn("Bus state: not reported in this snapshot",
                      text)
        self.assertIn("Working now: not reported in this snapshot",
                      text)
        self.assertIn("Budget: not reported in this snapshot", text)

    def test_no_environment_key_carries_no_lines(self):
        text = self._snapshot(None)
        self.assertNotIn("Repo:", text)
        self.assertNotIn("Bus:", text)
        self.assertNotIn("Working now:", text)
        self.assertNotIn("Budget:", text)

    def test_unknown_age_is_labelled_not_silent(self):
        env = {"repo": {"branch": "main", "commit": "a6c190f",
                        "dirty": 0},
               "bus": {"rooms": ["main"], "messages": 500},
               "jobs": [{"id": "5", "title": "brief panel",
                         "status": "claimed", "claim": "rowan"}],
               "budget": {"lane": "HANA", "spent": 120,
                          "cap": 300}}
        text = self._snapshot(env)
        self.assertIn("Repo: main at a6c190f, clean "
                      "(snapshot time not reported)", text)
        self.assertIn("Budget: HANA lane: 180 remaining of 300 cap "
                      "(snapshot time not reported)", text)
        self.assertNotIn("(as of ", text)

    def test_dirty_repo_and_no_claimed_job(self):
        env = {"repo": {"branch": "main", "commit": "a6c190f",
                        "dirty": 3, "as_of": self.AS_OF},
               "bus": {"rooms": ["main"], "messages": 500,
                       "as_of": self.AS_OF},
               "jobs": [{"id": "6", "title": "dispatch poster",
                         "status": "open"}],
               "budget": {"lane": "HANA", "remaining": 180,
                          "cap": 300, "as_of": self.AS_OF},
               "as_of": self.AS_OF}
        text = self._snapshot(env)
        self.assertIn("Repo: main at a6c190f, 3 uncommitted files "
                      "(as of 2026-10-27 05:30 ET)", text)
        self.assertIn("Working now: nobody holds a claimed job "
                      "in this snapshot "
                      "(as of 2026-10-27 05:30 ET)", text)

    def test_non_boot_brief_never_carries_environment_lines(self):
        text = self._snapshot(boot=False)
        self.assertNotIn("Repo:", text)
        self.assertNotIn("Working now:", text)
        self.assertNotIn("Budget:", text)

    def test_empty_boot_window_still_carries_environment_lines(self):
        text = brief.compose_template_brief(
            {"environment": self.ENV}, boot=True)
        self.assertIn("Repo: main at a6c190f, clean", text)
        self.assertIn("Working now: rowan: brief panel", text)
        self.assertIn("Budget: HANA lane: 180 remaining", text)
        self.assertIn("no activity yet", text)

    def test_environment_lines_survive_budget_trim(self):
        # Forty in-flight jobs push the untrimmed brief over
        # the 220-word morning budget, so the BRF-007 trim
        # runs; the environment lines are not bullets, so
        # the trim must drop job bullets, never an
        # environment line.
        jobs = [{"id": str(index), "title": f"job {index}",
                 "status": "claimed", "claim": "rowan"}
                for index in range(40)]
        text = brief.compose_brief(
            {"source_window": "boot window",
             "messages": [{"nick": "pax",
                           "text": "DECISION: resume after reboot"}],
             "jobs": jobs,
             "system_state": self.STATE,
             "environment": self.ENV},
            kind="morning", boot=True)
        self.assertIn("Repo: main at a6c190f, clean", text)
        self.assertIn("Working now: rowan: brief panel", text)
        self.assertIn("Budget: HANA lane: 180 remaining", text)
        self.assertLessEqual(len(text.split()), 220)

    def test_spec_names_os103_and_its_proof_gap(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "brief_boot.md")
        with open(path) as handle:
            spec = handle.read()
        self.assertIn("OS-103", spec)
        self.assertIn("environment", spec)
        self.assertIn("still owed", spec)


class RecoveryLineTest(unittest.TestCase):
    # OS-127: the boot brief's in-flight-jobs-recovered
    # line, reconciled against the lease sweep. One
    # line, after the environment lines and before
    # Decisions, in boot briefs only, and only when the
    # snapshot carries a recovery record — a snapshot
    # without one keeps its older exact shape, so a
    # brief never claims zero recovered without a sweep
    # record to reconcile against. NOT proven here: the
    # line against a real OS-126 plug-pull drill — the
    # lease sweep (Milo OS-129) has not landed, so no
    # caller yet fills "recovery" from a live sweep;
    # these tests prove the rendering from a stated
    # record, the same fixture pattern as OS-048
    # through OS-103.
    STATE = {"drivers": ["muse-code"],
             "gateway_healthy": True,
             "skill_apps": ["briefing", "dispatch"]}
    ENV = {"repo": {"branch": "main", "commit": "a6c190f",
                    "dirty": 0, "as_of": 1793093400},
           "bus": {"rooms": ["main"], "messages": 500,
                   "as_of": 1793093400},
           "jobs": [{"id": "5", "title": "brief panel",
                     "status": "claimed", "claim": "rowan"}],
           "budget": {"lane": "HANA", "spent": 120, "cap": 300,
                      "as_of": 1793093400},
           "as_of": 1793093400}
    RECOVERY = {"recovered": [
        {"id": "5", "title": "brief panel",
         "baton_step": "step 2"},
        {"id": "6", "title": "dispatch poster",
         "baton_step": "step 1"}],
        "sweep_count": 2}

    def _snapshot(self, recovery=RECOVERY, boot=True):
        snapshot = {
            "source_window": "boot window: previous shutdown "
                             "2026-10-26 22:00 ET to boot "
                             "2026-10-27 02:00 ET",
            "messages": [{"nick": "pax",
                          "text": "DECISION: resume after reboot"}],
            "jobs": [{"id": "5", "title": "brief panel",
                      "status": "claimed", "claim": "rowan"}],
            "system_state": self.STATE,
            "environment": self.ENV,
        }
        if recovery is not None:
            snapshot["recovery"] = recovery
        return brief.compose_template_brief(snapshot, boot=boot)

    def test_line_renders_in_order_with_values(self):
        text = self._snapshot()
        lines = text.splitlines()
        self.assertEqual(lines[9], (
            "In-flight jobs recovered at this boot: "
            "2 recovered: job 5 brief panel "
            "(resumed at step 2); job 6 dispatch poster "
            "(resumed at step 1)"))
        self.assertEqual(lines[10], "")
        self.assertEqual(lines[11], "Decisions")

    def test_clean_shutdown_reads_zero_recovered(self):
        text = self._snapshot({"recovered": [], "sweep_count": 0})
        self.assertIn("In-flight jobs recovered at this boot: "
                      "0 recovered", text)

    def test_sweep_mismatch_is_incomplete_not_a_count(self):
        recovery = dict(self.RECOVERY, sweep_count=3)
        text = self._snapshot(recovery)
        self.assertIn("recovery incomplete", text)
        self.assertIn("lease sweep reports 3 recovered", text)
        self.assertNotIn("2 recovered:", text)

    def test_corrupted_job_is_named_not_cleared(self):
        recovery = dict(self.RECOVERY,
                        corrupted=[{"id": "7",
                                    "title": "watchdog loop"}])
        text = self._snapshot(recovery)
        self.assertIn("recovery incomplete", text)
        self.assertIn("job 7 watchdog loop has a corrupted "
                      "record", text)
        self.assertNotIn("2 recovered:", text)

    def test_no_sweep_count_is_incomplete(self):
        recovery = {"recovered": self.RECOVERY["recovered"]}
        text = self._snapshot(recovery)
        self.assertIn("recovery incomplete", text)
        self.assertIn("no lease sweep count", text)

    def test_missing_baton_step_is_said_not_invented(self):
        recovery = {"recovered": [{"id": "5",
                                   "title": "brief panel"}],
                    "sweep_count": 1}
        text = self._snapshot(recovery)
        self.assertIn("job 5 brief panel (resumed at step not "
                      "reported)", text)

    def test_no_recovery_key_carries_no_line(self):
        text = self._snapshot(None)
        self.assertNotIn("recovered at this boot", text)

    def test_non_boot_brief_never_carries_recovery_line(self):
        text = self._snapshot(boot=False)
        self.assertNotIn("recovered at this boot", text)

    def test_empty_boot_window_still_carries_recovery_line(self):
        text = brief.compose_template_brief(
            {"recovery": self.RECOVERY}, boot=True)
        self.assertIn("In-flight jobs recovered at this boot: "
                      "2 recovered:", text)
        self.assertLess(text.index("recovered at this boot"),
                        text.index("no activity yet"))

    def test_recovery_line_survives_budget_trim(self):
        # Forty in-flight jobs push the untrimmed brief over
        # the 220-word morning budget, so the BRF-007 trim
        # runs; the recovery line is not a bullet, so the
        # trim must drop job bullets, never the line.
        jobs = [{"id": str(index), "title": f"job {index}",
                 "status": "claimed", "claim": "rowan"}
                for index in range(40)]
        text = brief.compose_brief(
            {"source_window": "boot window",
             "messages": [{"nick": "pax",
                           "text": "DECISION: resume after reboot"}],
             "jobs": jobs,
             "system_state": self.STATE,
             "environment": self.ENV,
             "recovery": self.RECOVERY},
            kind="morning", boot=True)
        self.assertIn("In-flight jobs recovered at this boot: "
                      "2 recovered:", text)
        self.assertLessEqual(len(text.split()), 220)

    def test_spec_names_os127_and_its_proof_gap(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "brief_boot.md")
        with open(path) as handle:
            spec = handle.read()
        self.assertIn("OS-127", spec)
        self.assertIn("recovered", spec)
        self.assertIn("still owed", spec)


class KnownLimitsTest(unittest.TestCase):
    """INT-026: the known-limits text lives in the README and in
    the submission notes, verbatim in both places."""

    def _readme_block(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "README.md")
        with open(path) as handle:
            text = handle.read()
        start = text.index("Stated plainly, so nobody reads a brief")
        end = text.index("Until then a brief lives in the store "
                         "and the CLI only.") + len(
                             "Until then a brief lives in the store "
                             "and the CLI only.")
        return text[start:end]

    def _notes_path(self):
        import os
        return os.path.join(os.path.dirname(__file__), "..",
                            "hackathon", "relay-intelligence",
                            "submission-notes.md")

    def test_limits_text_in_readme(self):
        block = self._readme_block()
        self.assertIn("DM rooms are not polled", block)
        self.assertIn("starts mid-story", block)

    def test_submission_notes_carry_same_text_verbatim(self):
        with open(self._notes_path()) as handle:
            notes = handle.read()
        block = self._readme_block()
        self.assertIn(block, notes)

    def test_submission_notes_name_int026_and_source(self):
        with open(self._notes_path()) as handle:
            notes = handle.read()
        self.assertIn("INT-026", notes)
        self.assertIn("intel/README.md", notes)
        self.assertIn("DOC-013", notes)

    def test_submission_notes_are_not_the_submission_package(self):
        with open(self._notes_path()) as handle:
            notes = handle.read()
        self.assertIn("DEM-005", notes)
        self.assertIn("has not landed", notes)


class MemoryBudgetLinesTest(unittest.TestCase):
    # OS-079: the boot brief (and the morning brief) opens
    # with settled decisions pulled from the memory
    # service, verbatim, plus one spend-vs-budget line
    # per lane. The lines render whenever the snapshot
    # carries a memory_budget record, in a boot brief
    # and in a morning brief alike, right after the
    # window line and before the digest and the
    # sections; a snapshot without the record carries
    # none, so older briefs keep their exact shape. NOT
    # proven here: the lines against a live memory
    # service or a live budget config — Milo OS-085 has
    # not landed, so no caller yet fills
    # "memory_budget" from live state; these tests prove
    # the rendering from a stated record, the same
    # fixture pattern as OS-048 through OS-127.
    RECORD = {"settled_decisions": ["Morning brief format is final"],
              "budgets": [{"lane": "HANA", "spent": 120, "cap": 300,
                           "as_of": 1793093400},
                          {"lane": "MILO", "remaining": 90, "cap": 200}],
              "as_of": 1793093400}

    def _snapshot(self, record=RECORD, boot=True):
        snapshot = {
            "source_window": "boot window: previous shutdown "
                             "2026-10-26 22:00 ET to boot "
                             "2026-10-27 02:00 ET",
            "messages": [{"nick": "pax",
                          "text": "DECISION: resume after reboot"}],
            "jobs": [{"id": "5", "title": "brief panel",
                      "status": "claimed", "claim": "rowan"}],
        }
        if record is not None:
            snapshot["memory_budget"] = record
        return brief.compose_template_brief(snapshot, boot=boot)

    def test_lines_open_the_brief_in_order_with_values(self):
        text = self._snapshot()
        lines = text.splitlines()
        self.assertEqual(lines[2], (
            "Settled decisions from memory: Morning brief "
            "format is final (as of 2026-10-27 05:30 ET)"))
        self.assertEqual(lines[3], (
            "Spend: HANA lane: 120 of 300 budget (180 "
            "remaining) (as of 2026-10-27 05:30 ET)"))
        self.assertEqual(lines[4], (
            "Spend: MILO lane: 90 remaining of 200 cap "
            "(as of 2026-10-27 05:30 ET)"))
        self.assertLess(text.index("Settled decisions"),
                        text.index("Decisions"))

    def test_memory_down_is_said_not_hidden(self):
        record = {"memory_down": True, "budgets": []}
        text = self._snapshot(record)
        self.assertIn("Settled decisions from memory: memory "
                      "service down, so no settled decisions "
                      "are shown", text)
        self.assertNotIn("Morning brief format is final", text)
        self.assertIn("Spend vs budget: not reported", text)

    def test_missing_decisions_are_not_reported_not_guessed(self):
        record = {"budgets": self.RECORD["budgets"],
                  "as_of": 1793093400}
        text = self._snapshot(record)
        self.assertIn("Settled decisions from memory: not "
                      "reported in this snapshot", text)

    def test_empty_decisions_read_none_reported(self):
        record = {"settled_decisions": [],
                  "budgets": self.RECORD["budgets"],
                  "as_of": 1793093400}
        text = self._snapshot(record)
        self.assertIn("Settled decisions from memory: none "
                      "reported", text)

    def test_unusable_budget_entry_renders_not_reported(self):
        record = {"settled_decisions": ["Morning brief format is final"],
                  "budgets": [{"lane": "HANA"}],
                  "as_of": 1793093400}
        text = self._snapshot(record)
        self.assertIn("Spend vs budget: not reported", text)
        self.assertNotIn("Spend: HANA", text)

    def test_no_record_carries_no_lines(self):
        text = self._snapshot(None)
        self.assertNotIn("Settled decisions", text)
        self.assertNotIn("Spend:", text)

    def test_morning_brief_also_opens_with_the_lines(self):
        text = self._snapshot(boot=False)
        lines = text.splitlines()
        self.assertEqual(lines[2], (
            "Settled decisions from memory: Morning brief "
            "format is final (as of 2026-10-27 05:30 ET)"))
        self.assertIn("Spend: HANA lane:", text)

    def test_empty_boot_window_still_carries_the_lines(self):
        text = brief.compose_template_brief(
            {"memory_budget": self.RECORD}, boot=True)
        self.assertIn("Settled decisions from memory: Morning "
                      "brief format is final", text)
        self.assertLess(text.index("Settled decisions"),
                        text.index("no activity yet"))

    def test_lines_survive_budget_trim(self):
        # Forty in-flight jobs push the untrimmed brief over
        # the 220-word morning budget, so the BRF-007 trim
        # runs; the memory lines are not bullets, so the
        # trim must drop job bullets, never the lines.
        jobs = [{"id": str(index), "title": f"job {index}",
                 "status": "claimed", "claim": "rowan"}
                for index in range(40)]
        text = brief.compose_brief(
            {"source_window": "boot window",
             "messages": [{"nick": "pax",
                           "text": "DECISION: resume after reboot"}],
             "jobs": jobs,
             "memory_budget": self.RECORD},
            kind="morning", boot=True)
        self.assertIn("Settled decisions from memory: Morning "
                      "brief format is final", text)
        self.assertIn("Spend: HANA lane: 120 of 300 budget",
                      text)
        self.assertLessEqual(len(text.split()), 220)

    def test_spec_names_os079_and_its_proof_gap(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "brief_boot.md")
        with open(path) as handle:
            spec = handle.read()
        self.assertIn("OS-079", spec)
        self.assertIn("memory", spec)
        self.assertIn("still owed", spec)


class OnJoinBriefScoreTest(unittest.TestCase):
    # BRF-018: the on-join brief scored against the BRF-015
    # rubric on a busy snapshot, with a cold-read verdict for
    # a newcomer who has only this brief. The snapshot is
    # hand-written, NOT Buffy's FND-023 busy fixture (not in
    # this repo yet), and the brief is the BRF-008 template
    # brief, not a Spark-composed brief — so a re-score on
    # Buffy's fixture and on a Spark brief are still owed,
    # and the cold-read verdict below is Hana's own, not an
    # independent lane member's verdict, which the task
    # acceptance asks for and is still owed.
    def _snapshot(self):
        return {
            "source_window": "2026-10-27 08:00 ET onward, "
                             "last 24 hours",
            "messages": [
                {"nick": "pax",
                 "text": "DECISION: freeze the demo fixture at noon"},
                {"nick": "milo",
                 "text": "DONE: watchdog loop passes its checks"},
                {"nick": "del",
                 "text": "DECISION: carry open jobs into the morning"},
            ],
            "jobs": [
                {"id": "2", "title": "brief panel",
                 "status": "claimed", "claim": "rowan",
                 "claimed_at": 1000},
                {"id": "3", "title": "dispatch poster",
                 "status": "claimed", "claim": "pax",
                 "claimed_at": 1000},
                {"id": "6", "title": "dashboard help text",
                 "status": "open"},
                {"id": "7", "title": "spark client",
                 "status": "blocked",
                 "note": "waiting on the real Spark endpoint"},
                {"id": "11", "title": "watchdog loop",
                 "status": "done", "note": "finished"},
            ],
            "alerts": [{"id": "ALERT-1",
                        "summary": "stall on job 2"}],
            "presence": ["pax", "milo", "rowan", "del", "sam"],
        }

    def test_onjoin_template_brief_scores_8_of_8(self):
        text = brief.compose_template_brief(self._snapshot())
        # Check 4, within budget: on-join budget is 150 words.
        self.assertLessEqual(len(text.split()), 150)
        # Check 6, window stated: the first lines state it.
        self.assertIn("Window: 2026-10-27 08:00 ET onward, "
                      "last 24 hours", text)
        # Check 7, decisions real: every decision traces to a
        # marker in the snapshot messages above.
        self.assertIn("- decision: freeze the demo fixture "
                      "at noon", text)
        self.assertIn("- done: watchdog loop passes its checks",
                      text)
        self.assertIn("- decision: carry open jobs into the "
                      "morning", text)
        # Check 2, owners right: claimed jobs only, under the
        # nick that claimed each one; the done job (id 11)
        # appears under no owner.
        self.assertIn("- rowan: brief panel", text)
        self.assertIn("- pax: dispatch poster", text)
        self.assertNotIn("- 11 ", text)
        # Check 1, all blocked named, with the reason verbatim.
        self.assertIn("- 7 spark client: waiting on the real "
                      "Spark endpoint", text)
        # Check 8, alerts linked: the one open alert, by id.
        self.assertIn("- ALERT-1: stall on job 2", text)
        # Check 3, no invented facts: the in-flight section
        # names only jobs from the snapshot, including the
        # one open job a newcomer could take.
        self.assertIn("- 6 dashboard help text (open)", text)

    def test_cold_read_can_start_but_has_no_lane_or_project(self):
        # Default kind is morning, so this still renders
        # the morning sections; the BRF-018 follow-up
        # closes the gap only for kind="onjoin" (see
        # test_intel_brief_onjoin_template.py).
        text = brief.compose_template_brief(self._snapshot())
        # Startable from this brief alone: an open job is
        # named, its status is open, the owners to ask are
        # named, and the blocked job to avoid is named.
        self.assertIn("dashboard help text (open)", text)
        self.assertIn("- rowan: brief panel", text)
        self.assertIn("- pax: dispatch poster", text)
        self.assertIn("spark client", text)
        # Gaps, pinned rather than hidden: the template brief
        # renders the morning sections, not the BRF-002
        # on-join sections, so it carries no project sentence,
        # no likely-lane line from a capability record, and
        # no "ask this nick for a first job" line. A newcomer
        # can start on the open job, but must ask an owner
        # which lane it belongs to.
        self.assertNotIn("What this crew is building", text)
        self.assertNotIn("Your likely lane", text)
        self.assertNotIn("Ask ", text)
        # The newcomer in the snapshot (sam, present with no
        # prior message) is offered an on-join brief, not
        # auto-generated one, per BRF-029.
        offered = [offer["nick"] for offer in
                   brief.offer_onjoin_brief(self._snapshot(),
                                            "build")]
        self.assertIn("sam", offered)

    def test_compose_onjoin_keeps_blocked_and_alert_in_budget(self):
        # The compose path caps the window and trims to the
        # 150-word on-join budget; on this snapshot no trim
        # is needed, so the blocked job and the alert that
        # the trim drops first must both survive. BRF-018
        # follow-up: the template now renders the four
        # BRF-002 on-join sections first, with the blocked
        # job in What is blocked, and the alert survives
        # in the additive Watch items section the INT-004
        # e2e3 loop reads from.
        text = brief.compose_brief(self._snapshot(),
                                   kind="onjoin")
        self.assertLessEqual(len(text.split()), 150)
        self.assertIn("Window: last 500 messages or last 24 "
                      "hours, 3 kept, 0 dropped", text)
        self.assertIn("What this crew is building", text)
        self.assertIn("spark client", text)
        self.assertIn("ALERT-1: stall on job 2", text)


class FederationSectionTest(unittest.TestCase):
    # OS-117: the morning brief's crew-of-crews section.
    # A two-machine fixture window names both machines'
    # completions, the cross-machine job with its state,
    # and the trust refusal, matching the room record;
    # a single-machine brief renders the section absent,
    # never empty-padded. NOT proven here: the section
    # against a live federation — the join flow (Pax
    # OS-110), trust enforcement (Milo OS-112), the
    # two-machine drill (Buffy OS-113), and the policy
    # ruling (Dale OS-115) have not landed, so no
    # caller yet fills "federation" from joined
    # machines; these tests prove the rendering from a
    # stated record, the same fixture pattern as
    # OS-048 through OS-127. This is a Phase B [B]
    # task built early as a renderer only.
    FED = {"machines": [
        {"name": "machine-a",
         "completions": ["brief panel", "dispatch poster"],
         "cross_machine_jobs": [{"id": "3",
                                 "title": "watchdog loop",
                                 "status": "claimed"}]},
        {"name": "machine-b",
         "completions": ["board grouping"],
         "cross_machine_jobs": []}],
        "trust_events": [
            {"kind": "refusal", "machine": "machine-c",
             "detail": "unsigned job refused"},
            {"kind": "join", "machine": "machine-b",
             "detail": "signed jobs accepted"}]}

    def _snapshot(self, federation=FED):
        snapshot = {
            "source_window": "last 500 messages or last "
                             "24 hours",
            "messages": [{"nick": "pax",
                          "text": "DECISION: freeze the demo "
                                  "fixture at noon"}],
            "jobs": [{"id": "5", "title": "brief panel",
                      "status": "claimed", "claim": "rowan"}],
            "alerts": [{"id": "ALERT-1",
                        "summary": "stall on job 2"}],
        }
        if federation is not None:
            snapshot["federation"] = federation
        return snapshot

    def test_two_machines_name_both_and_the_refusal(self):
        text = brief.compose_template_brief(self._snapshot())
        self.assertIn("Federation", text)
        self.assertIn("- machine-a: completed brief panel, "
                      "dispatch poster; cross-machine jobs: "
                      "job 3 watchdog loop (claimed)", text)
        self.assertIn("- machine-b: completed board "
                      "grouping", text)
        self.assertIn("- Trust: machine-c was refused: "
                      "unsigned job refused", text)
        self.assertIn("- Trust: machine-b joined the "
                      "federation: signed jobs accepted", text)
        self.assertLess(text.index("Watch items"),
                        text.index("Federation"))

    def test_single_machine_renders_no_section(self):
        single = {"machines": [{"name": "machine-a",
                                "completions": ["brief panel"],
                                "cross_machine_jobs": []}],
                  "trust_events": []}
        text = brief.compose_template_brief(
            self._snapshot(single))
        self.assertNotIn("Federation", text)
        self.assertNotIn("machine-a", text)

    def test_no_federation_key_carries_no_section(self):
        text = brief.compose_template_brief(
            self._snapshot(None))
        self.assertNotIn("Federation", text)

    def test_machine_with_no_completions_says_so(self):
        fed = {"machines": [
            {"name": "machine-a",
             "completions": ["brief panel"],
             "cross_machine_jobs": []},
            {"name": "machine-b",
             "completions": [],
             "cross_machine_jobs": []}],
            "trust_events": []}
        text = brief.compose_template_brief(
            self._snapshot(fed))
        self.assertIn("- machine-b: no completions "
                      "reported", text)

    def test_refusal_without_detail_says_reason_not_reported(self):
        fed = {"machines": self.FED["machines"],
               "trust_events": [{"kind": "refusal",
                                 "machine": "machine-c"}]}
        text = brief.compose_template_brief(
            self._snapshot(fed))
        self.assertIn("- Trust: machine-c was refused "
                      "(reason not reported)", text)

    def test_empty_window_still_carries_federation_section(self):
        text = brief.compose_template_brief(
            {"federation": self.FED})
        self.assertIn("Federation", text)
        self.assertIn("machine-a", text)
        self.assertLess(text.index("Federation"),
                        text.index("no activity yet"))

    def test_spec_names_os117_and_its_proof_gap(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "brief_boot.md")
        with open(path) as handle:
            spec = handle.read()
        self.assertIn("OS-117", spec)
        self.assertIn("federation", spec)
        self.assertIn("still owed", spec)


class MemoryDepthLinesTest(unittest.TestCase):
    # OS-092: the daily brief's long-term-memory lines.
    # A stated memory_depth record names the aged
    # decision with its original date, the due
    # commitment with its due date, and the fresh-agent
    # context verbatim, after Watch items; a down
    # memory service says so and shows nothing else;
    # missing dates read not reported, never guessed;
    # an empty record reads none reported, never
    # padded. NOT proven here: the lines against a
    # live memory service — the daily brief itself
    # (OS-075) has not landed, because the desktop
    # session (Rowan OS-071) has not landed and two
    # weeks of daily briefs have not run, and no
    # caller yet fills "memory_depth" from memory;
    # these tests prove the rendering from a stated
    # record, the same fixture pattern as OS-048
    # through OS-127. This is a Phase B [B] task
    # built early as a renderer only.
    MEM = {"aged_decisions": [
               {"decision": "freeze the demo fixture "
                            "at noon",
                "original_date": "2026-10-01"}],
           "due_commitments": [
               {"commitment": "ship the demo cut",
                "due": "2026-11-03"}],
           "fresh_context": ["the demo room is build "
                             "only, never a posting room"]}

    def _snapshot(self, memory_depth=MEM):
        snapshot = {
            "source_window": "last 500 messages or last "
                             "24 hours",
            "messages": [{"nick": "pax",
                          "text": "DECISION: freeze the demo "
                                  "fixture at noon"}],
            "jobs": [{"id": "5", "title": "brief panel",
                      "status": "claimed", "claim": "rowan"}],
            "alerts": [{"id": "ALERT-1",
                        "summary": "stall on job 2"}],
        }
        if memory_depth is not None:
            snapshot["memory_depth"] = memory_depth
        return snapshot

    def test_all_three_categories_named_verbatim(self):
        text = brief.compose_template_brief(self._snapshot())
        self.assertIn("Long-term memory", text)
        self.assertIn("Aged decision: freeze the demo "
                      "fixture at noon (from 2026-10-01)",
                      text)
        self.assertIn("Due commitment: ship the demo cut "
                      "(due 2026-11-03)", text)
        self.assertIn("Fresh-agent context: the demo room "
                      "is build only, never a posting room",
                      text)
        self.assertLess(text.index("Watch items"),
                        text.index("Long-term memory"))

    def test_no_memory_depth_key_carries_no_section(self):
        text = brief.compose_template_brief(
            self._snapshot(None))
        self.assertNotIn("Long-term memory", text)
        self.assertNotIn("Aged decision", text)
        self.assertNotIn("Due commitment", text)

    def test_memory_down_says_so_and_shows_no_items(self):
        text = brief.compose_template_brief(
            self._snapshot({"memory_down": True,
                            "aged_decisions": [
                                {"decision": "freeze the demo "
                                             "fixture at noon",
                                 "original_date":
                                     "2026-10-01"}]}))
        self.assertIn("Long-term memory: memory service "
                      "down", text)
        self.assertNotIn("Aged decision: freeze", text)

    def test_missing_dates_read_not_reported(self):
        mem = {"aged_decisions": [
                   {"decision": "freeze the demo fixture "
                                "at noon"}],
               "due_commitments": [
                   {"commitment": "ship the demo cut"}],
               "fresh_context": []}
        text = brief.compose_template_brief(
            self._snapshot(mem))
        self.assertIn("Aged decision: freeze the demo "
                      "fixture at noon (original date not "
                      "reported)", text)
        self.assertIn("Due commitment: ship the demo cut "
                      "(due date not reported)", text)

    def test_empty_record_reads_none_reported(self):
        text = brief.compose_template_brief(
            self._snapshot({}))
        self.assertIn("Aged decisions: none reported", text)
        self.assertIn("Due commitments: none reported", text)
        self.assertIn("Fresh-agent context: none reported",
                      text)

    def test_empty_window_still_carries_memory_section(self):
        text = brief.compose_template_brief(
            {"memory_depth": self.MEM})
        self.assertIn("Long-term memory", text)
        self.assertIn("Aged decision: freeze the demo "
                      "fixture at noon", text)
        self.assertLess(text.index("Long-term memory"),
                        text.index("no activity yet"))

    def test_budget_trim_keeps_memory_lines(self):
        snapshot = self._snapshot()
        snapshot["jobs"] = [{"id": str(n),
                             "title": "job work",
                             "status": "claimed",
                             "claim": "rowan"}
                            for n in range(60)]
        text = brief.compose_brief(snapshot, kind="morning")
        self.assertLessEqual(len(text.split()), 220)
        self.assertIn("Aged decision: freeze the demo "
                      "fixture at noon", text)
        self.assertIn("Due commitment: ship the demo cut",
                      text)

    def test_spec_names_os092_and_its_proof_gap(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "brief_boot.md")
        with open(path) as handle:
            spec = handle.read()
        self.assertIn("OS-092", spec)
        self.assertIn("memory_depth", spec)
        self.assertIn("still owed", spec)


class DailyBriefLinesTest(unittest.TestCase):
    # OS-075: Dale's daily brief section, the last
    # untried Hana task. A stated daily record names
    # the overnight results, today's queue, and what
    # needs Dale's word verbatim, after Watch items;
    # unusable entries are skipped, never padded; an
    # empty record reads none reported, never a
    # padded item. NOT proven here: the section in
    # a daily brief read on the desktop session --
    # Rowan OS-071 has not landed and two weeks of
    # daily briefs on the daily machine have not
    # run, so no caller yet fills "daily" and no
    # prompt-history change from Dale's feedback is
    # recorded; these tests prove the rendering from
    # a stated record, the same fixture pattern as
    # OS-048 through OS-127. This is a Phase B [B]
    # task built early as a renderer only.
    DAILY = {"overnight_results": ["shipped the brief panel"],
             "todays_queue": [{"id": "7", "title": "boot shot"}],
             "needs_word": [{"question": "ship the demo cut?",
                             "job": "7"}]}

    def _snapshot(self, daily=DAILY):
        snapshot = {
            "source_window": "last 500 messages or last "
                             "24 hours",
            "messages": [{"nick": "pax",
                          "text": "DECISION: freeze the demo "
                                  "fixture at noon"}],
            "jobs": [{"id": "5", "title": "brief panel",
                      "status": "claimed", "claim": "rowan"}],
            "alerts": [{"id": "ALERT-1",
                        "summary": "stall on job 2"}],
        }
        if daily is not None:
            snapshot["daily"] = daily
        return snapshot

    def test_all_three_categories_named_verbatim(self):
        snapshot = self._snapshot()
        snapshot["memory_depth"] = {"fresh_context": ["context"]}
        text = brief.compose_template_brief(snapshot)
        self.assertIn("Daily brief", text)
        self.assertIn("Overnight result: shipped the brief panel",
                      text)
        self.assertIn("Today's queue: job 7 boot shot", text)
        self.assertIn("Needs your word: ship the demo cut? "
                      "(job 7)", text)
        self.assertLess(text.index("Watch items"),
                        text.index("Daily brief"))
        self.assertLess(text.index("Daily brief"),
                        text.index("Long-term memory"))

    def test_no_daily_key_carries_no_section(self):
        text = brief.compose_template_brief(
            self._snapshot(None))
        self.assertNotIn("Daily brief", text)
        self.assertNotIn("Overnight result", text)
        self.assertNotIn("Needs your word", text)

    def test_unusable_entries_skipped_never_padded(self):
        daily = {"overnight_results": ["shipped the brief panel",
                                       42, ""],
                 "todays_queue": [{"title": "no id"},
                                  {"id": "8", "title": "real job"}],
                 "needs_word": [{"job": "9"},
                                "go now"]}
        text = brief.compose_template_brief(
            self._snapshot(daily))
        self.assertIn("Overnight result: shipped the brief panel",
                      text)
        self.assertNotIn("42", text)
        self.assertIn("Today's queue: job 8 real job", text)
        self.assertNotIn("no id", text)
        self.assertIn("Needs your word: go now", text)
        self.assertNotIn("job 9", text)

    def test_empty_record_reads_none_reported(self):
        text = brief.compose_template_brief(
            self._snapshot({}))
        self.assertIn("Overnight results: none reported", text)
        self.assertIn("Today's queue: none reported", text)
        self.assertIn("Needs your word: none reported", text)

    def test_empty_window_still_carries_daily_section(self):
        text = brief.compose_template_brief(
            {"daily": self.DAILY})
        self.assertIn("Daily brief", text)
        self.assertIn("Overnight result: shipped the brief panel",
                      text)
        self.assertLess(text.index("Daily brief"),
                        text.index("no activity yet"))

    def test_budget_trim_keeps_daily_lines(self):
        snapshot = self._snapshot()
        snapshot["jobs"] = [{"id": str(n),
                             "title": "job work",
                             "status": "claimed",
                             "claim": "rowan"}
                            for n in range(60)]
        text = brief.compose_brief(snapshot, kind="morning")
        self.assertLessEqual(len(text.split()), 220)
        self.assertIn("Overnight result: shipped the brief panel",
                      text)
        self.assertIn("Needs your word: ship the demo cut?",
                      text)

    def test_age_label_reports_missing_time(self):
        text = brief.compose_template_brief(self._snapshot())
        self.assertIn("(snapshot time not reported)", text)

    def test_spec_names_os075_and_its_proof_gap(self):
        import os
        path = os.path.join(os.path.dirname(__file__), "..",
                            "intel", "prompts", "brief_boot.md")
        with open(path) as handle:
            spec = handle.read()
        self.assertIn("OS-075", spec)
        self.assertIn("daily", spec)
        self.assertIn("still owed", spec)


if __name__ == "__main__":
    unittest.main()
