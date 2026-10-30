"""DSH-037: static payload dev pack for the dashboard lane.

The pack is checked-in JSON under intel/devpack/, built from real
producer output on fixtures, never hand-written history:

- brief: two generate_brief records (morning, template fallback)
  from one fixture snapshot: fresh (age 900s) and stale (age
  12600s), the BRF-043 pair the brief panel is developed against.
- plan_preview: validated_plan + check_dep_graph on the demo
  goal plan (hackathon/demo_goal_plan.json), reduced to the
  DSP-037 preview shape by intel/devpack.py.
- alerts: watchdog.tick on a stall/collision/dead-dep fixture
  snapshot, each alert built into a WDG-010 record. tick emits
  one collision alert per colliding pair, so the feed holds five
  records, all critical.
- crew_board: presence beats, capability registrations, and
  jobs.py posts/claims/progress/blocks run on FakeUpstash, then
  presence_list + capabilities.agents + list --json read back.
  The acting nicks are crew nicks (pax posts, milo claims,
  rowan blocks), so the presence list holds crew only; job
  commands beat for the acting nick, which is why presence is
  read after the job commands, not before.

test_pack_matches_checked_in rebuilds all four payloads and
asserts they equal the checked-in files: a stale pack fails the
suite instead of silently drifting from the code. Regenerate
with: python3 tests/test_intel_devpack.py --dump intel/devpack
(run from the repo root). Nothing here posts to a bus, calls
Spark, or touches a real Redis: the whole build runs on
FakeUpstash under a frozen clock.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import jobs  # noqa: E402
import relay_common as rc  # noqa: E402
from helpers import RelayTestCase  # noqa: E402
from intel import brief, devpack, dispatch, watchdog  # noqa: E402
from intel import store as istore  # noqa: E402
from mos import capabilities  # noqa: E402

ROOM = "build-relay-intel"
NOW = 1793101200
FRESH_TS = 1793101200
STALE_TS = 1793089500
AS_OF = 1793102100
PACK_DIR = os.path.join(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))), "intel", "devpack")


def brief_snapshot():
    return {
        "messages": [
            {"nick": "pax",
             "text": "DECISION: ship the brief panel first"},
            {"nick": "milo",
             "text": "DONE: watchdog loop runs on the stall fixture"},
            {"nick": "rowan", "text": "just checking the viewer"},
            {"nick": "pax",
             "text": "BLOCKED: dispatch needs the Spark endpoint"},
        ],
        "jobs": [
            {"id": "1", "title": "intel status module",
             "status": "claimed", "claim": "milo"},
            {"id": "2", "title": "status module tests",
             "status": "open"},
            {"id": "3", "title": "viewer panel stub",
             "status": "blocked",
             "note": "waiting on the Spark endpoint decision"},
        ],
        "alerts": [{"id": "alert:presence-stall:milo:1",
                    "summary": "milo stalled on job 1"}],
    }


def alert_snapshot():
    return {
        "messages": [{"nick": "pax", "text": "working",
                      "ts": NOW - 60}],
        "presence": ["pax", "rowan"],
        "caps": {"milo": {}, "pax": {}, "rowan": {}},
        "jobs": [
            {"id": "1", "title": "intel status module",
             "status": "claimed", "claim": "milo",
             "files": "intel/status.py",
             "last_progress": NOW - 7200},
            {"id": "7", "title": "status panel A",
             "status": "claimed", "claim": "pax",
             "files": "intel/status.py",
             "last_progress": NOW - 60},
            {"id": "8", "title": "status panel B",
             "status": "claimed", "claim": "rowan",
             "files": "intel/status.py",
             "last_progress": NOW - 60},
            {"id": "3", "title": "viewer panel stub",
             "status": "blocked",
             "note": "waiting on the Spark endpoint decision"},
            {"id": "9", "title": "docs for the status page",
             "status": "open", "deps": "3"},
        ],
    }


def build_pack(case):
    """Build all four payloads on the case's FakeUpstash."""
    case.fake.t = NOW
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    _text, fresh = brief.generate_brief(
        brief_snapshot(), ROOM, kind="morning", now=FRESH_TS,
        dry_run=True)
    _text, stale = brief.generate_brief(
        brief_snapshot(), ROOM, kind="morning", now=STALE_TS,
        dry_run=True)
    brief_pack = {
        "room": ROOM,
        "fresh": devpack.brief_entry(fresh, AS_OF),
        "stale": devpack.brief_entry(stale, AS_OF),
    }

    with open(os.path.join(root, "hackathon",
                           "demo_goal_plan.json")) as fh:
        plan_text = fh.read()
    plan, order, _clamps = dispatch.validated_plan(plan_text)
    plan_pack = {"room": ROOM,
                 "source": "hackathon/demo_goal_plan.json"}
    plan_pack.update(devpack.plan_preview(plan, order))

    found = watchdog.tick(alert_snapshot(), now=NOW)
    records = [istore.build_alert_record(a, room=ROOM, now=NOW)
               for a in found]
    alerts_pack = {"room": ROOM,
                   "alerts": devpack.alerts_feed(records)}

    case.set_nick("pax", "host-a")
    rc.presence_beat()
    case.set_nick("rowan", "host-b")
    rc.presence_beat()
    for nick, host, caps, roles in (
            ("pax", "host-a", ["brief", "dispatch"], "builder"),
            ("milo", "host-c", ["watchdog"], "watcher"),
            ("rowan", "host-b", ["viewer"], "builder")):
        case.set_nick(nick, host)
        capabilities.register(nick, caps, roles=roles)
    case.set_nick("pax", "host-a")
    jobs.NICK = "pax"
    case.run_cli(jobs.main, ["post", "--title", "intel status module",
                             "--spec", "build the module",
                             "--files", "intel/status.py"])
    case.run_cli(jobs.main, ["post", "--title", "status module tests",
                             "--spec", "test the module",
                             "--files", "tests/test_intel_status.py",
                             "--deps", "1"])
    case.run_cli(jobs.main, ["post", "--title", "viewer panel stub",
                             "--spec", "stub the panel",
                             "--files", "bus.html"])
    case.set_nick("milo", "host-c")
    jobs.NICK = "milo"
    case.run_cli(jobs.main, ["claim", "1", "--lease", "1800"])
    case.run_cli(jobs.main, ["progress", "1",
                             "--note", "module drafted"])
    case.set_nick("rowan", "host-b")
    jobs.NICK = "rowan"
    case.run_cli(jobs.main, ["claim", "3", "--lease", "500"])
    case.run_cli(jobs.main, ["blocked", "3", "--reason",
                             "waiting on the Spark endpoint decision"])
    _code, out, _err = case.run_cli(jobs.main, ["list", "--json"])
    rows = json.loads(out)
    presence = rc.presence_list()
    caps = capabilities.agents()
    crew_pack = {"room": ROOM}
    crew_pack.update(devpack.crew_board(presence, caps, rows))

    return {"brief": brief_pack, "plan_preview": plan_pack,
            "alerts": alerts_pack, "crew_board": crew_pack}


