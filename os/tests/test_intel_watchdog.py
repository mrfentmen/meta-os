"""intel/watchdog.py: watchdog main loop (Milo lane, WDG-001).

Pure-function tests: no network, no Redis, no bus posts. Fixtures
are hand-written snapshot dicts in the shape intel/brief.py
documents. WDG-002 (presence-stall), WDG-003 (progress-stall),
WDG-004 (lease-risk), WDG-005 (dead-dep), WDG-006
(missing-dep), WDG-007 (file-collision), WDG-008
(attempt-exhaustion), and WDG-009 (silent-room, info only)
are registered; a quiet snapshot still yields zero alerts,
and that zero must NOT be read as proof that any other
failure is detected yet.
"""

import importlib
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

sys.path.insert(0, ".")
sys.path.insert(0, "tests")
from helpers import RelayTestCase  # noqa: E402
from intel import thresholds  # noqa: E402
from intel import watchdog  # noqa: E402
from intel import brief  # noqa: E402
from intel import store as istore  # noqa: E402


class TickTest(unittest.TestCase):
    def test_quiet_snapshot_yields_zero_alerts(self):
        # WDG-001 acceptance: --once on a quiet fixture writes
        # zero alerts and exits 0. The tick half: no alerts, and
        # an emit sink (the future WDG-010 writer's seat) is
        # never called.
        emitted = []
        got = watchdog.tick({}, now=1000, emit=emitted.append)
        self.assertEqual(got, [])
        self.assertEqual(emitted, [])

    def test_healthy_busy_snapshot_also_yields_zero_for_now(self):
        # A claimed job with a fresh heartbeat is not, by itself,
        # a failure. With no detectors registered yet the loop
        # still returns zero; WDG-002/WDG-003 will change this
        # file's expectations when detectors land, on purpose.
        snapshot = {
            "messages": [{"nick": "pax", "text": "working on it"}],
            "jobs": [{"id": "1", "title": "demo job", "status": "claimed",
                      "claim": "pax", "claimed_at": 900}],
            "presence": ["pax"],
            "caps": {"pax": {"caps": "build"}},
        }
        self.assertEqual(watchdog.tick(snapshot, now=1000), [])

    def test_missing_sections_are_empty_not_an_error(self):
        self.assertEqual(watchdog.tick(None), [])
        self.assertEqual(watchdog.tick({"jobs": None}), [])

    def test_a_crashing_detector_does_not_blind_the_loop(self):
        def _boom(snapshot, now):
            raise RuntimeError("detector blew up")

        def _ok(snapshot, now):
            return [{"kind": "test", "id": "t1"}]

        with mock.patch.object(watchdog, "DETECTORS", [_boom, _ok]):
            self.assertEqual(
                watchdog.tick({}, now=1000),
                [{"kind": "test", "id": "t1"}])

    def test_emit_receives_each_alert_in_order(self):
        def _two(snapshot, now):
            return [{"id": "a"}, {"id": "b"}]

        seen = []
        with mock.patch.object(watchdog, "DETECTORS", [_two]):
            got = watchdog.tick({}, now=1000, emit=seen.append)
        self.assertEqual(got, [{"id": "a"}, {"id": "b"}])
        self.assertEqual(seen, got)


class CliTest(unittest.TestCase):
    def _snapshot_file(self, snapshot):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False)
        json.dump(snapshot, handle)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        return handle.name

    def test_once_on_quiet_fixture_exits_zero(self):
        # WDG-001 acceptance, CLI half.
        path = self._snapshot_file({})
        out = io.StringIO()
        with redirect_stdout(out):
            code = watchdog.main(["--once", "--snapshot", path])
        self.assertEqual(code, 0)
        self.assertIn("0 alert(s)", out.getvalue())

    def test_once_without_snapshot_uses_quiet_snapshot(self):
        out = io.StringIO()
        with redirect_stdout(out):
            code = watchdog.main(["--once"])
        self.assertEqual(code, 0)
        self.assertIn("0 alert(s)", out.getvalue())

    def test_once_with_bad_snapshot_file_exits_one(self):
        code = watchdog.main(["--once", "--snapshot",
                              "/nonexistent/snapshot.json"])
        self.assertEqual(code, 1)

    def test_loop_runs_bounded_ticks_then_exits_zero(self):
        path = self._snapshot_file({})
        out = io.StringIO()
        with redirect_stdout(out):
            code = watchdog.main(["--loop", "--snapshot", path,
                                  "--interval", "0", "--max-ticks", "2"])
        self.assertEqual(code, 0)
        self.assertEqual(out.getvalue().count("0 alert(s)"), 2)

    def test_neither_mode_is_an_error(self):
        with self.assertRaises(SystemExit):
            watchdog.main([])


class PresenceStallTest(unittest.TestCase):
    """WDG-002: nick in caps, absent from presence, claimed job idle."""

    def _stall_snapshot(self, **overrides):
        snapshot = {
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9340}],
            "presence": ["hana"],
            "caps": {"pax": {"caps": "build"}},
        }
        snapshot.update(overrides)
        return snapshot

    def test_stall_fixture_yields_exactly_one_alert_naming_all(self):
        # WDG-002 acceptance: exactly one stall alert naming the
        # nick, the job, and the last-progress age (660s = 11 min).
        got = watchdog.tick(self._stall_snapshot(), now=10000)
        self.assertEqual(len(got), 1)
        alert = got[0]
        self.assertEqual(alert["kind"], "presence-stall")
        self.assertEqual(alert["nick"], "pax")
        self.assertEqual(alert["job"], "7")
        self.assertEqual(alert["last_progress_age_seconds"], 660)
        self.assertEqual(alert["last_progress_age_minutes"], 11)

    def test_present_nick_with_idle_job_is_not_presence_stall(self):
        # Present but unmoving is WDG-003's case, not this one:
        # exactly one progress-stall alert, zero presence-stall.
        snapshot = self._stall_snapshot(presence=["pax", "hana"])
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "progress-stall")
        self.assertEqual(got[0]["nick"], "pax")
        self.assertEqual(got[0]["job"], "7")

    def test_fresh_claimed_job_is_not_a_stall(self):
        snapshot = self._stall_snapshot()
        snapshot["jobs"][0]["claimed_at"] = 9900  # 100s ago
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_absent_nick_with_no_claimed_job_is_not_a_stall(self):
        snapshot = self._stall_snapshot()
        snapshot["jobs"][0]["status"] = "open"
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_walk_on_claimer_not_in_caps_is_not_presence_stall(self):
        # WDG-025's case: a claimer never in the caps registry.
        snapshot = self._stall_snapshot(caps={"hana": {}})
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_job_with_no_timestamp_never_invents_an_age(self):
        snapshot = self._stall_snapshot()
        del snapshot["jobs"][0]["claimed_at"]
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_explicit_progress_timestamp_beats_claim_time(self):
        snapshot = self._stall_snapshot()
        snapshot["jobs"][0]["claimed_at"] = 9000
        snapshot["jobs"][0]["last_progress"] = 9950  # 50s ago
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_cli_once_on_stall_fixture_reports_one_alert(self):
        handle = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False)
        json.dump(self._stall_snapshot(), handle)
        handle.close()
        self.addCleanup(os.unlink, handle.name)
        out = io.StringIO()
        with redirect_stdout(out):
            code = watchdog.main(["--once", "--snapshot", handle.name])
        self.assertEqual(code, 0)
        self.assertIn("1 alert(s)", out.getvalue())


class ProgressStallTest(unittest.TestCase):
    """WDG-003: nick present (heartbeat alive), claimed job unmoving."""

    def _progress_snapshot(self, **overrides):
        snapshot = {
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9000, "last_progress": 9340}],
            "presence": ["pax", "hana"],
            "caps": {"pax": {"caps": "build"}},
        }
        snapshot.update(overrides)
        return snapshot

    def test_heartbeat_but_no_progress_yields_exactly_one(self):
        # WDG-003 acceptance: heartbeats-but-no-progress yields
        # a progress-stall alert distinct from presence-stall
        # (660s = 11 min past the 10-minute window).
        got = watchdog.tick(self._progress_snapshot(), now=10000)
        self.assertEqual(len(got), 1)
        alert = got[0]
        self.assertEqual(alert["kind"], "progress-stall")
        self.assertNotEqual(alert["kind"], "presence-stall")
        self.assertEqual(alert["nick"], "pax")
        self.assertEqual(alert["job"], "7")
        self.assertEqual(alert["last_progress_age_seconds"], 660)
        self.assertEqual(alert["last_progress_age_minutes"], 11)
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["dedupe_key"], "progress-stall:pax:7")

    def test_absent_nick_yields_presence_stall_not_progress_stall(self):
        # Distinctness, the other direction: gone worker, same
        # idle job, yields exactly one presence-stall alert and
        # zero progress-stall alerts.
        snapshot = self._progress_snapshot(presence=["hana"])
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "presence-stall")

    def test_fresh_progress_is_not_a_stall(self):
        snapshot = self._progress_snapshot()
        snapshot["jobs"][0]["last_progress"] = 9900  # 100s ago
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_old_claim_with_no_progress_note_is_a_stall(self):
        # Claim time counts as last activity: claimed 11 min ago
        # with no progress note since is stuck work, not a fresh
        # job.
        snapshot = self._progress_snapshot()
        del snapshot["jobs"][0]["last_progress"]
        snapshot["jobs"][0]["claimed_at"] = 9340
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "progress-stall")

    def test_job_with_no_timestamp_never_invents_an_age(self):
        snapshot = self._progress_snapshot()
        del snapshot["jobs"][0]["claimed_at"]
        del snapshot["jobs"][0]["last_progress"]
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_unclaimed_job_is_not_a_stall(self):
        snapshot = self._progress_snapshot()
        snapshot["jobs"][0]["status"] = "open"
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_walk_on_claimer_not_in_caps_is_not_progress_stall(self):
        # WDG-025's case, same as WDG-002.
        snapshot = self._progress_snapshot(caps={"hana": {}})
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_one_alert_per_job_not_per_detector(self):
        # Two idle claimed jobs for the same present worker yield
        # two progress-stall alerts, one per job, no duplicates.
        snapshot = self._progress_snapshot()
        snapshot["jobs"].append(
            {"id": "8", "title": "second job", "status": "claimed",
             "claim": "pax", "claimed_at": 9000,
             "last_progress": 9300})
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 2)
        self.assertEqual({a["job"] for a in got}, {"7", "8"})
        self.assertTrue(all(a["kind"] == "progress-stall" for a in got))


class LeaseRiskTest(unittest.TestCase):
    def _lease_snapshot(self, **job_overrides):
        # Fresh claim (100s ago, present nick) so no stall
        # detector fires; only the lease fields vary.
        job = {"id": "9", "title": "lease job",
               "status": "claimed", "claim": "pax",
               "claimed_at": 9900, "lease_until": 10240}
        job.update(job_overrides)
        return {"jobs": [job],
                "presence": ["pax"],
                "caps": {"pax": {"caps": "build"}}}

    def test_near_expiry_with_quiet_heartbeat_yields_warning(self):
        # WDG-004 acceptance: lease expiring in 4 min, last
        # heartbeat derived as lease_until - default lease
        # (10240 - 1800 = 8440, 1560s ago, past the 2-min quiet
        # window) yields exactly one warning alert naming nick,
        # job, and seconds to expiry.
        got = watchdog.tick(self._lease_snapshot(), now=10000)
        self.assertEqual(len(got), 1)
        alert = got[0]
        self.assertEqual(alert["kind"], "lease-risk")
        self.assertEqual(alert["severity"], "warning")
        self.assertEqual(alert["nick"], "pax")
        self.assertEqual(alert["job"], "9")
        self.assertEqual(alert["seconds_to_expiry"], 240)
        self.assertEqual(alert["minutes_to_expiry"], 4)
        self.assertEqual(alert["dedupe_key"], "lease-risk:pax:9")
        self.assertIn("9", alert["explanation"])

    def test_recent_heartbeat_with_short_lease_is_not_a_risk(self):
        # Lease expiring in 90s but heartbeat 30s ago (short
        # 120s lease: 10090 - 120 = 9970) is a live worker
        # renewing fast, not a risk — the quiet condition
        # matters, not just the expiry window.
        snapshot = self._lease_snapshot(lease_until=10090, lease=120)
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_explicit_heartbeat_beats_derived_heartbeat(self):
        # Explicit heartbeat_at 10s ago suppresses the warning
        # even with the lease expiring in 3 min.
        snapshot = self._lease_snapshot(lease_until=10180,
                                        heartbeat_at=9990)
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_lease_far_from_expiry_is_not_a_risk(self):
        snapshot = self._lease_snapshot(lease_until=11000)
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_already_expired_lease_is_not_a_warning(self):
        # Expired is the sweep's job, not a warning: no alert.
        snapshot = self._lease_snapshot(lease_until=9990)
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_job_without_lease_until_never_invents_an_expiry(self):
        snapshot = self._lease_snapshot()
        del snapshot["jobs"][0]["lease_until"]
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_requeued_job_stops_firing(self):
        # WDG-004 acceptance, auto-resolve half: once the sweep
        # requeues the job (status back to open) the detector
        # stops firing on it. The alert lifecycle itself is
        # WDG-014's work, not claimed here.
        snapshot = self._lease_snapshot(status="open")
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_walk_on_claimer_lease_still_warned(self):
        # Lease risk is job data, not caps data: a walk-on
        # worker's expiring lease still warns (WDG-025 direction).
        snapshot = self._lease_snapshot()
        snapshot["caps"] = {"hana": {}}
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "lease-risk")


