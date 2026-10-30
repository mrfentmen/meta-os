"""BRF-018 follow-up: the template composer renders the BRF-002
on-join sections for kind="onjoin", instead of the morning
sections it rendered for every kind before this change.

A newcomer reading only this brief must find, in order: what
the crew is building, their likely lane, what is blocked, and
who to ask — with nothing guessed: no project sentence when
the snapshot states none, no lane from a job title, no owner
when none is recorded. NOT proven here: a Spark-composed
on-join brief under the v2 prompt (real Spark transport still
blocked), or a brief for a newcomer named by a lane caller
(no lane caller invokes kind="onjoin" yet); these tests prove
the template rendering from stated snapshots, the same
fixture pattern as the other section follow-ups.
"""

import unittest

from intel import brief


class OnJoinTemplateTest(unittest.TestCase):
    # The BRF-018 busy snapshot: 3 messages (2 DECISION, 1
    # DONE), 5 jobs (2 claimed, 1 open, 1 blocked, 1 done),
    # 1 alert, presence pax, milo, rowan, del, sam. Newcomer
    # sam is present with no prior message.
    def _snapshot(self, **overrides):
        snapshot = {
            "source_window": "2026-10-27 08:00 ET onward, "
                             "last 24 hours",
            "messages": ["pax: DECISION: freeze the demo fixture "
                         "at noon",
                         "milo: done: watchdog loop passes its checks",
                         "rowan: DECISION: carry open jobs into the "
                         "morning"],
            "jobs": [
                {"id": "2", "title": "brief panel",
                 "status": "claimed", "claim": "rowan",
                 "claimed_at": 1000},
                {"id": "5", "title": "dispatch poster",
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
        snapshot.update(overrides)
        return snapshot

    def test_onjoin_renders_four_sections_in_order(self):
        text = brief.compose_template_brief(
            self._snapshot(), kind="onjoin")
        self.assertTrue(text.startswith("TEMPLATE"))
        self.assertIn("Window: 2026-10-27 08:00 ET onward, "
                      "last 24 hours", text)
        sections = ["What this crew is building",
                    "Your likely lane",
                    "What is blocked",
                    "Who to ask"]
        positions = [text.index(section) for section in sections]
        self.assertEqual(positions, sorted(positions))
        # Morning sections are gone: this is an on-join
        # brief now, not a morning brief in disguise.
        self.assertNotIn("\nDecisions\n", text)
        self.assertNotIn("\nIn flight\n", text)
        self.assertNotIn("\nOwners\n", text)
        # Additive INT-004 sections follow the four, in
        # morning bullet form, because the e2e3 loop reads
        # the blocked job and the alert from them.
        self.assertIn("\nBlocked and why\n", text)
        self.assertIn("- 7 spark client: waiting on the real "
                      "Spark endpoint", text)
        self.assertIn("\nWatch items\n", text)
        self.assertIn("- ALERT-1: stall on job 2", text)
        self.assertLess(
            text.index("Who to ask"),
            text.index("Blocked and why"))
        self.assertLess(
            text.index("Blocked and why"),
            text.index("Watch items"))

    def test_no_blocked_no_alerts_means_no_additive_sections(self):
        snapshot = self._snapshot()
        snapshot["jobs"] = [job for job in snapshot["jobs"]
                            if job["status"] != "blocked"]
        snapshot["alerts"] = []
        text = brief.compose_template_brief(
            snapshot, kind="onjoin")
        self.assertIn("Nothing blocked in this window", text)
        self.assertNotIn("\nBlocked and why\n", text)
        self.assertNotIn("\nWatch items\n", text)

    def test_crew_building_not_stated_without_a_stated_sentence(self):
        text = brief.compose_template_brief(
            self._snapshot(), kind="onjoin")
        self.assertIn("The room's current work is not stated "
                      "in this window", text)

    def test_crew_building_stated_verbatim_when_caller_states_it(self):
        text = brief.compose_template_brief(
            self._snapshot(
                crew_building="The crew is building a relay "
                              "dashboard for the build."),
            kind="onjoin")
        self.assertIn("The crew is building a relay dashboard "
                      "for the build.", text)

    def test_likely_lane_names_open_job_lane_in_v2_form(self):
        jobs = self._snapshot()["jobs"]
        jobs[2] = dict(jobs[2], lane="briefings")
        text = brief.compose_template_brief(
            self._snapshot(jobs=jobs), kind="onjoin")
        self.assertIn("The open job dashboard help text belongs "
                      "to the briefings lane", text)

    def test_likely_lane_never_guessed_from_a_title(self):
        text = brief.compose_template_brief(
            self._snapshot(), kind="onjoin")
        self.assertNotIn("belongs to the", text)
        self.assertIn("Open job: 6 dashboard help text", text)

    def test_newcomer_caps_named_verbatim(self):
        text = brief.compose_template_brief(
            self._snapshot(
                caps={"sam": {"caps": "build, docs",
                              "roles": "builder"}}),
            kind="onjoin")
        self.assertIn("sam's capability record lists build, docs; "
                      "roles: builder", text)

    def test_no_lane_no_caps_points_to_first_owner(self):
        text = brief.compose_template_brief(
            self._snapshot(), kind="onjoin")
        self.assertIn("No capability record and no open job "
                      "lane are stated in this window.", text)
        self.assertIn("Ask rowan for a first job", text)

    def test_no_owner_recorded_said_plainly(self):
        snapshot = self._snapshot()
        snapshot["jobs"] = [job for job in snapshot["jobs"]
                            if job["status"] not in
                            ("claimed", "open")]
        snapshot["presence"] = ["sam"]
        text = brief.compose_template_brief(
            snapshot, kind="onjoin")
        self.assertIn("No owner is recorded in this window", text)

    def test_blocked_reason_verbatim_and_nothing_blocked_line(self):
        text = brief.compose_template_brief(
            self._snapshot(), kind="onjoin")
        self.assertIn("7 spark client: waiting on the real "
                      "Spark endpoint", text)
        snapshot = self._snapshot()
        snapshot["jobs"] = [job for job in snapshot["jobs"]
                            if job["status"] != "blocked"]
        text = brief.compose_template_brief(
            snapshot, kind="onjoin")
        self.assertIn("Nothing blocked in this window", text)

    def test_who_to_ask_marks_absent_owners_not_online(self):
        # rowan and pax are present; add a claimed job for
        # buffy, who is not in presence, and check only she
        # carries the marker.
        snapshot = self._snapshot()
        snapshot["jobs"] = snapshot["jobs"] + [
            {"id": "9", "title": "panel notes",
             "status": "claimed", "claim": "buffy",
             "claimed_at": 1000}]
        text = brief.compose_template_brief(
            snapshot, kind="onjoin")
        self.assertIn("rowan: brief panel", text)
        self.assertNotIn("rowan: brief panel (not online",
                         text)
        self.assertIn("buffy: panel notes (not online in this "
                      "window)", text)

    def test_blocked_contact_ask_nick_in_who_to_ask(self):
        text = brief.compose_template_brief(
            self._snapshot(
                blocked_contacts={"contacts": [
                    {"job_id": "7", "ask": "milo"}]}),
            kind="onjoin")
        self.assertIn("Ask milo about 7 spark client", text)

    def test_default_kind_keeps_morning_shape_exactly(self):
        text = brief.compose_template_brief(self._snapshot())
        self.assertIn("\nDecisions\n", text)
        self.assertIn("\nIn flight\n", text)
        self.assertNotIn("What this crew is building", text)
        self.assertNotIn("Your likely lane", text)

    def test_unknown_kind_falls_back_to_morning(self):
        text = brief.compose_template_brief(
            self._snapshot(), kind="bogus")
        self.assertIn("\nDecisions\n", text)
        self.assertNotIn("What this crew is building", text)

    def test_boot_plus_onjoin_keeps_boot_shape(self):
        text = brief.compose_template_brief(
            self._snapshot(), boot=True, kind="onjoin")
        self.assertIn("\nDecisions\n", text)
        self.assertNotIn("What this crew is building", text)

    def test_compose_onjoin_carries_sections_within_budget(self):
        text = brief.compose_brief(self._snapshot(),
                                   kind="onjoin")
        self.assertLessEqual(len(text.split()), 150)
        self.assertIn("What this crew is building", text)
        self.assertIn("Your likely lane", text)
        self.assertIn("7 spark client: waiting on the real "
                      "Spark endpoint", text)

    def test_generate_onjoin_dry_run_carries_sections(self):
        text, _record = brief.generate_brief(
            self._snapshot(), "build", kind="onjoin",
            dry_run=True)
        self.assertIn("What this crew is building", text)
        self.assertIn("Who to ask", text)

    def test_non_dict_snapshot_never_raises(self):
        text = brief.compose_template_brief(None, kind="onjoin")
        self.assertIn("no activity yet", text)


if __name__ == "__main__":
    unittest.main()