class DevpackTest(RelayTestCase):
    def test_pack_matches_checked_in(self):
        pack = build_pack(self)
        loaded = devpack.load_pack()
        self.assertEqual(pack, loaded)

    def test_brief_fresh_and_stale(self):
        pack = build_pack(self)
        fresh = pack["brief"]["fresh"]
        stale = pack["brief"]["stale"]
        self.assertEqual(fresh["age_seconds"], 900)
        self.assertEqual(stale["age_seconds"], 12600)
        self.assertEqual(fresh["model"], "template")
        self.assertEqual(stale["model"], "template")
        self.assertEqual(fresh["sections"], stale["sections"])
        self.assertEqual(fresh["sections"]["Blocked and why"],
                         ["3 viewer panel stub: "
                          "waiting on the Spark endpoint decision"])

    def test_plan_preview_shape(self):
        preview = build_pack(self)["plan_preview"]
        self.assertEqual(preview["posting_order"],
                         ["module", "panel", "tests", "docs", "review"])
        self.assertEqual(preview["budgets"],
                         {"jobs": 5, "max_attempts_total": 15})
        self.assertEqual([j["key"] for j in preview["jobs"]],
                         ["module", "panel", "tests", "docs", "review"])
        for job in preview["jobs"]:
            self.assertTrue(job["files"])
            self.assertTrue(job["accept"])

    def test_alerts_feed(self):
        alerts = build_pack(self)["alerts"]["alerts"]
        self.assertEqual(len(alerts), 5)
        kinds = sorted(a["kind"] for a in alerts)
        self.assertEqual(kinds, ["dead-dep", "file-collision",
                                 "file-collision", "file-collision",
                                 "presence-stall"])
        self.assertTrue(all(a["severity"] == "critical"
                        for a in alerts))
        self.assertTrue(all(a["status"] == "open" for a in alerts))
        stamps = [a["created_at"] for a in alerts]
        self.assertEqual(stamps, sorted(stamps, reverse=True))

    def test_crew_board_sources(self):
        crew = build_pack(self)["crew_board"]
        self.assertEqual(crew["presence"], ["milo", "pax", "rowan"])
        self.assertEqual(set(crew["caps"]),
                         {"milo", "pax", "rowan"})
        rows = {r["id"]: r for r in crew["jobs"]}
        self.assertEqual(rows["1"]["status"], "claimed")
        self.assertEqual(rows["1"]["claim"], "milo")
        self.assertEqual(rows["1"]["last_progress_at"], NOW)
        self.assertEqual(rows["1"]["lease_until"], NOW + 1800)
        self.assertEqual(rows["2"]["status"], "open")
        self.assertEqual(rows["3"]["status"], "blocked")
        self.assertEqual(set(rows["1"].keys()),
                         {"id", "title", "status", "claim", "files",
                          "deps", "artifacts", "req", "attempts",
                          "lease_until", "last_progress_at"})
        self.assertEqual(rows["1"]["artifacts"], [])

    def test_brief_entry_rejects_bad_timestamps(self):
        with self.assertRaises(ValueError):
            devpack.brief_entry({"generated_at": "soon"}, NOW)
        with self.assertRaises(ValueError):
            devpack.brief_entry({"generated_at": NOW}, "soon")

    def test_plan_preview_rejects_bad_order(self):
        plan = {"summary": "s", "jobs": [{
            "key": "a", "title": "t", "files": ["f"], "deps": [],
            "max_attempts": 3, "accept": ["file-exists f"]}]}
        with self.assertRaises(ValueError):
            devpack.plan_preview(plan, ["b"])


def _dump(directory):
    case = DevpackTest("test_pack_matches_checked_in")
    case.setUp()
    try:
        pack = build_pack(case)
    finally:
        case.doCleanups()
    os.makedirs(directory, exist_ok=True)
    for name, filename in devpack.PACK_FILES.items():
        path = os.path.join(directory, filename)
        with open(path, "w") as fh:
            json.dump(pack[name], fh, indent=2, sort_keys=True)
            fh.write("\n")
        print(f"wrote {path}")


if __name__ == "__main__":
    if len(sys.argv) >= 3 and sys.argv[1] == "--dump":
        _dump(sys.argv[2])
    else:
        unittest.main()