class DeadDepTest(unittest.TestCase):
    def _snapshot(self, job_overrides=None, dep_overrides=None):
        # Job B (id 2) depends on job A (id 1). B is open, so no
        # stall/lease detector can fire on it; only the dep
        # state varies.
        job = {"id": "2", "title": "blocked job", "status": "open",
               "deps": "1"}
        if job_overrides:
            job.update(job_overrides)
        dep = {"id": "1", "title": "dep job", "status": "blocked",
               "note": "waiting on vendor API key"}
        if dep_overrides:
            dep.update(dep_overrides)
        return {"jobs": [job, dep]}

    def test_blocked_dep_yields_one_critical_alert(self):
        # WDG-005 acceptance: dead-dep fixture yields one alert
        # naming both job ids and the blocking reason verbatim.
        got = watchdog.tick(self._snapshot(), now=10000)
        self.assertEqual(len(got), 1)
        alert = got[0]
        self.assertEqual(alert["kind"], "dead-dep")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["job"], "2")
        self.assertEqual(alert["dep"], "1")
        self.assertEqual(alert["dep_status"], "blocked")
        self.assertEqual(alert["blocking_reason"],
                         "waiting on vendor API key")
        self.assertIn("2", alert["explanation"])
        self.assertIn("1", alert["explanation"])
        self.assertIn("waiting on vendor API key",
                      alert["explanation"])
        self.assertEqual(alert["dedupe_key"], "dead-dep:2:1")

    def test_failed_final_dep_also_dead(self):
        # A failed-final dep cannot proceed either; its status
        # is the reason when it carries no note.
        snapshot = self._snapshot(dep_overrides={"status": "failed-final"})
        del snapshot["jobs"][1]["note"]
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["dep_status"], "failed-final")
        self.assertEqual(got[0]["blocking_reason"], "failed-final")

    def test_claimed_job_with_blocked_dep_also_alerts(self):
        # The sweep reports open AND claimed jobs; so does this
        # detector. The claim is fresh and present, so no stall
        # or lease detector fires alongside it.
        snapshot = self._snapshot(
            job_overrides={"status": "claimed", "claim": "pax",
                           "claimed_at": 9990})
        snapshot["presence"] = ["pax"]
        snapshot["caps"] = {"pax": {"caps": "build"}}
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "dead-dep")

    def test_live_dep_yields_no_alert(self):
        for status in ("open", "claimed", "done"):
            snapshot = self._snapshot(dep_overrides={"status": status})
            self.assertEqual(watchdog.tick(snapshot, now=10000), [],
                             f"dep status {status} must not alert")

    def test_missing_dep_is_not_dead_dep(self):
        # A dep id with no job in the snapshot is WDG-006's
        # missing-dep case, not this detector's: exactly one
        # missing-dep alert, zero dead-dep alerts.
        snapshot = self._snapshot()
        snapshot["jobs"] = [snapshot["jobs"][0]]
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "missing-dep")
        self.assertEqual(got[0]["dep"], "1")

    def test_done_job_with_blocked_dep_yields_no_alert(self):
        snapshot = self._snapshot(job_overrides={"status": "done"})
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_unblocked_dep_stops_firing(self):
        # Auto-resolve half: once the dep is unblocked (back to
        # open), the detector stops firing on the job.
        snapshot = self._snapshot(dep_overrides={"status": "open"})
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_two_dead_deps_yield_one_alert_each(self):
        snapshot = self._snapshot(
            job_overrides={"deps": "1,3"})
        snapshot["jobs"].append(
            {"id": "3", "title": "second dep", "status": "blocked",
             "note": "out of budget"})
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 2)
        self.assertEqual({a["dep"] for a in got}, {"1", "3"})
        self.assertEqual({a["dedupe_key"] for a in got},
                         {"dead-dep:2:1", "dead-dep:2:3"})

    def test_job_with_no_deps_yields_no_alert(self):
        snapshot = self._snapshot(job_overrides={"deps": ""})
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])


class MissingDepTest(unittest.TestCase):
    def _snapshot(self, job_overrides=None, extra_jobs=None):
        # Job B (id 2) depends on job id 9, which exists in no
        # job list here. B is open, so no stall/lease detector
        # can fire on it; only the dep's existence varies.
        job = {"id": "2", "title": "dangling job", "status": "open",
               "deps": "9"}
        if job_overrides:
            job.update(job_overrides)
        jobs = [job]
        if extra_jobs:
            jobs.extend(extra_jobs)
        return {"jobs": jobs}

    def test_dangling_dep_yields_one_critical_alert(self):
        # WDG-006 acceptance: fixture with a dangling dep
        # yields a missing-dep alert naming both job ids.
        got = watchdog.tick(self._snapshot(), now=10000)
        self.assertEqual(len(got), 1)
        alert = got[0]
        self.assertEqual(alert["kind"], "missing-dep")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["job"], "2")
        self.assertEqual(alert["dep"], "9")
        self.assertIn("2", alert["explanation"])
        self.assertIn("9", alert["explanation"])
        self.assertEqual(alert["dedupe_key"], "missing-dep:2:9")

    def test_claimed_job_with_dangling_dep_also_alerts(self):
        # A claimed job waiting on a nonexistent dep is just
        # as stuck as an open one. The claim is fresh and
        # present, so no stall or lease detector fires
        # alongside it.
        snapshot = self._snapshot(
            job_overrides={"status": "claimed", "claim": "pax",
                           "claimed_at": 9990})
        snapshot["presence"] = ["pax"]
        snapshot["caps"] = {"pax": {"caps": "build"}}
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "missing-dep")

    def test_existing_dep_yields_no_alert(self):
        # A dep that exists in any status is not missing.
        # Blocked/failed-final deps still fire WDG-005's
        # dead-dep alert (that is the correct detector for
        # them), so this test asserts zero missing-dep
        # alerts, and an empty tick only for live statuses.
        for status in ("open", "claimed", "done", "blocked",
                       "failed-final"):
            snapshot = self._snapshot(extra_jobs=[
                {"id": "9", "title": "real dep", "status": status}])
            got = watchdog.tick(snapshot, now=10000)
            self.assertEqual(
                [a for a in got if a["kind"] == "missing-dep"], [],
                f"existing dep status {status} must not "
                "yield missing-dep")
            if status in ("open", "claimed", "done"):
                self.assertEqual(got, [],
                                 f"live dep status {status} "
                                 "must not alert at all")

    def test_dead_dep_and_missing_dep_do_not_cross_fire(self):
        # One job with a blocked dep and a dangling dep yields
        # exactly one dead-dep alert and one missing-dep alert,
        # no more, no fewer.
        snapshot = self._snapshot(
            job_overrides={"deps": "1,9"},
            extra_jobs=[{"id": "1", "title": "blocked dep",
                         "status": "blocked",
                         "note": "waiting on vendor API key"}])
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 2)
        self.assertEqual({a["kind"] for a in got},
                         {"dead-dep", "missing-dep"})
        self.assertEqual({a["dep"] for a in got}, {"1", "9"})

    def test_two_dangling_deps_yield_one_alert_each(self):
        snapshot = self._snapshot(job_overrides={"deps": "9,10"})
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 2)
        self.assertEqual({a["dep"] for a in got}, {"9", "10"})
        self.assertEqual({a["dedupe_key"] for a in got},
                         {"missing-dep:2:9", "missing-dep:2:10"})

    def test_done_job_with_dangling_dep_yields_no_alert(self):
        snapshot = self._snapshot(job_overrides={"status": "done"})
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_list_form_deps_are_checked_too(self):
        snapshot = self._snapshot(job_overrides={"deps": ["9"]})
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["dep"], "9")

    def test_job_with_no_deps_yields_no_alert(self):
        snapshot = self._snapshot(job_overrides={"deps": ""})
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_posting_the_missing_job_clears_the_alert(self):
        # Auto-resolve half: once job 9 is actually posted,
        # the detector stops firing on job 2.
        snapshot = self._snapshot(extra_jobs=[
            {"id": "9", "title": "late dep", "status": "open"}])
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])


class FileCollisionTest(unittest.TestCase):
    def _claimed(self, job_id, nick, files):
        # Fresh claim, present nick, in caps: no stall or
        # lease detector can fire on it, so any alert in
        # these tests is a collision alert, or a test bug.
        return {"id": job_id, "title": f"job {job_id}",
                "status": "claimed", "claim": nick,
                "claimed_at": 9990, "files": files}

    def _snapshot(self, jobs):
        nicks = [j["claim"] for j in jobs
                 if isinstance(j, dict) and j.get("claim")]
        return {"jobs": jobs, "presence": nicks,
                "caps": {n: {"caps": "build"} for n in nicks}}

    def test_overlapping_claimed_pair_yields_one_critical_alert(self):
        # WDG-007 acceptance: collision fixture yields one
        # alert naming the shared path and both jobs.
        snapshot = self._snapshot([
            self._claimed("1", "pax", "intel/watchdog.py, intel/store.py"),
            self._claimed("2", "rowan", "intel/store.py, intel/brief.py")])
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        alert = got[0]
        self.assertEqual(alert["kind"], "file-collision")
        self.assertEqual(alert["severity"], "critical")
        self.assertEqual(alert["job"], "1")
        self.assertEqual(alert["other_job"], "2")
        self.assertEqual(alert["shared_path"], "intel/store.py")
        self.assertIn("1", alert["explanation"])
        self.assertIn("2", alert["explanation"])
        self.assertIn("intel/store.py", alert["explanation"])
        self.assertEqual(alert["dedupe_key"],
                         "file-collision:1:2:intel/store.py")

    def test_disjoint_files_yield_no_alert(self):
        snapshot = self._snapshot([
            self._claimed("1", "pax", "intel/watchdog.py"),
            self._claimed("2", "rowan", "intel/brief.py")])
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_open_job_overlapping_claimed_yields_no_alert(self):
        # An open job is not being worked yet: nothing to
        # collide with, even on the same path.
        snapshot = self._snapshot([
            self._claimed("1", "pax", "intel/store.py"),
            {"id": "2", "title": "open job", "status": "open",
             "files": "intel/store.py"}])
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_claimed_overlapping_done_branch_yields_alert(self):
        # Done job with a branch name is an unmerged branch:
        # a new claim on one of its paths is a collision.
        snapshot = self._snapshot([
            self._claimed("1", "pax", "intel/store.py"),
            {"id": "2", "title": "done job", "status": "done",
             "branch": "worker/rowan/feature",
             "files": "intel/store.py"}])
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "file-collision")
        self.assertEqual(got[0]["other_job"], "2")
        self.assertEqual(got[0]["other_status"], "done")
        self.assertEqual(got[0]["branch"], "worker/rowan/feature")
        self.assertIn("intel/store.py", got[0]["explanation"])

    def test_claimed_overlapping_done_without_branch_yields_no_alert(self):
        # No branch data on the done job: finished work with
        # no branch to collide with, per the acceptance.
        snapshot = self._snapshot([
            self._claimed("1", "pax", "intel/store.py"),
            {"id": "2", "title": "done job", "status": "done",
             "files": "intel/store.py"}])
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_two_shared_paths_yield_one_alert_each(self):
        snapshot = self._snapshot([
            self._claimed("1", "pax", "a.py, b.py"),
            self._claimed("2", "rowan", "b.py, a.py")])
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 2)
        self.assertEqual({a["shared_path"] for a in got},
                         {"a.py", "b.py"})
        self.assertEqual({a["dedupe_key"] for a in got},
                         {"file-collision:1:2:a.py",
                          "file-collision:1:2:b.py"})

    def test_duplicate_path_on_one_job_counts_once(self):
        snapshot = self._snapshot([
            self._claimed("1", "pax", "a.py, a.py"),
            self._claimed("2", "rowan", "a.py")])
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)

    def test_list_form_files_are_checked_too(self):
        snapshot = self._snapshot([
            self._claimed("1", "pax", ["a.py"]),
            self._claimed("2", "rowan", ["a.py", "c.py"])])
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["shared_path"], "a.py")

    def test_job_with_no_files_yields_no_alert(self):
        snapshot = self._snapshot([
            self._claimed("1", "pax", ""),
            self._claimed("2", "rowan", "a.py")])
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_removing_the_overlap_clears_the_alert(self):
        # Auto-resolve half: once the jobs no longer share a
        # path, the detector stops firing on them.
        jobs = [self._claimed("1", "pax", "a.py"),
                self._claimed("2", "rowan", "a.py")]
        self.assertEqual(len(watchdog.tick(
            self._snapshot(jobs), now=10000)), 1)
        jobs[1]["files"] = "b.py"
        self.assertEqual(watchdog.tick(
            self._snapshot(jobs), now=10000), [])


