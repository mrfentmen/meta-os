#!/usr/bin/env python3
"""patrol.py — the Meta Imperium patrol worker.

Patrol is the front of the agent crew (docs/AGENT_CREW.md): it
cycles the public camera list, takes one snapshot per visit, and
files it as a trio-assessment job on the existing queue through
crew.Crew — which runs review, records, investigation, and the
SIMULATED response for anything that flags. Patrol itself only
decides WHERE to look next and WHEN to stop spending:

  * Round-robin over the loaded camera list, one division lens per
    visit, the lens rotating with each visit (vigiles -> ignis ->
    medicus -> ...) so every camera is checked under every lens
    over time.
  * Adaptive priority: cameras at or near an open incident
    (within PRIORITY_RADIUS_M of the incident camera, or the
    incident camera itself) and cameras flagged recently are
    visited FIRST each cycle; the rest follow in round-robin order.
  * Budget governor: before every check, the existing guardrail
    state (spark_guardrail.status()) is read. When the remaining
    test budget falls to the reserve (TRIO_CREW_BUDGET_RESERVE_USD,
    default $5) or the guardrail itself refuses, patrol PAUSES —
    writes its status as paused-budget, records the event, and
    files nothing — until the state changes. The pause is loud in
    crew-status.json and the event feed, never silent. Note the
    guardrail's own scope (spark_guardrail.py): it counts the
    direct transport; on the DEV helper transport the helper's own
    guardrail independently refuses calls — patrol's governor is an
    additional stop, not the only one.

State is written every cycle to crew_records (crew-status.json), so
the Command view's loop feed and the status endpoint always show
what patrol is actually doing — including when the camera list came
from the offline fallback subset (the status names the source).

Run: python3 patrol.py [--interval 20] [--once] [--max-checks N]
Stdlib only.
"""
import argparse
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew  # noqa: E402
import crew_common  # noqa: E402
import crew_records  # noqa: E402
import spark_guardrail  # noqa: E402

DIVISIONS = ("vigiles", "ignis", "medicus")
PRIORITY_RADIUS_M = 1500.0
RECENT_FLAG_WINDOW_S = 3600
DEFAULT_BUDGET_RESERVE_USD = 5.0


def _log(msg):
    print(f"patrol: {msg}", file=sys.stderr)


def patrol_order(cameras, priority_ids, start_after_id=None):
    """The visit order for one cycle: priority cameras first (in
    list order), then the rest in round-robin order starting just
    after start_after_id. Pure and deterministic — the adaptive
    part is which ids are in priority_ids, computed by
    compute_priority_ids from the records."""
    ids = [c["id"] for c in cameras]
    by_id = {c["id"]: c for c in cameras}
    priority = [i for i in ids if i in priority_ids]
    rest = [i for i in ids if i not in priority_ids]
    if start_after_id in rest:
        k = rest.index(start_after_id)
        rest = rest[k + 1:] + rest[:k + 1]
    return [by_id[i] for i in priority + rest]


def compute_priority_ids(cameras, incidents, recent_events,
                         now_epoch, radius_m=PRIORITY_RADIUS_M,
                         window_s=RECENT_FLAG_WINDOW_S):
    """Cameras patrol should revisit sooner: the incident cameras
    themselves, every camera within radius_m of an open incident,
    and any camera flagged within the recent window."""
    priority = set()
    incident_points = []
    for record in incidents:
        cam = record.get("camera") or {}
        if cam.get("id"):
            priority.add(cam["id"])
        if isinstance(cam.get("latitude"), (int, float)) and \
                isinstance(cam.get("longitude"), (int, float)):
            incident_points.append(cam)
    for cam in cameras:
        for point in incident_points:
            if crew_common.distance_meters(cam, point) <= radius_m:
                priority.add(cam["id"])
                break
    for event in recent_events:
        if event.get("type") != "flag":
            continue
        at = event.get("at_epoch")
        if isinstance(at, (int, float)) and \
                now_epoch - at <= window_s and event.get("camera_id"):
            priority.add(event["camera_id"])
    return priority


class Patrol:
    def __init__(self, crew_obj, cameras, camera_source, records,
                 interval_s=20.0, divisions=DIVISIONS,
                 reserve_usd=DEFAULT_BUDGET_RESERVE_USD,
                 guardrail_status=None, sleep=time.sleep):
        self.crew = crew_obj
        self.cameras = list(cameras)
        self.camera_source = camera_source
        self.records = records
        self.interval_s = float(interval_s)
        self.divisions = tuple(divisions)
        self.reserve_usd = float(reserve_usd)
        self.guardrail_status = guardrail_status or spark_guardrail.status
        self.sleep = sleep
        self._visits = 0
        self._last_id = None
        self._counts = {"checks": 0, "baseline": 0, "flagged": 0,
                        "reported": 0, "feed_errors": 0, "job_errors": 0}
        self._paused = False

    def _budget(self):
        """(ok, status_dict): ok=False means paused. The existing
        guardrail is the source: its stop raises GuardrailStop, its
        status() gives the numbers the pause decision and the
        heartbeat both report."""
        try:
            spark_guardrail.check()
        except spark_guardrail.GuardrailStop as e:
            return False, {"guardrail_stop": str(e)}
        st = self.guardrail_status()
        if st["remaining_usd"] <= self.reserve_usd:
            return False, st
        return True, st

    def _write_status(self, state, reason=None, extra=None):
        status = {
            "service": "imperium-patrol",
            "state": state,
            "reason": reason,
            "at": crew_common.now_iso(),
            "camera_source": self.camera_source,
            "cameras": len(self.cameras),
            "interval_s": self.interval_s,
            "counts": dict(self._counts),
            "last_camera_id": self._last_id,
        }
        if extra:
            status.update(extra)
        self.records.write_status(status)
        return status

    def run_cycle(self):
        """One patrol visit: budget check, pick the next camera and
        lens, run the crew check, update the heartbeat. Returns the
        outcome dict (or {"outcome": "paused-budget"})."""
        ok, budget = self._budget()
        if not ok:
            if not self._paused:
                self._paused = True
                self.records.append_event({
                    "at": crew_common.now_iso(), "type": "patrol-status",
                    "state": "paused-budget",
                    "reason": "test budget reserve reached — patrol "
                              "files no jobs until the guardrail "
                              "state changes",
                    "guardrail": budget})
                _log("PAUSED — budget reserve reached; filing nothing")
            self._write_status("paused-budget",
                               reason="budget reserve reached",
                               extra={"guardrail": budget})
            return {"outcome": "paused-budget"}
        if self._paused:
            self._paused = False
            self.records.append_event({
                "at": crew_common.now_iso(), "type": "patrol-status",
                "state": "running"})
        incidents = self.records.open_incidents()
        events = self.records.recent_events(200)
        priority = compute_priority_ids(self.cameras, incidents,
                                        events, time.time())
        order = patrol_order(self.cameras, priority, self._last_id)
        if not order:
            self._write_status("idle", reason="no cameras loaded",
                               extra={"guardrail": budget})
            return {"outcome": "no-cameras"}
        camera = order[0]
        division = self.divisions[self._visits % len(self.divisions)]
        self._visits += 1
        self._last_id = camera["id"]
        outcome = self.crew.check_camera(camera, division)
        self._counts["checks"] += 1
        o = outcome.get("outcome")
        if o == "baseline":
            self._counts["baseline"] += 1
        elif o == "feed-error":
            self._counts["feed_errors"] += 1
        elif o in ("job-error", "assessment-failed"):
            self._counts["job_errors"] += 1
        else:
            self._counts["flagged"] += 1
            if o in ("dispatched-simulated", "reported"):
                self._counts["reported"] += 1
        self._write_status("running", extra={
            "guardrail": budget,
            "last_check": {"camera_id": camera["id"],
                           "camera_name": camera["name"],
                           "division": division, "outcome": o}})
        return outcome

    def run(self, max_checks=None):
        done = 0
        while max_checks is None or done < max_checks:
            self.run_cycle()
            done += 1
            if max_checks is not None and done >= max_checks:
                break
            self.sleep(self.interval_s)
        return dict(self._counts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=20.0,
                    help="seconds between patrol visits")
    ap.add_argument("--once", action="store_true",
                    help="one patrol visit, then exit")
    ap.add_argument("--max-checks", type=int, default=None)
    ap.add_argument("--reserve-usd", type=float,
                    default=DEFAULT_BUDGET_RESERVE_USD)
    args = ap.parse_args()
    cameras, source = crew_common.load_cameras()
    _log(f"camera list source: {source} ({len(cameras)} online cameras)")
    if source == "fallback-subset":
        _log("WARNING — live NYCTMC list unreachable; patrolling the "
             "offline fallback subset, labelled as such in status")
    records = crew_records.CrewRecords()
    crew_obj = crew.Crew.production(records=records, cameras=cameras)
    patrol = Patrol(crew_obj, cameras, source, records,
                    interval_s=args.interval,
                    reserve_usd=args.reserve_usd)
    max_checks = 1 if args.once else args.max_checks
    try:
        counts = patrol.run(max_checks=max_checks)
        _log(f"counts: {counts}")
    except KeyboardInterrupt:
        _log("stopping")
    return 0


if __name__ == "__main__":
    sys.exit(main())