class AttemptExhaustionTest(unittest.TestCase):
    def _snapshot(self, jobs):
        return {"jobs": jobs}

    def _job(self, attempts, max_attempts, status="open"):
        return {"id": "7", "title": "flaky job", "status": status,
                "claim": "pax", "attempts": attempts,
                "max_attempts": max_attempts}

    def test_walk_produces_warning_at_max_minus_one_then_critical(self):
        # WDG-008 acceptance, fixture walk: attempts 0..3
        # against a budget of 3 stay silent until 2 (one left),
        # then warn once; at 3 the warning is replaced by the
        # critical failed-final alert, never both at once.
        for attempts in (0, 1):
            got = watchdog.tick(
                self._snapshot([self._job(attempts, 3)]), now=10000)
            self.assertEqual(got, [],
                             f"attempts={attempts} should be silent")
        got = watchdog.tick(
            self._snapshot([self._job(2, 3)]), now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "attempt-warning")
        self.assertEqual(got[0]["severity"], "warning")
        self.assertEqual(got[0]["job"], "7")
        self.assertEqual(got[0]["attempts"], 2)
        self.assertEqual(got[0]["max_attempts"], 3)
        self.assertEqual(got[0]["attempts_remaining"], 1)
        self.assertEqual(got[0]["dedupe_key"], "attempt-warning:7")
        self.assertIn("7", got[0]["explanation"])
        self.assertIn("one attempt", got[0]["explanation"])
        got = watchdog.tick(
            self._snapshot([self._job(3, 3)]), now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "attempt-exhaustion")
        self.assertEqual(got[0]["severity"], "critical")
        self.assertEqual(got[0]["job"], "7")
        self.assertEqual(got[0]["attempts_remaining"], 0)
        self.assertEqual(got[0]["dedupe_key"], "attempt-exhaustion:7")
        self.assertIn("failed-final", got[0]["explanation"])
        # Past the budget the critical alert holds, still one.
        got = watchdog.tick(
            self._snapshot([self._job(4, 3)]), now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "attempt-exhaustion")

    def test_failed_final_job_at_max_yields_critical(self):
        # jobs.py marks the job failed-final at requeue time;
        # the detector must fire on that record itself, not
        # only on live jobs approaching the budget.
        got = watchdog.tick(
            self._snapshot([self._job(3, 3, status="failed-final")]),
            now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "attempt-exhaustion")

    def test_claimed_job_at_max_minus_one_warns(self):
        # The heads-up matters on a live claim, not just on
        # an open job waiting for requeue.
        got = watchdog.tick(
            self._snapshot([self._job(2, 3, status="claimed")]),
            now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "attempt-warning")

    def test_no_budget_yields_no_alert_at_any_attempt_count(self):
        for job in (self._job(9, None), self._job(9, ""),
                    {"id": "7", "status": "open", "attempts": 9}):
            self.assertEqual(
                watchdog.tick(self._snapshot([job]), now=10000), [])

    def test_string_form_attempts_match_redis_hashes(self):
        got = watchdog.tick(
            self._snapshot([self._job("2", "3")]), now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "attempt-warning")

    def test_done_job_at_max_yields_no_alert(self):
        # Finished work is not a budget failure, however many
        # attempts it burned getting there.
        self.assertEqual(watchdog.tick(
            self._snapshot([self._job(3, 3, status="done")]),
            now=10000), [])

    def test_budget_of_one_warns_at_zero_then_fails_at_one(self):
        got = watchdog.tick(
            self._snapshot([self._job(0, 1)]), now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "attempt-warning")
        got = watchdog.tick(
            self._snapshot([self._job(1, 1)]), now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "attempt-exhaustion")


class SilentRoomTest(unittest.TestCase):
    def _snapshot(self, jobs, messages):
        return {"jobs": jobs, "messages": messages}

    def _claimed(self, job_id):
        return {"id": job_id, "title": "claimed job",
                "status": "claimed", "claim": "pax",
                "claimed_at": 1000}

    def test_silent_room_yields_info_record_only(self):
        # WDG-009 acceptance, positive case: claimed jobs and
        # zero messages for over the 60-minute threshold yields
        # exactly one record, and it is INFO, never an alert:
        # no critical or warning severity anywhere in the tick.
        snapshot = self._snapshot(
            [self._claimed("1")],
            [{"nick": "pax", "text": "starting", "ts": 1000}])
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        record = got[0]
        self.assertEqual(record["kind"], "silent-room")
        self.assertEqual(record["severity"], "info")
        self.assertEqual(record["claimed_jobs"], ["1"])
        self.assertEqual(record["claimed_count"], 1)
        self.assertEqual(record["last_message_age_seconds"], 9000)
        self.assertEqual(record["dedupe_key"], "silent-room")
        self.assertIn("1", record["explanation"])
        self.assertIn("60", record["explanation"])
        self.assertNotIn("ALERT", record["explanation"])

    def test_dashboard_severity_mapping_silent_room_is_info(self):
        # WDG-009 acceptance, mapping half: the dashboard keys
        # colour off severity, and silent-room must map to the
        # info band, never to the alert bands (critical/warning)
        # that WDG-015 would announce. The whole tick output
        # for a silent fixture carries only the info severity.
        snapshot = self._snapshot(
            [self._claimed("1")],
            [{"nick": "pax", "text": "starting", "ts": 1000}])
        got = watchdog.tick(snapshot, now=10000)
        severities = {record["severity"] for record in got}
        self.assertEqual(severities, {"info"})
        self.assertTrue(all(record["severity"] not in ("critical", "warning")
                            for record in got))

    def test_fresh_message_inside_threshold_yields_no_record(self):
        # Last message 30 minutes ago is inside the 60-minute
        # window: the room is talking, not silent.
        snapshot = self._snapshot(
            [self._claimed("1")],
            [{"nick": "pax", "text": "update", "ts": 8200}])
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_silence_exactly_at_threshold_yields_no_record(self):
        # Boundary matches the other detectors: age must exceed
        # the threshold, not merely reach it.
        snapshot = self._snapshot(
            [self._claimed("1")],
            [{"nick": "pax", "text": "starting", "ts": 6400}])
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_no_claimed_jobs_yields_no_record(self):
        # A quiet room with nothing claimed is normal, even
        # with an ancient last message.
        snapshot = self._snapshot(
            [{"id": "1", "title": "open job", "status": "open"}],
            [{"nick": "pax", "text": "done for now", "ts": 1000}])
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_no_timestamped_messages_yields_no_record(self):
        # No ts on any message (or no messages at all) proves
        # nothing about duration: the detector never invents
        # an age, so a claimed job alone is not silence.
        for messages in ([{"nick": "pax", "text": "working"}],
                         [], ["pax: working"]):
            snapshot = self._snapshot([self._claimed("1")], messages)
            self.assertEqual(watchdog.tick(snapshot, now=10000), [],
                             f"messages={messages} should be silent")

    def test_latest_message_sets_the_clock(self):
        # A recent message resets the silence even when an old
        # message is also in the room.
        snapshot = self._snapshot(
            [self._claimed("1")],
            [{"nick": "pax", "text": "old", "ts": 1000},
             {"nick": "rowan", "text": "new", "ts": 9500}])
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])

    def test_multiple_claimed_jobs_yield_one_room_record(self):
        # Room-level, not per-job: two claimed jobs share one
        # record naming both, so a silent room never spams
        # one record per job.
        snapshot = self._snapshot(
            [self._claimed("1"), self._claimed("2")],
            [{"nick": "pax", "text": "starting", "ts": 1000}])
        got = watchdog.tick(snapshot, now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["claimed_jobs"], ["1", "2"])
        self.assertEqual(got[0]["claimed_count"], 2)

    def test_message_after_tick_time_yields_no_record(self):
        # A timestamp in the future is not silence, it is a
        # clock anomaly: negative age never exceeds the window.
        snapshot = self._snapshot(
            [self._claimed("1")],
            [{"nick": "pax", "text": "starting", "ts": 20000}])
        self.assertEqual(watchdog.tick(snapshot, now=10000), [])


class AlertRecordWriterTest(RelayTestCase):
    """WDG-010: alert record writer via intel/store.py.

    Acceptance: records round-trip, and required fields are
    validated. A detector dict (nick/job fields, dedupe_key,
    no id/room/subjects/resolved_at) becomes a record carrying
    all ten WDG-010 fields, and get_alert reads back exactly
    what write_alert stored.
    """

    def _stall_detector_alert(self):
        return {
            "kind": "presence-stall", "severity": "critical",
            "nick": "pax", "job": "7", "job_title": "demo job",
            "last_progress_age_seconds": 660,
            "explanation": "pax holds claimed job 7 but has been "
                           "absent for over 10 minutes.",
            "suggested_fix": "Check on pax; the lease sweep "
                             "will requeue job 7.",
            "dedupe_key": "presence-stall:pax:7",
            "created_at": 10000,
        }

    def test_detector_alert_round_trips_with_all_required_fields(self):
        record = istore.write_alert(self._stall_detector_alert(),
                                    room="build")
        for field in istore.ALERT_REQUIRED_FIELDS:
            self.assertIn(field, record)
        self.assertEqual(record["id"], "presence-stall:pax:7")
        self.assertEqual(record["room"], "build")
        self.assertEqual(record["subjects"], ["pax", "7"])
        self.assertIsNone(record["resolved_at"])
        self.assertEqual(istore.get_alert(record["id"]), record)

    def test_tick_output_feeds_writer_via_emit(self):
        # The writer is tick's emit seat: a real stall fixture
        # ticked with write_alert as emit persists exactly one
        # validated record, and the tick return value matches it.
        snapshot = {
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9340}],
            "presence": ["hana"],
            "caps": {"pax": {"caps": "build"}},
        }
        written = []
        got = watchdog.tick(
            snapshot, now=10000,
            emit=lambda a: written.append(
                istore.write_alert(a, room="build")))
        self.assertEqual(len(got), 1)
        self.assertEqual(len(written), 1)
        self.assertEqual(written[0]["kind"], "presence-stall")
        self.assertEqual(istore.get_alert(written[0]["id"]),
                         written[0])

    def test_silent_room_record_uses_claimed_jobs_as_subjects(self):
        record = istore.write_alert({
            "kind": "silent-room", "severity": "info",
            "claimed_jobs": ["1", "2"], "claimed_count": 2,
            "last_message_age_seconds": 5400,
            "explanation": "The room has claimed jobs but no "
                           "messages for 90 minutes.",
            "suggested_fix": "No action required: informational "
                            "only.",
            "dedupe_key": "silent-room:build",
            "created_at": 10000,
        }, room="build")
        self.assertEqual(record["subjects"], ["1", "2"])
        self.assertEqual(record["severity"], "info")
        self.assertEqual(istore.get_alert(record["id"]), record)

    def test_missing_required_field_is_rejected_and_stores_nothing(self):
        broken = self._stall_detector_alert()
        del broken["suggested_fix"]
        with self.assertRaises(ValueError):
            istore.write_alert(broken, room="build")
        self.assertIsNone(
            istore.get_alert("presence-stall:pax:7"))

    def test_bad_severity_and_empty_subjects_are_rejected(self):
        bad_severity = self._stall_detector_alert()
        bad_severity["severity"] = "urgent"
        with self.assertRaises(ValueError):
            istore.write_alert(bad_severity, room="build")
        no_subjects = self._stall_detector_alert()
        del no_subjects["nick"]
        del no_subjects["job"]
        with self.assertRaises(ValueError):
            istore.write_alert(no_subjects, room="build")

    def test_explicit_id_and_cleaned_room(self):
        record = istore.write_alert(
            self._stall_detector_alert(), room="Build Room!",
            alert_id="a-99")
        self.assertEqual(record["id"], "a-99")
        self.assertEqual(record["room"], "buildroom")
        self.assertEqual(istore.get_alert("a-99"), record)

    def test_missing_created_at_falls_back_to_given_now(self):
        alert = self._stall_detector_alert()
        del alert["created_at"]
        record = istore.write_alert(alert, room="build", now=5000)
        self.assertEqual(record["created_at"], 5000)


class AlertDedupeTest(RelayTestCase):
    """WDG-013: same dedupe key inside cooldown updates last_seen.

    Acceptance: two ticks on the stall fixture yield one alert
    with last_seen advanced. The cooldown is
    thresholds.ALERT_DEDUPE_COOLDOWN_MINUTES (30 at write
    time): inside it the original record stands with only
    last_seen moved; at or past it the report starts a fresh
    occurrence under the same id.
    """

    def _stall_alert(self, created_at, explanation=None):
        return {
            "kind": "presence-stall", "severity": "critical",
            "nick": "pax", "job": "7", "job_title": "demo job",
            "last_progress_age_seconds": 660,
            "explanation": explanation or "pax holds claimed job 7 "
                           "but has been absent for over 10 minutes.",
            "suggested_fix": "Check on pax; the lease sweep "
                             "will requeue job 7.",
            "dedupe_key": "presence-stall:pax:7",
            "created_at": created_at,
        }

    def _stall_snapshot(self):
        return {
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9340}],
            "presence": ["hana"],
            "caps": {"pax": {"caps": "build"}},
        }

    def test_first_write_sets_last_seen_to_created_at(self):
        record = istore.write_alert(self._stall_alert(10000),
                                    room="build")
        self.assertEqual(record["created_at"], 10000)
        self.assertEqual(record["last_seen"], 10000)
        self.assertEqual(istore.get_alert(record["id"]), record)

    def test_second_write_inside_cooldown_updates_only_last_seen(self):
        first = istore.write_alert(self._stall_alert(10000),
                                   room="build")
        second = istore.write_alert(
            self._stall_alert(10600, explanation="a newer telling"),
            room="build")
        self.assertEqual(second["id"], first["id"])
        self.assertEqual(second["created_at"], 10000)
        self.assertEqual(second["last_seen"], 10600)
        # The ongoing incident keeps its original telling.
        self.assertEqual(second["explanation"], first["explanation"])
        self.assertEqual(istore.get_alert(first["id"]), second)

    def test_two_ticks_yield_one_alert_with_last_seen_advanced(self):
        snapshot = self._stall_snapshot()
        watchdog.tick(snapshot, now=10000,
                      emit=lambda a: istore.write_alert(a,
                                                         room="build"))
        watchdog.tick(snapshot, now=10600,
                      emit=lambda a: istore.write_alert(a,
                                                         room="build"))
        record = istore.get_alert("presence-stall:pax:7")
        self.assertIsNotNone(record)
        self.assertEqual(record["created_at"], 10000)
        self.assertEqual(record["last_seen"], 10600)

    def test_write_at_cooldown_boundary_starts_fresh_occurrence(self):
        istore.write_alert(self._stall_alert(10000), room="build")
        fresh = istore.write_alert(
            self._stall_alert(11800, explanation="still stalled"),
            room="build")
        self.assertEqual(fresh["created_at"], 11800)
        self.assertEqual(fresh["last_seen"], 11800)
        self.assertEqual(fresh["explanation"], "still stalled")
        self.assertEqual(istore.get_alert(fresh["id"]), fresh)

    def test_different_dedupe_keys_are_not_merged(self):
        istore.write_alert(self._stall_alert(10000), room="build")
        other = self._stall_alert(10000)
        other["job"] = "8"
        other["dedupe_key"] = "presence-stall:pax:8"
        istore.write_alert(other, room="build")
        self.assertIsNotNone(istore.get_alert("presence-stall:pax:7"))
        self.assertIsNotNone(istore.get_alert("presence-stall:pax:8"))


class AlertLifecycleTest(RelayTestCase):
    """WDG-014: alert lifecycle open -> acknowledged -> resolved.

    Acceptance: a lifecycle test walks all transitions, and
    auto-resolve fires when the fixture condition clears. The
    CLI surface is intel.py alerts --ack/--resolve (same store
    calls, same exit contract as --show); the store transitions
    are asserted here on the fake Redis surface.
    """

    def _stall_alert(self, created_at):
        return {
            "kind": "presence-stall", "severity": "critical",
            "nick": "pax", "job": "7", "job_title": "demo job",
            "last_progress_age_seconds": 660,
            "explanation": "pax holds claimed job 7 but has been "
                           "absent for over 10 minutes.",
            "suggested_fix": "Check on pax; the lease sweep "
                             "will requeue job 7.",
            "dedupe_key": "presence-stall:pax:7",
            "created_at": created_at,
        }

    def _stall_snapshot(self):
        return {
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9340}],
            "presence": ["hana"],
            "caps": {"pax": {"caps": "build"}},
        }

    def test_new_record_starts_open(self):
        record = istore.write_alert(self._stall_alert(10000),
                                    room="build")
        self.assertEqual(record["status"], "open")
        self.assertIsNone(record["acknowledged_at"])
        self.assertIsNone(record["resolved_at"])
        self.assertEqual(istore.alert_status(record), "open")

    def test_ack_then_resolve_walks_all_transitions(self):
        record = istore.write_alert(self._stall_alert(10000),
                                    room="build")
        acked = istore.acknowledge_alert(record["id"], now=10100)
        self.assertEqual(acked["status"], "acknowledged")
        self.assertEqual(acked["acknowledged_at"], 10100)
        self.assertIsNone(acked["resolved_at"])
        self.assertEqual(istore.get_alert(record["id"]), acked)
        resolved = istore.resolve_alert(record["id"], now=10200)
        self.assertEqual(resolved["status"], "resolved")
        # The acknowledged stamp survives: the full walk shows.
        self.assertEqual(resolved["acknowledged_at"], 10100)
        self.assertEqual(resolved["resolved_at"], 10200)
        self.assertEqual(istore.get_alert(record["id"]), resolved)

    def test_resolve_straight_from_open(self):
        record = istore.write_alert(self._stall_alert(10000),
                                    room="build")
        resolved = istore.resolve_alert(record["id"], now=10100)
        self.assertEqual(resolved["status"], "resolved")
        self.assertIsNone(resolved["acknowledged_at"])
        self.assertEqual(resolved["resolved_at"], 10100)

    def test_ack_and_resolve_are_idempotent(self):
        record = istore.write_alert(self._stall_alert(10000),
                                    room="build")
        first_ack = istore.acknowledge_alert(record["id"], now=10100)
        second_ack = istore.acknowledge_alert(record["id"], now=10900)
        self.assertEqual(second_ack, first_ack)
        first_resolve = istore.resolve_alert(record["id"], now=10200)
        second_resolve = istore.resolve_alert(record["id"],
                                              now=10900)
        self.assertEqual(second_resolve, first_resolve)

    def test_ack_of_resolved_is_refused_and_stores_nothing_new(self):
        record = istore.write_alert(self._stall_alert(10000),
                                    room="build")
        istore.resolve_alert(record["id"], now=10100)
        with self.assertRaises(ValueError):
            istore.acknowledge_alert(record["id"], now=10200)
        stored = istore.get_alert(record["id"])
        self.assertEqual(stored["status"], "resolved")
        self.assertIsNone(stored["acknowledged_at"])

    def test_transitions_on_missing_alert_return_none(self):
        self.assertIsNone(istore.acknowledge_alert("nope"))
        self.assertIsNone(istore.resolve_alert("nope"))

    def test_refire_after_resolve_starts_fresh_open_occurrence(self):
        istore.write_alert(self._stall_alert(10000), room="build")
        istore.resolve_alert("presence-stall:pax:7", now=10100)
        fresh = istore.write_alert(self._stall_alert(12000),
                                   room="build")
        self.assertEqual(fresh["status"], "open")
        self.assertEqual(fresh["created_at"], 12000)
        self.assertIsNone(fresh["acknowledged_at"])
        self.assertIsNone(fresh["resolved_at"])

    def test_refire_while_acknowledged_keeps_ack_inside_cooldown(self):
        istore.write_alert(self._stall_alert(10000), room="build")
        istore.acknowledge_alert("presence-stall:pax:7", now=10100)
        refired = istore.write_alert(self._stall_alert(10600),
                                     room="build")
        self.assertEqual(refired["status"], "acknowledged")
        self.assertEqual(refired["acknowledged_at"], 10100)
        self.assertEqual(refired["last_seen"], 10600)
        self.assertIsNone(refired["resolved_at"])

    def test_auto_resolve_fires_when_fixture_condition_clears(self):
        # Tick 1: stall fires and is written. Tick 2: the worker
        # is back in presence, so the tick fires nothing — the
        # condition cleared, and the tracked alert auto-resolves.
        watchdog.tick(self._stall_snapshot(), now=10000,
                      emit=lambda a: istore.write_alert(a,
                                                         room="build"))
        cleared = dict(self._stall_snapshot())
        cleared["presence"] = ["hana", "pax"]
        # Fresh progress too: presence alone would only flip the
        # presence-stall into a progress-stall (worker alive,
        # work still stuck). A cleared condition means the worker
        # is back AND moving.
        cleared["jobs"] = [dict(self._stall_snapshot()["jobs"][0],
                               claimed_at=10500)]
        live = watchdog.tick(cleared, now=10600)
        self.assertEqual(live, [])
        resolved = istore.auto_resolve_cleared(
            ["presence-stall:pax:7"], live, now=10600)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["status"], "resolved")
        self.assertEqual(resolved[0]["resolved_at"], 10600)
        stored = istore.get_alert("presence-stall:pax:7")
        self.assertEqual(stored["status"], "resolved")

    def test_auto_resolve_leaves_still_live_alerts_open(self):
        watchdog.tick(self._stall_snapshot(), now=10000,
                      emit=lambda a: istore.write_alert(a,
                                                         room="build"))
        live = watchdog.tick(self._stall_snapshot(), now=10600)
        self.assertEqual(len(live), 1)
        resolved = istore.auto_resolve_cleared(
            ["presence-stall:pax:7"], live, now=10600)
        self.assertEqual(resolved, [])
        stored = istore.get_alert("presence-stall:pax:7")
        self.assertEqual(stored["status"], "open")

    def test_auto_resolve_skips_unknown_and_already_resolved(self):
        record = istore.write_alert(self._stall_alert(10000),
                                    room="build")
        istore.resolve_alert(record["id"], now=10100)
        resolved = istore.auto_resolve_cleared(
            [record["id"], "never-existed"], [], now=10200)
        self.assertEqual(resolved, [])


class SparkPolishTest(unittest.TestCase):
    """WDG-012: optional Spark polish pass on alert explanations."""

    class _FakeClient:
        def __init__(self, text=None, error=None):
            self.text = text
            self.error = error
            self.calls = []

        def complete(self, prompt, system=None, lane_feature=None):
            self.calls.append((prompt, lane_feature))
            if self.error is not None:
                raise self.error
            return self.text

    def _stall_snapshot(self):
        return {
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9340}],
            "presence": ["hana"],
            "caps": {"pax": {"caps": "build"}},
        }

    def test_toggle_off_keeps_template_text(self):
        got = watchdog.tick(self._stall_snapshot(), now=10000)
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0]["explanation"].startswith(
            "pax holds claimed job 7"))

    def test_toggle_on_uses_polished_text(self):
        polished = "Pax has gone quiet while holding job 7."
        client = self._FakeClient(text=polished)
        got = watchdog.tick(self._stall_snapshot(), now=10000,
                            polish_client=client)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["explanation"], polished)
        # The suggested fix is an instruction, never polished.
        self.assertIn("lease sweep", got[0]["suggested_fix"])
        self.assertEqual(len(client.calls), 1)
        self.assertEqual(client.calls[0][1], "watchdog")
        self.assertIn("job 7", client.calls[0][0])

    def test_emitted_alert_carries_polished_text(self):
        client = self._FakeClient(text="Polished explanation.")
        seen = []
        got = watchdog.tick(self._stall_snapshot(), now=10000,
                            emit=seen.append, polish_client=client)
        self.assertEqual(seen, got)
        self.assertEqual(seen[0]["explanation"],
                         "Polished explanation.")

    def test_spark_failure_keeps_template_text(self):
        client = self._FakeClient(error=RuntimeError("spark down"))
        got = watchdog.tick(self._stall_snapshot(), now=10000,
                            polish_client=client)
        self.assertEqual(len(got), 1)
        self.assertTrue(got[0]["explanation"].startswith(
            "pax holds claimed job 7"))

    def test_empty_spark_reply_keeps_template_text(self):
        for empty in ("", "   "):
            client = self._FakeClient(text=empty)
            got = watchdog.tick(self._stall_snapshot(), now=10000,
                                polish_client=client)
            self.assertTrue(got[0]["explanation"].startswith(
                "pax holds claimed job 7"))

    def test_quiet_snapshot_with_polish_client_calls_nothing(self):
        client = self._FakeClient(text="never used")
        got = watchdog.tick({}, now=1000, polish_client=client)
        self.assertEqual(got, [])
        self.assertEqual(client.calls, [])

    def test_polish_helper_toggle_off_and_failure(self):
        from intel import explanations
        template = "pax holds claimed job 7."
        self.assertEqual(
            explanations.polish_explanation(template), template)
        self.assertEqual(
            explanations.polish_explanation(
                template, self._FakeClient(
                    error=RuntimeError("down"))),
            template)
        self.assertEqual(
            explanations.polish_explanation(
                template, self._FakeClient(text="  ")),
            template)


class AnnounceTest(unittest.TestCase):
    """WDG-015: new critical alerts announce once, in frozen
    format; warnings and info records stay silent. No test
    here posts anywhere: the announce sink is a list, and
    the default (no callback) announces nothing by design —
    Dale's posting rule gates the real bus post to a caller
    that explicitly opts in."""

    def _stall_snapshot(self):
        return {
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9340}],
            "presence": ["hana"],
            "caps": {"pax": {"caps": "build"}},
        }

    def _lease_snapshot(self):
        return {"jobs": [{"id": "9", "title": "lease job",
                          "status": "claimed", "claim": "pax",
                          "claimed_at": 9900,
                          "lease_until": 10240}],
                "presence": ["pax"],
                "caps": {"pax": {"caps": "build"}}}

    def _silent_snapshot(self):
        return {"jobs": [{"id": "7", "title": "demo job",
                          "status": "claimed", "claim": "pax",
                          "claimed_at": 9900}],
                "presence": ["pax"],
                "caps": {"pax": {"caps": "build"}},
                "messages": [{"nick": "pax", "text": "old",
                              "ts": 1000}]}

    def test_critical_fixture_yields_exactly_one_announcement(self):
        # WDG-015 acceptance: one critical alert -> one line,
        # frozen format ALERT:<id> <kind>: <explanation>,
        # naming the same id the store files the record under
        # (the dedupe_key here, since tick yields detector
        # dicts, not stored records).
        lines = []
        got = watchdog.tick(self._stall_snapshot(), now=10000,
                            announce=lines.append)
        self.assertEqual(len(got), 1)
        self.assertEqual(len(lines), 1)
        line = lines[0]
        self.assertTrue(line.startswith(
            "ALERT:presence-stall:pax:7 presence-stall: "))
        self.assertIn("pax", line)
        self.assertNotIn("\n", line)

    def test_warning_fixture_yields_no_announcement(self):
        # Lease-risk is a warning: it accumulates for the
        # brief/dashboard and never reaches the announce sink.
        lines = []
        got = watchdog.tick(self._lease_snapshot(), now=10000,
                            announce=lines.append)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["severity"], "warning")
        self.assertEqual(lines, [])

    def test_info_record_yields_no_announcement(self):
        # Silent-room is info only: WDG-015 never announces it.
        lines = []
        got = watchdog.tick(self._silent_snapshot(), now=10000,
                            announce=lines.append)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["severity"], "info")
        self.assertEqual(lines, [])

    def test_no_callback_means_held_not_posted(self):
        # Default tick announces nothing: lines exist only
        # through format_announcement()/announcements_for(),
        # held for a caller under Dale's posting rule.
        got = watchdog.tick(self._stall_snapshot(), now=10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(
            watchdog.announcements_for(got),
            [watchdog.format_announcement(got[0])])
        self.assertTrue(
            watchdog.announcements_for(got)[0].startswith(
                "ALERT:presence-stall:pax:7 "))

    def test_format_gate_rejects_warning_info_and_bad_input(self):
        warning = {"severity": "warning", "id": "w",
                   "kind": "lease-risk", "explanation": "x"}
        info = {"severity": "info", "id": "i",
                "kind": "silent-room", "explanation": "x"}
        no_id = {"severity": "critical", "kind": "stall",
                 "explanation": "x"}
        self.assertIsNone(watchdog.format_announcement(warning))
        self.assertIsNone(watchdog.format_announcement(info))
        self.assertIsNone(watchdog.format_announcement(no_id))
        self.assertIsNone(watchdog.format_announcement(None))
        self.assertEqual(watchdog.announcements_for([warning, info]),
                         [])
        self.assertEqual(watchdog.announcements_for(None), [])

    def test_announcement_flattens_multiline_explanation(self):
        alert = {"severity": "critical", "id": "c1",
                 "kind": "presence-stall",
                 "explanation": "line one\nline two"}
        line = watchdog.format_announcement(alert)
        self.assertEqual(
            line, "ALERT:c1 presence-stall: line one line two")

    def test_cli_announce_prints_line_only_with_flag(self):
        path = tempfile.NamedTemporaryFile(
            "w", suffix=".json", delete=False)
        json.dump(self._stall_snapshot(), path)
        path.close()
        self.addCleanup(os.unlink, path.name)
        out = io.StringIO()
        with redirect_stdout(out):
            code = watchdog.main(["--once", "--snapshot", path.name])
        self.assertEqual(code, 0)
        self.assertNotIn("ALERT:", out.getvalue())
        out = io.StringIO()
        with redirect_stdout(out):
            code = watchdog.main(["--once", "--snapshot", path.name,
                                  "--announce"])
        self.assertEqual(code, 0)
        self.assertIn("ALERT:presence-stall:pax:7 ", out.getvalue())


class SelfBeatTest(unittest.TestCase):
    def test_beat_called_once_per_tick_even_when_quiet(self):
        # WDG-016 acceptance, loop half: a quiet tick still
        # proves the watchdog alive — the beat fires with the
        # tick timestamp, not only when an alert fires.
        beats = []
        got = watchdog.tick({}, now=1000, beat=beats.append)
        self.assertEqual(got, [])
        self.assertEqual(beats, [1000])

    def test_beat_called_once_when_alerts_fire(self):
        snapshot = {
            "jobs": [{"id": "7", "title": "stuck", "status": "claimed",
                      "claim": "pax", "claimed_at": 100}],
            "presence": [],
            "caps": {"pax": {"caps": "build"}},
        }
        beats = []
        got = watchdog.tick(snapshot, now=10000, beat=beats.append)
        self.assertTrue(got)
        self.assertEqual(beats, [10000])

    def test_no_beat_callback_writes_nothing_and_raises_nothing(self):
        self.assertEqual(watchdog.tick({}, now=1000), [])

    def test_failing_beat_never_fails_the_tick_or_hides_alerts(self):
        # The beat is best-effort liveness: a dead store must not
        # blind the detectors, and the missed beat is itself the
        # signal the dashboard renders as stale.
        def _boom(ts):
            raise RuntimeError("store down")

        snapshot = {
            "jobs": [{"id": "7", "title": "stuck", "status": "claimed",
                      "claim": "pax", "claimed_at": 100}],
            "presence": [],
            "caps": {"pax": {"caps": "build"}},
        }
        got = watchdog.tick(snapshot, now=10000, beat=_boom)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "presence-stall")


class SelfBeatIntegrationTest(RelayTestCase):
    def test_tick_with_store_beat_writes_the_beat_key(self):
        # WDG-016 acceptance, end to end in tests: tick wired to
        # the store beat leaves muse-bus:intel:wd:beat readable
        # with age zero at the tick time — the key the dashboard
        # (bus.html, DSH-015) reads for its alive/stale render.
        now = int(self.fake.now())
        watchdog.tick({}, now=now, beat=istore.wd_self_beat)
        self.assertEqual(istore.wd_self_beat_age(now), 0)
        self.assertEqual(
            json.loads(self.fake.api_get(
                "get/muse-bus:intel:wd:beat"))["result"],
            json.dumps({"ts": now}, sort_keys=True))


class TickBudgetTest(unittest.TestCase):
    def _busy_snapshot(self, message_count, last_ts):
        # Oldest first (ingest order): 1500 messages whose newest
        # carries last_ts, plus one claimed job so the silent-room
        # detector has something to measure silence against.
        messages = [{"nick": "pax", "text": f"note {i}",
                     "ts": last_ts - (message_count - 1 - i)}
                    for i in range(message_count)]
        return {"jobs": [{"id": "1", "title": "claimed job",
                          "status": "claimed", "claim": "pax",
                          "claimed_at": 1000}],
                "messages": messages}

    def test_paginate_yields_page_sized_chunks_oldest_first(self):
        # digest.py's PAGE shape: full pages, then a short final
        # page, order preserved, nothing lost or duplicated.
        pages = list(watchdog.paginate(range(2500), 1000))
        self.assertEqual([len(p) for p in pages], [1000, 1000, 500])
        self.assertEqual([n for p in pages for n in p],
                         list(range(2500)))

    def test_paginate_rejects_non_positive_page_size(self):
        for bad in (0, -100):
            with self.assertRaises(ValueError):
                list(watchdog.paginate(range(10), bad))

    def test_cap_keeps_newest_and_reports_the_drop(self):
        # WDG-017 acceptance, window half: the cap keeps the
        # newest TICK_MAX_MESSAGES and names the drop count in
        # the tick_window record, brief.py source_window style.
        snapshot = self._busy_snapshot(1500, 1000)
        capped = watchdog.cap_tick_snapshot(snapshot)
        window = capped["tick_window"]
        self.assertEqual(window["messages_kept"], 1000)
        self.assertEqual(window["messages_dropped"], 500)
        self.assertEqual(capped["messages"][0]["text"], "note 500")
        self.assertEqual(capped["messages"][-1]["text"], "note 1499")
        # Jobs, presence, caps pass through: the cap is a message
        # window cap, never a job cap.
        self.assertEqual(capped["jobs"], snapshot["jobs"])

    def test_cap_under_the_limit_passes_through_unchanged(self):
        snapshot = self._busy_snapshot(50, 1000)
        capped = watchdog.cap_tick_snapshot(snapshot)
        self.assertEqual(capped["tick_window"]["messages_dropped"], 0)
        self.assertEqual(capped["messages"], snapshot["messages"])

    def test_cap_twice_accumulates_the_drop_count(self):
        # brief.py BRF-024's lesson, same trap here: a second cap
        # must not reset the first cap's drop count to zero.
        once = watchdog.cap_tick_snapshot(self._busy_snapshot(1500,
                                                               1000))
        twice = watchdog.cap_tick_snapshot(once, max_messages=100)
        self.assertEqual(twice["tick_window"]["messages_dropped"],
                         500 + 900)
        self.assertEqual(twice["tick_window"]["messages_kept"], 100)

    def test_1500_message_tick_completes_with_correct_verdict(self):
        # WDG-017 acceptance, tick half: a 1,500-message fixture
        # tick completes, and the cap cannot change the verdict —
        # the silent-room detector reads the newest message,
        # which always survives the cap. Old last message:
        # silence record fires with the true age.
        got = watchdog.tick(self._busy_snapshot(1500, 1000),
                            now=10000)
        records = [r for r in got if r["kind"] == "silent-room"]
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["last_message_age_seconds"], 9000)
        # Fresh last message: no record, even under the cap.
        got = watchdog.tick(self._busy_snapshot(1500, 8200),
                            now=10000)
        self.assertEqual([r for r in got if r["kind"] == "silent-room"],
                         [])

    def test_tick_cap_never_hides_a_job_detector_verdict(self):
        # Jobs are never capped: a stalled claimed job still
        # alerts when the message history is 1,500 deep.
        snapshot = self._busy_snapshot(1500, 8200)
        snapshot["jobs"] = [{"id": "7", "title": "stuck",
                             "status": "claimed", "claim": "pax",
                             "claimed_at": 100}]
        snapshot["presence"] = []
        snapshot["caps"] = {"pax": {"caps": "build"}}
        got = watchdog.tick(snapshot, now=10000)
        stalls = [r for r in got if r["kind"] == "presence-stall"]
        self.assertEqual(len(stalls), 1)
        self.assertEqual(stalls[0]["job"], "7")

    def test_cli_once_on_1500_message_snapshot_exits_zero(self):
        # End to end through the CLI: --once on the big fixture
        # exits 0, so the guard holds on the real entry point too.
        snapshot = self._busy_snapshot(1500, 8200)
        with tempfile.NamedTemporaryFile("w", suffix=".json",
                                         delete=False) as handle:
            json.dump(snapshot, handle)
            path = handle.name
        try:
            with redirect_stdout(io.StringIO()):
                code = watchdog.main(["--once", "--snapshot", path])
            self.assertEqual(code, 0)
        finally:
            os.unlink(path)


class EnvOverrideTest(unittest.TestCase):
    # WDG-018: every threshold is env-overridable, and changing
    # the environment changes detector behavior, not just a
    # constant on a page. Consumers read thresholds attributes
    # at call time, so reloading the module (the documented
    # pick-up mechanism for a long-running process) is enough;
    # each test restores the environment and reloads back to
    # defaults so no other test ever sees an overridden value.
    def _reload_with_env(self, env):
        saved = {}
        for name in env:
            saved[name] = os.environ.get(name)
            os.environ[name] = env[name]
        importlib.reload(thresholds)
        return saved

    def _restore(self, saved):
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        importlib.reload(thresholds)

    def test_defaults_unchanged_without_env(self):
        # The documented FND-030 defaults survive the WDG-018
        # rewrite untouched when no WATCHDOG_* variable is set.
        self.assertEqual(thresholds.STALL_MINUTES, 10)
        self.assertEqual(thresholds.PROGRESS_STALL_MINUTES, 10)
        self.assertEqual(thresholds.LEASE_RISK_WINDOW_MINUTES, 5)
        self.assertEqual(thresholds.LEASE_RISK_QUIET_MINUTES, 2)
        self.assertEqual(thresholds.ALERT_DEDUPE_COOLDOWN_MINUTES, 30)
        self.assertEqual(thresholds.SILENT_ROOM_MINUTES, 60)
        self.assertEqual(thresholds.WATCHDOG_BEAT_TTL_SECONDS, 300)
        self.assertEqual(thresholds.TICK_PAGE_SIZE, 1000)
        self.assertEqual(thresholds.TICK_MAX_MESSAGES, 1000)

    def test_env_override_changes_presence_stall_behavior(self):
        # WDG-018 acceptance, stall half: a job silent for 30
        # minutes alerts under the 10-minute default but goes
        # quiet when WATCHDOG_STALL_MINUTES is raised to 60,
        # and alerts again once the default is restored.
        snapshot = {"jobs": [{"id": "9", "title": "stuck",
                              "status": "claimed", "claim": "pax",
                              "claimed_at": 100}],
                    "presence": [],
                    "caps": {"pax": {"caps": "build"}}}
        stalls = [r for r in watchdog.tick(snapshot, now=1900)
                  if r["kind"] == "presence-stall"]
        self.assertEqual(len(stalls), 1)
        saved = self._reload_with_env(
            {"WATCHDOG_STALL_MINUTES": "60"})
        try:
            self.assertEqual(thresholds.STALL_MINUTES, 60)
            stalls = [r for r in watchdog.tick(snapshot, now=1900)
                      if r["kind"] == "presence-stall"]
            self.assertEqual(stalls, [])
        finally:
            self._restore(saved)
        self.assertEqual(thresholds.STALL_MINUTES, 10)
        stalls = [r for r in watchdog.tick(snapshot, now=1900)
                  if r["kind"] == "presence-stall"]
        self.assertEqual(len(stalls), 1)

    def test_env_override_changes_silent_room_behavior(self):
        # WDG-018 acceptance, silent-room half: a room silent
        # for 70 minutes records under the 60-minute default
        # but stays quiet with WATCHDOG_SILENT_ROOM_MINUTES=120.
        snapshot = {"jobs": [{"id": "1", "title": "claimed job",
                              "status": "claimed", "claim": "pax",
                              "claimed_at": 1000}],
                    "messages": [{"nick": "pax", "text": "note",
                                  "ts": 1000}]}
        records = [r for r in watchdog.tick(snapshot, now=5200)
                   if r["kind"] == "silent-room"]
        self.assertEqual(len(records), 1)
        saved = self._reload_with_env(
            {"WATCHDOG_SILENT_ROOM_MINUTES": "120"})
        try:
            self.assertEqual(thresholds.SILENT_ROOM_MINUTES, 120)
            records = [r for r in watchdog.tick(snapshot, now=5200)
                       if r["kind"] == "silent-room"]
            self.assertEqual(records, [])
        finally:
            self._restore(saved)

    def test_env_override_changes_tick_cap_behavior(self):
        # The tick budget guard honors the environment too: a
        # 1,500-message snapshot keeps 100 messages, not 1000,
        # with WATCHDOG_TICK_MAX_MESSAGES=100.
        snapshot = {"jobs": [], "messages": [
            {"nick": "pax", "text": f"note {i}", "ts": i}
            for i in range(1500)]}
        saved = self._reload_with_env(
            {"WATCHDOG_TICK_MAX_MESSAGES": "100"})
        try:
            capped = watchdog.cap_tick_snapshot(snapshot)
            self.assertEqual(
                capped["tick_window"]["messages_kept"], 100)
            self.assertEqual(
                capped["tick_window"]["messages_dropped"], 1400)
        finally:
            self._restore(saved)

    def test_bad_env_values_fall_back_to_defaults(self):
        # A typo in the environment must never crash the
        # watchdog or invent a threshold: blank, unparseable,
        # and below-minimum values all yield the default.
        cases = [("WATCHDOG_STALL_MINUTES", "", 10),
                 ("WATCHDOG_STALL_MINUTES", "banana", 10),
                 ("WATCHDOG_STALL_MINUTES", "-5", 10),
                 ("WATCHDOG_TICK_PAGE_SIZE", "0", 1000),
                 ("WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES", "45",
                  45)]
        for name, value, expected in cases:
            saved = self._reload_with_env({name: value})
            try:
                if name == "WATCHDOG_STALL_MINUTES":
                    self.assertEqual(thresholds.STALL_MINUTES,
                                     expected)
                elif name == "WATCHDOG_TICK_PAGE_SIZE":
                    self.assertEqual(thresholds.TICK_PAGE_SIZE,
                                     expected)
                else:
                    self.assertEqual(
                        thresholds.ALERT_DEDUPE_COOLDOWN_MINUTES,
                        expected)
            finally:
                self._restore(saved)


class DetectorCoverageTest(unittest.TestCase):
    """WDG-019: every detector has a positive and a negative case.

    The per-detector classes above carry the detailed cases;
    this class is the single checklist WDG-019's acceptance
    names: one positive and one negative per detector, run
    against the detector functions directly, plus a registry
    check that tick() actually runs all ten (a detector
    tested in isolation but never registered detects nothing).
    """

    NOW = 10000

    def test_registry_runs_all_nine_detectors(self):
        self.assertEqual(len(watchdog.DETECTORS), 10)
        positives = [
            ({"jobs": [{"id": "7", "status": "claimed", "claim": "pax",
                        "claimed_at": 9340}],
              "presence": ["hana"], "caps": {"pax": {}}},
             "presence-stall"),
            ({"jobs": [{"id": "7", "status": "claimed", "claim": "pax",
                        "claimed_at": 9000, "last_progress": 9340}],
              "presence": ["pax"], "caps": {"pax": {}}},
             "progress-stall"),
            ({"jobs": [{"id": "7", "status": "claimed", "claim": "pax",
                        "lease_until": 10200}]}, "lease-risk"),
            ({"jobs": [{"id": "1", "status": "open", "deps": "2"},
                      {"id": "2", "status": "blocked",
                       "note": "waiting on vendor"}]}, "dead-dep"),
            ({"jobs": [{"id": "1", "status": "open", "deps": "9"}]},
             "missing-dep"),
            ({"jobs": [{"id": "1", "status": "claimed", "files": "a.py"},
                      {"id": "2", "status": "claimed",
                       "files": "a.py"}]}, "file-collision"),
            ({"jobs": [{"id": "1", "status": "open", "attempts": 2,
                        "max_attempts": 3}]}, "attempt-warning"),
            ({"jobs": [{"id": "1", "status": "claimed"}],
              "messages": [{"nick": "pax", "text": "hi", "ts": 6000}]},
             "silent-room"),
            ({"jobs": [{"id": "1", "status": "open"}],
              "messages": ["worker: REJECTED:1 BAD "
                           "signed_by=overseer rejected_by=worker"]},
             "rejected-dispatch"),
            ({"jobs": [], "messages": [], "presence": [],
              "caps": {},
              "budgets": [{"lane": "spark", "spent": 80,
                           "cap": 100}]},
             "budget-warning"),
        ]
        seen = set()
        for snapshot, _kind in positives:
            for alert in watchdog.tick(snapshot, now=self.NOW):
                seen.add(alert["kind"])
        for _snapshot, kind in positives:
            self.assertIn(kind, seen)

    def test_presence_stall_positive_and_negative(self):
        stalled = {"jobs": [{"id": "7", "status": "claimed",
                             "claim": "pax", "claimed_at": 9340}],
                   "presence": ["hana"], "caps": {"pax": {}}}
        self.assertEqual(len(watchdog.detect_presence_stall(
            stalled, self.NOW)), 1)
        present = dict(stalled, presence=["pax"])
        self.assertEqual(watchdog.detect_presence_stall(
            present, self.NOW), [])

    def test_progress_stall_positive_and_negative(self):
        stuck = {"jobs": [{"id": "7", "status": "claimed",
                           "claim": "pax", "claimed_at": 9000,
                           "last_progress": 9340}],
                 "presence": ["pax"], "caps": {"pax": {}}}
        self.assertEqual(len(watchdog.detect_progress_stall(
            stuck, self.NOW)), 1)
        fresh = {"jobs": [{"id": "7", "status": "claimed",
                           "claim": "pax", "claimed_at": 9000,
                           "last_progress": 9900}],
                 "presence": ["pax"], "caps": {"pax": {}}}
        self.assertEqual(watchdog.detect_progress_stall(
            fresh, self.NOW), [])

    def test_lease_risk_positive_and_negative(self):
        at_risk = {"jobs": [{"id": "7", "status": "claimed",
                             "claim": "pax", "lease_until": 10200}]}
        self.assertEqual(len(watchdog.detect_lease_risk(
            at_risk, self.NOW)), 1)
        renewed = {"jobs": [{"id": "7", "status": "claimed",
                             "claim": "pax", "lease_until": 10200,
                             "heartbeat_at": 9950}]}
        self.assertEqual(watchdog.detect_lease_risk(
            renewed, self.NOW), [])

    def test_dead_dep_positive_and_negative(self):
        dead = {"jobs": [{"id": "1", "status": "open", "deps": "2"},
                         {"id": "2", "status": "blocked",
                          "note": "waiting on vendor"}]}
        got = watchdog.detect_dead_dep(dead, self.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "dead-dep")
        live = {"jobs": [{"id": "1", "status": "open", "deps": "2"},
                         {"id": "2", "status": "open"}]}
        self.assertEqual(watchdog.detect_dead_dep(live, self.NOW), [])

    def test_missing_dep_positive_and_negative(self):
        dangling = {"jobs": [{"id": "1", "status": "open",
                              "deps": "9"}]}
        got = watchdog.detect_missing_dep(dangling, self.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "missing-dep")
        found = {"jobs": [{"id": "1", "status": "open", "deps": "2"},
                          {"id": "2", "status": "open"}]}
        self.assertEqual(watchdog.detect_missing_dep(
            found, self.NOW), [])

    def test_file_collision_positive_and_negative(self):
        clash = {"jobs": [{"id": "1", "status": "claimed",
                           "files": "a.py"},
                          {"id": "2", "status": "claimed",
                           "files": "a.py"}]}
        got = watchdog.detect_file_collision(clash, self.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "file-collision")
        disjoint = {"jobs": [{"id": "1", "status": "claimed",
                              "files": "a.py"},
                             {"id": "2", "status": "claimed",
                              "files": "b.py"}]}
        self.assertEqual(watchdog.detect_file_collision(
            disjoint, self.NOW), [])

    def test_attempt_exhaustion_positive_and_negative(self):
        warning = {"jobs": [{"id": "1", "status": "open", "attempts": 2,
                             "max_attempts": 3}]}
        got = watchdog.detect_attempt_exhaustion(warning, self.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "attempt-warning")
        spent = {"jobs": [{"id": "1", "status": "open", "attempts": 3,
                           "max_attempts": 3}]}
        got = watchdog.detect_attempt_exhaustion(spent, self.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "attempt-exhaustion")
        healthy = {"jobs": [{"id": "1", "status": "open", "attempts": 0,
                             "max_attempts": 3}]}
        self.assertEqual(watchdog.detect_attempt_exhaustion(
            healthy, self.NOW), [])

    def test_silent_room_positive_and_negative(self):
        quiet = {"jobs": [{"id": "1", "status": "claimed"}],
                 "messages": [{"nick": "pax", "text": "hi",
                               "ts": 6000}]}
        got = watchdog.detect_silent_room(quiet, self.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "silent-room")
        self.assertEqual(got[0]["severity"], "info")
        noisy = {"jobs": [{"id": "1", "status": "claimed"}],
                 "messages": [{"nick": "pax", "text": "hi",
                               "ts": 9900}]}
        self.assertEqual(watchdog.detect_silent_room(
            noisy, self.NOW), [])

    def test_rejected_dispatch_positive_and_negative(self):
        refused = {"jobs": [{"id": "1", "status": "open"}],
                   "messages": ["worker: REJECTED:1 BAD "
                                "signed_by=overseer "
                                "rejected_by=worker"]}
        got = watchdog.detect_rejected_dispatch(refused, self.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "rejected-dispatch")
        self.assertEqual(got[0]["severity"], "critical")
        self.assertEqual(got[0]["dedupe_key"],
                         "rejected-dispatch:1:BAD")
        self.assertEqual(got[0]["job"], "1")
        self.assertEqual(got[0]["verdict"], "BAD")
        clean = {"jobs": [{"id": "1", "status": "open"}],
                 "messages": [{"nick": "pax", "text": "all quiet"}]}
        self.assertEqual(watchdog.detect_rejected_dispatch(
            clean, self.NOW), [])
        malformed = {"messages": [
            "worker: REJECTED:abc BAD",
            "worker: REJECTED:2 OK signed_by=x rejected_by=y",
            "worker: REJECTED"]}
        self.assertEqual(watchdog.detect_rejected_dispatch(
            malformed, self.NOW), [])

    def test_budget_warning_positive_and_negative(self):
        warned = {"jobs": [], "messages": [], "presence": [],
                  "caps": {},
                  "budgets": [{"lane": "spark", "spent": 80,
                               "cap": 100}]}
        got = watchdog.detect_budget_warning(warned, self.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "budget-warning")
        self.assertEqual(got[0]["severity"], "warning")
        self.assertEqual(got[0]["lane"], "spark")
        self.assertEqual(got[0]["dedupe_key"],
                         "budget-warning:spark")
        under = {"budgets": [{"lane": "spark", "spent": 70,
                              "cap": 100}]}
        self.assertEqual(watchdog.detect_budget_warning(
            under, self.NOW), [])
        capped = {"budgets": [{"lane": "spark", "spent": 100,
                                "cap": 100}]}
        self.assertEqual(watchdog.detect_budget_warning(
            capped, self.NOW), [])


class WalkOnTrackingTest(unittest.TestCase):
    """WDG-025: unknown claimer yields a tracking record, and
    stall detection for registered workers still works."""

    NOW = 10000

    def _snapshot(self, **overrides):
        snapshot = {
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "walkon",
                      "claimed_at": 9340}],
            "presence": ["hana"],
            "caps": {"hana": {}},
        }
        snapshot.update(overrides)
        return snapshot

    def test_unknown_claimer_yields_tracking_record(self):
        # WDG-025 acceptance: the fixture yields a tracking
        # record naming the nick, the job, and the age (660s).
        got = watchdog.detect_walk_on_workers(
            self._snapshot(), self.NOW)
        self.assertEqual(len(got), 1)
        record = got[0]
        self.assertEqual(record["kind"], "walk-on-worker")
        self.assertEqual(record["nick"], "walkon")
        self.assertEqual(record["job"], "7")
        self.assertEqual(record["last_progress_age_seconds"], 660)
        self.assertEqual(record["last_progress_age_minutes"], 11)
        self.assertEqual(record["tracked_from"], "jobs")

    def test_tracking_is_not_an_alert(self):
        # The record rides the tracking function, never tick:
        # the walk-on fixture still yields zero alerts, and
        # the function is not a registered detector.
        self.assertEqual(watchdog.tick(self._snapshot(),
                                       now=self.NOW), [])
        self.assertNotIn(watchdog.detect_walk_on_workers,
                         watchdog.DETECTORS)

    def test_registered_claimer_is_not_tracked(self):
        snapshot = self._snapshot(caps={"walkon": {}, "hana": {}})
        self.assertEqual(watchdog.detect_walk_on_workers(
            snapshot, self.NOW), [])

    def test_open_job_is_not_tracked(self):
        snapshot = self._snapshot()
        snapshot["jobs"][0]["status"] = "open"
        self.assertEqual(watchdog.detect_walk_on_workers(
            snapshot, self.NOW), [])

    def test_present_walk_on_is_still_tracked(self):
        # Tracking comes from jobs data alone: presence does
        # not hide a walk-on worker.
        snapshot = self._snapshot(presence=["walkon", "hana"])
        got = watchdog.detect_walk_on_workers(snapshot, self.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["nick"], "walkon")

    def test_no_timestamp_never_invents_an_age(self):
        snapshot = self._snapshot()
        del snapshot["jobs"][0]["claimed_at"]
        got = watchdog.detect_walk_on_workers(snapshot, self.NOW)
        self.assertEqual(len(got), 1)
        self.assertIsNone(got[0]["last_progress_age_seconds"])
        self.assertIsNone(got[0]["last_progress_age_minutes"])

    def test_malformed_sections_yield_no_crash(self):
        self.assertEqual(watchdog.detect_walk_on_workers(
            {"jobs": "not-a-list", "caps": "not-a-dict"},
            self.NOW), [])
        self.assertEqual(watchdog.detect_walk_on_workers(
            None, self.NOW), [])

    def test_stall_detection_still_works_alongside_tracking(self):
        # A registered worker's stall still alerts through
        # tick while the walk-on job is tracked separately.
        snapshot = self._snapshot()
        snapshot["jobs"].append(
            {"id": "8", "title": "registered job",
             "status": "claimed", "claim": "pax",
             "claimed_at": 9340})
        snapshot["caps"] = {"pax": {}, "hana": {}}
        got = watchdog.tick(snapshot, now=self.NOW)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "presence-stall")
        self.assertEqual(got[0]["nick"], "pax")
        tracked = watchdog.detect_walk_on_workers(
            snapshot, self.NOW)
        self.assertEqual(len(tracked), 1)
        self.assertEqual(tracked[0]["nick"], "walkon")


class SeverityMappingTest(unittest.TestCase):
    """WDG-024: every detector kind maps to exactly one severity,
    and every detector actually emits the severity the table
    names. The table is published in intel/README.md; this test
    is what keeps the code honest against it."""

    NOW = 10000

    # One positive fixture per detector kind, mirroring
    # DetectorCoverageTest's registry fixtures, plus the second
    # attempt kind (spent budget) that the registry fixture does
    # not cover.
    POSITIVES = [
        ({"jobs": [{"id": "7", "status": "claimed", "claim": "pax",
                    "claimed_at": 9340}],
          "presence": ["hana"], "caps": {"pax": {}}},
         "presence-stall"),
        ({"jobs": [{"id": "7", "status": "claimed", "claim": "pax",
                    "claimed_at": 9000, "last_progress": 9340}],
          "presence": ["pax"], "caps": {"pax": {}}},
         "progress-stall"),
        ({"jobs": [{"id": "7", "status": "claimed", "claim": "pax",
                    "lease_until": 10200}]}, "lease-risk"),
        ({"jobs": [{"id": "1", "status": "open", "deps": "2"},
                  {"id": "2", "status": "blocked",
                   "note": "waiting on vendor"}]}, "dead-dep"),
        ({"jobs": [{"id": "1", "status": "open", "deps": "9"}]},
         "missing-dep"),
        ({"jobs": [{"id": "1", "status": "claimed", "files": "a.py"},
                  {"id": "2", "status": "claimed",
                   "files": "a.py"}]}, "file-collision"),
        ({"jobs": [{"id": "1", "status": "open", "attempts": 2,
                    "max_attempts": 3}]}, "attempt-warning"),
        ({"jobs": [{"id": "1", "status": "open", "attempts": 3,
                    "max_attempts": 3}]}, "attempt-exhaustion"),
        ({"jobs": [{"id": "1", "status": "claimed"}],
          "messages": [{"nick": "pax", "text": "hi", "ts": 6000}]},
         "silent-room"),
        ({"jobs": [{"id": "1", "status": "open"}],
          "messages": ["worker: REJECTED:1 BAD "
                       "signed_by=overseer rejected_by=worker"]},
         "rejected-dispatch"),
        # OS-085: a lane past its warning threshold warns; the
        # snapshot carries budgets in the OS-079 entry shape.
        ({"jobs": [], "messages": [], "presence": [], "caps": {},
          "budgets": [{"lane": "spark", "spent": 80,
                       "cap": 100}]},
         "budget-warning"),
    ]

    def test_table_covers_every_detector_kind(self):
        emitted = set()
        for snapshot, _kind in self.POSITIVES:
            for alert in watchdog.tick(snapshot, now=self.NOW):
                emitted.add(alert["kind"])
        self.assertEqual(set(watchdog.SEVERITY_BY_KIND), emitted)

    def test_table_values_are_valid_severities(self):
        for kind, severity in watchdog.SEVERITY_BY_KIND.items():
            self.assertIn(severity, istore.ALERT_SEVERITIES,
                          f"{kind} maps to invalid severity {severity!r}")

    def test_every_detector_emits_its_table_severity(self):
        for snapshot, kind in self.POSITIVES:
            got = [a for a in watchdog.tick(snapshot, now=self.NOW)
                   if a["kind"] == kind]
            self.assertEqual(len(got), 1, f"{kind} fixture")
            self.assertEqual(got[0]["severity"],
                             watchdog.SEVERITY_BY_KIND[kind])

    def test_mapping_matches_the_lane_plan_rule(self):
        table = watchdog.SEVERITY_BY_KIND
        for kind in ("presence-stall", "progress-stall", "dead-dep",
                     "missing-dep", "file-collision"):
            self.assertEqual(table[kind], "critical")
        for kind in ("lease-risk", "attempt-warning",
                     "budget-warning"):
            self.assertEqual(table[kind], "warning")
        self.assertEqual(table["silent-room"], "info")
        # WDG-008 refinement: a spent attempt budget is a dead
        # job, not a risk, so it is critical, not warning.
        self.assertEqual(table["attempt-exhaustion"], "critical")


class AlertHistoryQueryTest(RelayTestCase):
    """WDG-023: alert history query --room --since --kind.

    Acceptance: a query on a fixture alert set returns exactly
    the filtered subset. The query reads the WDG-023 index that
    write_alert() maintains (score = created_at); raw
    put_alert() records are deliberately not indexed, and the
    query skips index entries whose record is gone rather
    than failing.
    """

    def _alert(self, kind, dedupe, created_at, severity="critical"):
        return {
            "kind": kind, "severity": severity,
            "nick": "pax",
            "explanation": f"{kind} happened",
            "suggested_fix": "look into it",
            "dedupe_key": dedupe, "created_at": created_at,
        }

    def _fixture_set(self):
        istore.write_alert(self._alert("presence-stall",
                                      "presence-stall:pax:7", 10000),
                           room="main")
        istore.write_alert(self._alert("file-collision",
                                      "file-collision:1:2", 11000),
                           room="build")
        istore.write_alert(self._alert("presence-stall",
                                      "presence-stall:hana:9", 12000),
                           room="build")
        istore.write_alert(self._alert("dead-dep",
                                      "dead-dep:3:4", 13000),
                           room="main")

    def test_query_all_returns_everything_oldest_first(self):
        self._fixture_set()
        got = istore.query_alerts()
        self.assertEqual([r["id"] for r in got],
                         ["presence-stall:pax:7", "file-collision:1:2",
                          "presence-stall:hana:9", "dead-dep:3:4"])

    def test_room_filter_returns_exact_subset(self):
        self._fixture_set()
        got = istore.query_alerts(room="build")
        self.assertEqual([r["id"] for r in got],
                         ["file-collision:1:2",
                          "presence-stall:hana:9"])

    def test_kind_filter_returns_exact_subset(self):
        self._fixture_set()
        got = istore.query_alerts(kind="presence-stall")
        self.assertEqual([r["id"] for r in got],
                         ["presence-stall:pax:7",
                          "presence-stall:hana:9"])

    def test_since_filter_keeps_at_or_after(self):
        self._fixture_set()
        got = istore.query_alerts(since=12000)
        self.assertEqual([r["id"] for r in got],
                         ["presence-stall:hana:9", "dead-dep:3:4"])

    def test_combined_filters_intersect(self):
        self._fixture_set()
        got = istore.query_alerts(room="main", since=11000,
                                  kind="dead-dep")
        self.assertEqual([r["id"] for r in got], ["dead-dep:3:4"])

    def test_no_match_returns_empty_not_error(self):
        self._fixture_set()
        self.assertEqual(istore.query_alerts(room="nope"), [])
        self.assertEqual(istore.query_alerts(kind="nope"), [])
        self.assertEqual(istore.query_alerts(since=99999), [])

    def test_dedupe_refire_does_not_duplicate_history(self):
        first = istore.write_alert(
            self._alert("presence-stall", "presence-stall:pax:7", 10000),
            room="main")
        istore.write_alert(
            self._alert("presence-stall", "presence-stall:pax:7", 10600),
            room="main")
        got = istore.query_alerts()
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["id"], first["id"])
        self.assertEqual(got[0]["created_at"], 10000)

    def test_raw_put_alert_is_not_queryable(self):
        istore.put_alert("raw:1", {"id": "raw:1", "kind": "test",
                                   "created_at": 10000})
        self.assertEqual(istore.query_alerts(), [])

    def test_cli_query_filters_match_store(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "intel_cli", "intel.py")
        cli = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cli)
        self._fixture_set()
        out = io.StringIO()
        with redirect_stdout(out):
            rc = cli.main(["alerts", "--room", "build",
                           "--kind", "presence-stall"])
        self.assertEqual(rc, 0)
        got = json.loads(out.getvalue())
        self.assertEqual([r["id"] for r in got],
                         ["presence-stall:hana:9"])


class ClockSkewTest(unittest.TestCase):
    """WDG-026: one resolved "now" per tick; server time wins
    over a skewed wall clock, an explicit now wins over both."""

    def _stall_snapshot(self, server_time="absent"):
        snapshot = {
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9300}],
            "presence": ["hana"],
            "caps": {"pax": {"caps": "build"}},
        }
        if server_time != "absent":
            snapshot["server_time"] = server_time
        return snapshot

    def test_server_time_beats_skewed_wall_clock(self):
        # Wall clock says 9500 (age 200s, fresh); the server
        # says 10000 (age 700s, stalled). The alert must come
        # from the server's clock, with the server's timestamp.
        with mock.patch.object(watchdog.time, "time",
                               return_value=9500):
            got = watchdog.tick(self._stall_snapshot(10000))
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["kind"], "presence-stall")
        self.assertEqual(got[0]["last_progress_age_seconds"], 700)
        self.assertEqual(got[0]["created_at"], 10000)

    def test_explicit_now_beats_server_time(self):
        # An injected clock is never silently overridden by a
        # server_time stamped on the fixture: now=9500 gives
        # age 200s, so no alert, despite server_time=10000.
        got = watchdog.tick(self._stall_snapshot(10000), now=9500)
        self.assertEqual(got, [])

    def test_wall_clock_fallback_when_no_server_time(self):
        # No server_time, no explicit now: the wall clock is
        # the tick clock, and the alert carries its timestamp.
        with mock.patch.object(watchdog.time, "time",
                               return_value=10000):
            got = watchdog.tick(self._stall_snapshot())
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["last_progress_age_seconds"], 700)
        self.assertEqual(got[0]["created_at"], 10000)

    def test_malformed_server_time_falls_back_to_wall_clock(self):
        # A non-numeric server_time (or a bool) is treated as
        # absent, never as zero: the wall clock decides, and
        # the tick neither crashes nor invents an epoch.
        for bad in ("not-a-time", True):
            with mock.patch.object(watchdog.time, "time",
                                   return_value=10000):
                got = watchdog.tick(self._stall_snapshot(bad))
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0]["created_at"], 10000)

    def test_string_and_time_pair_server_time_forms(self):
        # Redis-flavoured shapes both parse: a numeric string
        # (hash/JSON form) and TIME's [seconds, microseconds]
        # pair (sub-second part dropped; ages are whole secs).
        for form in ("10000", [10000, 500000]):
            with mock.patch.object(watchdog.time, "time",
                                   return_value=9500):
                got = watchdog.tick(self._stall_snapshot(form))
            self.assertEqual(len(got), 1)
            self.assertEqual(got[0]["created_at"], 10000)

    def test_resolve_tick_now_reports_its_source(self):
        self.assertEqual(watchdog.resolve_tick_now({}, now=123),
                         (123, "explicit"))
        self.assertEqual(
            watchdog.resolve_tick_now({"server_time": 10000}),
            (10000, "server_time"))
        with mock.patch.object(watchdog.time, "time",
                               return_value=9500):
            self.assertEqual(watchdog.resolve_tick_now({}),
                             (9500, "wall_clock"))

    def test_detector_ages_use_injected_clock_not_wall_clock(self):
        # Acceptance half: ages in tests use the injected
        # clock. The detector takes now as an argument and
        # never reads the wall clock, so a wildly skewed
        # wall clock cannot change its age.
        with mock.patch.object(watchdog.time, "time",
                               return_value=99999):
            got = watchdog.detect_presence_stall(
                self._stall_snapshot(), 10000)
        self.assertEqual(len(got), 1)
        self.assertEqual(got[0]["last_progress_age_seconds"], 700)


class WatchdogStatusLineTest(RelayTestCase):
    """WDG-028: watchdog status line for the morning brief.

    Acceptance: a brief on the stall fixture includes watchdog
    counts matching the alert store. The status record is built
    from the queried alert store (not from a second count), it
    round-trips through its own key, and the template brief
    renders its line at the head of Watch items.
    """

    def _stall_snapshot(self):
        return {
            "jobs": [{"id": "7", "title": "demo job",
                      "status": "claimed", "claim": "pax",
                      "claimed_at": 9340}],
            "presence": ["hana"],
            "caps": {"pax": {"caps": "build"}},
        }

    def _write(self, alert, room="build"):
        return istore.write_alert(alert, room=room)

    def test_stall_fixture_counts_match_alert_store(self):
        written = []
        got = watchdog.tick(
            self._stall_snapshot(), now=10000,
            emit=lambda a: written.append(
                istore.write_alert(a, room="build")))
        self.assertEqual(len(got), 1)
        self.assertEqual(len(written), 1)
        stored = istore.query_alerts(room="build")
        self.assertEqual(len(stored), 1)
        self.assertEqual(stored[0]["id"], written[0]["id"])
        status = istore.build_watchdog_status(stored, room="build",
                                              ts=10000)
        self.assertEqual(status["counts"],
                         {"critical": 1, "warning": 0, "info": 0})
        self.assertEqual(status["open"], 1)
        self.assertEqual(status["resolved"], 0)
        self.assertEqual(status["total"], 1)
        self.assertEqual(status["top_alert"], written[0]["id"])
        self.assertEqual(status["line"],
                         "Watchdog: 1 critical, 0 warning, 0 info "
                         "open — top alert: "
                         + written[0]["id"])
        key = istore.put_watchdog_status("build", 10000, status)
        self.assertEqual(key, istore.watchdog_status_key("build",
                                                          10000))
        self.assertEqual(istore.get_watchdog_status("build", 10000),
                         status)

    def test_top_alert_is_highest_severity_earliest_first(self):
        self._write({"kind": "lease-risk", "severity": "warning",
                     "nick": "pax", "job": "8",
                     "explanation": "lease near expiry.",
                     "suggested_fix": "Wait for the sweep.",
                     "dedupe_key": "lease-risk:pax:8",
                     "created_at": 9000}, room="build")
        self._write({"kind": "presence-stall", "severity": "critical",
                     "nick": "pax", "job": "7",
                     "explanation": "pax absent over 10 minutes.",
                     "suggested_fix": "Check on pax.",
                     "dedupe_key": "presence-stall:pax:7",
                     "created_at": 9500}, room="build")
        self._write({"kind": "silent-room", "severity": "info",
                     "claimed_jobs": ["1"],
                     "explanation": "Room quiet with claimed jobs.",
                     "suggested_fix": "No action required.",
                     "dedupe_key": "silent-room:build",
                     "created_at": 8000}, room="build")
        status = istore.build_watchdog_status(
            istore.query_alerts(room="build"), room="build", ts=10000)
        self.assertEqual(status["counts"],
                         {"critical": 1, "warning": 1, "info": 1})
        self.assertEqual(status["open"], 3)
        self.assertEqual(status["top_alert"], "presence-stall:pax:7")

    def test_resolved_alerts_leave_open_counts_but_are_counted(self):
        record = self._write(
            {"kind": "presence-stall", "severity": "critical",
             "nick": "pax", "job": "7",
             "explanation": "pax absent over 10 minutes.",
             "suggested_fix": "Check on pax.",
             "dedupe_key": "presence-stall:pax:7",
             "created_at": 10000}, room="build")
        istore.resolve_alert(record["id"], now=10100)
        status = istore.build_watchdog_status(
            istore.query_alerts(room="build"), room="build", ts=10100)
        self.assertEqual(status["counts"],
                         {"critical": 0, "warning": 0, "info": 0})
        self.assertEqual(status["open"], 0)
        self.assertEqual(status["resolved"], 1)
        self.assertEqual(status["total"], 1)
        self.assertIsNone(status["top_alert"])
        self.assertIn("no open alerts", status["line"])

    def test_quiet_store_status_line_is_all_clear(self):
        status = istore.build_watchdog_status([], room="build",
                                              ts=10000)
        self.assertEqual(status["counts"],
                         {"critical": 0, "warning": 0, "info": 0})
        self.assertEqual(status["open"], 0)
        self.assertIsNone(status["top_alert"])
        self.assertEqual(status["line"],
                         "Watchdog: 0 critical, 0 warning, 0 info "
                         "open — no open alerts")

    def test_template_brief_on_stall_fixture_carries_matching_line(
            self):
        written = []
        watchdog.tick(
            self._stall_snapshot(), now=10000,
            emit=lambda a: written.append(
                istore.write_alert(a, room="build")))
        stored = istore.query_alerts(room="build")
        status = istore.build_watchdog_status(stored, room="build",
                                              ts=10000)
        snapshot = dict(self._stall_snapshot())
        snapshot["alerts"] = [
            dict(record, summary=record["explanation"])
            for record in stored]
        text = brief.compose_template_brief(snapshot)
        self.assertIn(status["line"], text)
        self.assertIn(written[0]["id"], text)
        watch = text.split("Watch items\n", 1)[1]
        self.assertTrue(watch.startswith(status["line"] + "\n"))

    def test_brief_without_severity_alerts_keeps_exact_shape(self):
        snapshot = {"messages": [], "jobs": [],
                    "alerts": [{"id": "WD-STALL-3",
                                "summary": "job 3 stalled, no progress 30m"}]}
        text = brief.compose_template_brief(snapshot)
        self.assertNotIn("Watchdog:", text)
        self.assertIn("- WD-STALL-3: job 3 stalled, no progress 30m",
                      text)


class LockedThresholdsTest(unittest.TestCase):
    """INT-022: production thresholds locked, pinned in one place.

    Values are the locked table in intel/evals/watchdog_tuning.md
    (INT-022 section). EnvOverrideTest already covers the override
    mechanics; this class pins the locked defaults themselves so a
    silent drift fails loudly and cites the tuning doc.
    """

    def test_int022_locked_threshold_table(self):
        self.assertEqual(thresholds.STALL_MINUTES, 10)
        self.assertEqual(thresholds.PROGRESS_STALL_MINUTES, 10)
        self.assertEqual(thresholds.LEASE_RISK_WINDOW_MINUTES, 5)
        self.assertEqual(thresholds.LEASE_RISK_QUIET_MINUTES, 2)
        self.assertEqual(thresholds.ALERT_DEDUPE_COOLDOWN_MINUTES, 30)
        self.assertEqual(thresholds.SILENT_ROOM_MINUTES, 60)
        self.assertEqual(thresholds.WATCHDOG_BEAT_TTL_SECONDS, 300)
        self.assertEqual(thresholds.TICK_PAGE_SIZE, 1000)
        self.assertEqual(thresholds.TICK_MAX_MESSAGES, 1000)


if __name__ == "__main__":
    unittest.main()
