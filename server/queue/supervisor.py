#!/usr/bin/env python3
"""supervisor.py — the Meta Imperium autonomous supervisor.

The supervisor is NOT a failure watchdog and not another
assessment agent. It files no assessments, makes NO model calls,
dispatches nothing, and spends $0: every input is a record the
crew already wrote, and every output is a record appended to the
same audit trail. Its job is the one ChatGPT's review named and
Del approved: evaluate whether the whole system is BEHAVING
CORRECTLY, and intervene inside hard limits when it is not.

It reads three existing sources of truth:

  * the patrol heartbeat + crew event feed + incident records
    (crew_records.py, under TRIO_CREW_DATA_DIR),
  * the guardrail status (spark_guardrail.py) — read-only.

Detectors (all thresholds configurable, defaults in parentheses):

  patrol_stale (15 min)
      No patrol visit or running heartbeat recorded within the
      window while patrol should be running. A heartbeat in the
      paused-budget state is NOT stale: that pause is the budget
      governor working, and the budget detector below owns it.
      Intervention: requeue_stalled_patrol — a patrol-resume
      event is emitted for the patrol worker / loop feed.
  incident_stuck (30 min)
      An incident sitting in the same non-terminal state with no
      timeline activity past the window. Intervention: a
      supervisor step on the incident's timeline; an incident
      stuck in "investigating" is additionally stopped (its
      status advances to investigation-stopped).
  repeated_disagreement (3)
      Review verdicts clearing the origin division's flag —
      Review contradicting Patrol — at least 3 times for the
      same division in the recorded events. Event only: the
      supervisor flags the pattern; it does not re-judge frames.
  repeated_job_failure (3)
      The same failing outcome for the same camera at least 3
      times in the event feed. Feed errors pause the feed
      (pause_feed: the camera id is written to paused-feeds.json
      in the crew data dir, and patrol.py skips paused cameras);
      other failure kinds are event-only warnings.
  spend_approaching_limit (80% of the $75 cap)
      Guardrail spend at or past the warning fraction.
      Intervention: budget_warning, event only.
  orchestrator_loop (2)
      The same incident investigated again on the same evidence
      — same evidence hash when a record carries one, else the
      same camera + division lens — at least twice. This is the
      "orchestrator keeps re-investigating the same evidence"
      failure. Intervention: stop_investigation (a timeline step
      that advances the incident to investigation-stopped).
      Lane B's orchestrator events are read defensively: any
      investigation-shaped timeline step or event counts,
      whatever fields it happens to carry.

HARD LIMITS, in code: this module imports no generation
transport, files no job envelopes, and has no dispatch path. It
never overrides the budget or the safety policy — its only
writes are supervisor events, incident timeline steps, and the
paused-feeds file. Findings are de-duplicated against recent
supervisor events so a cron loop does not spam the trail with
the same finding every pass.

Run: python3 supervisor.py --once
Stdlib only.
"""
import argparse
import json
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import crew_records  # noqa: E402
import spark_guardrail  # noqa: E402

PAUSED_FEEDS_FILE = "paused-feeds.json"

DEFAULT_PATROL_STALE_S = 15 * 60
DEFAULT_INCIDENT_STUCK_S = 30 * 60
DEFAULT_DISAGREEMENT_THRESHOLD = 3
DEFAULT_JOB_FAILURE_THRESHOLD = 3
DEFAULT_BUDGET_WARN_FRACTION = 0.80
DEFAULT_LOOP_THRESHOLD = 2
DEFAULT_DEDUPE_WINDOW_S = 3600
EVENTS_WINDOW = 500

# Terminal incident statuses: the legacy pipeline values plus the
# orchestrator lifecycle's (orchestrator.TERMINAL_STATUSES), plus
# this supervisor's own stop state. "monitoring" is deliberately
# NOT terminal — it is an open hold, so a monitoring incident with
# no activity past the stuck window is exactly what the stuck
# detector exists to notice.
TERMINAL_STATUSES = {"cleared-by-review", "dispatched-simulated",
                     "closed-false-positive", "stopped", "resolved",
                     "closed", "investigation-stopped"}
FAILURE_OUTCOMES = {"feed-error", "job-error", "assessment-failed"}
EVIDENCE_HASH_FIELDS = ("evidence_hash", "frame_hash",
                        "frame_sha256", "sha256")


# -- time helpers --------------------------------------------------------

def _iso(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def _parse_iso(value):
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.timestamp()


def _epoch_of(record):
    """Best-effort epoch for a record/step/event, from whatever
    timestamp shape it carries. None when there is nothing
    parseable — an undated record is skipped, never guessed at."""
    if not isinstance(record, dict):
        return None
    for key in ("at_epoch", "epoch"):
        value = record.get(key)
        if isinstance(value, (int, float)) and \
                not isinstance(value, bool):
            return float(value)
    for key in ("at", "timestamp", "created_at"):
        parsed = _parse_iso(record.get(key))
        if parsed is not None:
            return parsed
    return None


# -- paused feeds (the file patrol.py reads) ------------------------------

def paused_feeds_path(directory):
    return os.path.join(directory, PAUSED_FEEDS_FILE)


def load_paused_feeds(directory):
    """Camera ids currently paused, [] when the file is absent or
    unreadable — a torn paused-feeds file pauses nothing rather
    than crashing the supervisor or patrol."""
    try:
        with open(paused_feeds_path(directory)) as f:
            data = json.load(f)
    except Exception:
        return []
    if isinstance(data, list):
        return [c for c in data if isinstance(c, str)]
    return []


def _write_paused_feeds(directory, camera_ids):
    path = paused_feeds_path(directory)
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(sorted(set(camera_ids)), f, indent=1)
    os.replace(tmp, path)


class Supervisor:
    """One deterministic evaluation pass over the crew records.
    All inputs are injected seams (records, guardrail status,
    clock) so the whole pass is testable offline."""

    def __init__(self, records=None, guardrail_status=None,
                 now_epoch=None,
                 patrol_stale_s=DEFAULT_PATROL_STALE_S,
                 incident_stuck_s=DEFAULT_INCIDENT_STUCK_S,
                 disagreement_threshold=DEFAULT_DISAGREEMENT_THRESHOLD,
                 job_failure_threshold=DEFAULT_JOB_FAILURE_THRESHOLD,
                 budget_warn_fraction=DEFAULT_BUDGET_WARN_FRACTION,
                 loop_threshold=DEFAULT_LOOP_THRESHOLD,
                 dedupe_window_s=DEFAULT_DEDUPE_WINDOW_S):
        self.records = records or crew_records.CrewRecords()
        self.guardrail_status = guardrail_status or spark_guardrail.status
        self._now = now_epoch or time.time
        self.patrol_stale_s = float(patrol_stale_s)
        self.incident_stuck_s = float(incident_stuck_s)
        self.disagreement_threshold = int(disagreement_threshold)
        self.job_failure_threshold = int(job_failure_threshold)
        self.budget_warn_fraction = float(budget_warn_fraction)
        self.loop_threshold = int(loop_threshold)
        self.dedupe_window_s = float(dedupe_window_s)
        self._events = []
        self._incidents = []

    # -- interventions -----------------------------------------------------

    def pause_feed(self, camera_id):
        """Add camera_id to paused-feeds.json (patrol.py skips
        paused cameras). Returns True when newly added."""
        current = load_paused_feeds(self.records.dir)
        if camera_id in current:
            return False
        current.append(camera_id)
        _write_paused_feeds(self.records.dir, current)
        return True

    def _already_reported(self, detector, scope, window_s):
        now = self._now()
        for event in self._events:
            if event.get("type") != "supervisor":
                continue
            if event.get("detector") != detector or \
                    event.get("scope") != scope:
                continue
            at = _epoch_of(event)
            if at is not None and now - at <= window_s:
                return True
        return False

    def _emit(self, detector, action, scope, detail, incident_id=None,
              timeline_status=None, extra=None):
        """The supervisor's only record writes: one event on the
        feed, and — for incident-scoped findings — one append-only
        timeline step on that incident. Nothing is edited or
        deleted, ever."""
        now = self._now()
        event = {"at": _iso(now), "at_epoch": now,
                 "type": "supervisor", "agent": "supervisor",
                 "detector": detector, "action": action,
                 "scope": scope, "detail": detail}
        if incident_id:
            event["incident_id"] = incident_id
        if extra:
            event.update(extra)
        self.records.append_event(event)
        if incident_id:
            step = {"at": _iso(now), "step": "supervisor",
                    "agent": "supervisor", "detector": detector,
                    "action": action, "detail": detail}
            if timeline_status:
                step["status"] = timeline_status
            try:
                self.records.append_timeline(incident_id, step)
            except KeyError:
                pass  # the feed event above is the record of record
        return event

    # -- detectors -----------------------------------------------------------

    def _detect_patrol_stale(self):
        status = None
        try:
            status = self.records.read_status()
        except Exception:
            status = None
        if status and status.get("state") == "paused-budget":
            return []  # the governor's pause is loud already
        last = _epoch_of(status) if status else None
        for event in self._events:
            if event.get("type") == "patrol-check":
                at = _epoch_of(event)
                if at is not None:
                    last = at if last is None else max(last, at)
        now = self._now()
        if last is not None and now - last <= self.patrol_stale_s:
            return []
        if last is None:
            detail = ("no patrol visit or heartbeat has ever been "
                      "recorded in the crew data")
        else:
            detail = (f"last patrol activity {int(now - last)}s ago "
                      f"exceeds the {int(self.patrol_stale_s)}s "
                      "stale threshold")
        scope = "patrol"
        if self._already_reported("patrol_stale", scope,
                                  self.patrol_stale_s):
            return []
        self._emit("patrol_stale", "requeue_stalled_patrol", scope,
                   detail)
        # The patrol-resume signal the intervention is named for:
        # a distinct, plainly-labelled event on the same feed.
        self.records.append_event({
            "at": _iso(now), "at_epoch": now, "type": "patrol-resume",
            "agent": "supervisor", "detector": "patrol_stale",
            "action": "requeue_stalled_patrol", "detail": detail})
        return [{"detector": "patrol_stale",
                 "action": "requeue_stalled_patrol", "scope": scope,
                 "detail": detail}]

    def _detect_incidents_stuck(self):
        findings = []
        now = self._now()
        for record in self._incidents:
            status = record.get("status") or ""
            if status in TERMINAL_STATUSES:
                continue
            last = _epoch_of(record)
            for step in record.get("timeline") or []:
                at = _epoch_of(step)
                if at is not None:
                    last = at if last is None else max(last, at)
            if last is None or now - last <= self.incident_stuck_s:
                continue
            incident_id = record.get("id")
            scope = f"incident:{incident_id}"
            if self._already_reported("incident_stuck", scope,
                                      self.incident_stuck_s):
                continue
            detail = (f"incident in state {status!r} with no "
                      f"timeline activity for {int(now - last)}s "
                      f"(threshold {int(self.incident_stuck_s)}s)")
            if status == "investigating":
                action = "stop_investigation"
                timeline_status = "investigation-stopped"
            else:
                action = "stuck_incident_flagged"
                timeline_status = None
            self._emit("incident_stuck", action, scope, detail,
                       incident_id=incident_id,
                       timeline_status=timeline_status)
            findings.append({"detector": "incident_stuck",
                             "action": action, "scope": scope,
                             "incident_id": incident_id,
                             "detail": detail})
        return findings

    def _detect_disagreement(self):
        counts = Counter()
        for event in self._events:
            if event.get("type") == "review" and \
                    event.get("verdict") == "cleared" and \
                    event.get("division"):
                counts[event["division"]] += 1
        findings = []
        for division, count in sorted(counts.items()):
            if count < self.disagreement_threshold:
                continue
            scope = f"division:{division}"
            if self._already_reported("repeated_disagreement", scope,
                                      self.dedupe_window_s):
                continue
            detail = (f"review cleared the {division} flag {count} "
                      f"times in the recorded events (threshold "
                      f"{self.disagreement_threshold}) — review "
                      "keeps contradicting patrol for this division")
            self._emit("repeated_disagreement",
                       "disagreement_warning", scope, detail,
                       extra={"division": division, "count": count})
            findings.append({"detector": "repeated_disagreement",
                             "action": "disagreement_warning",
                             "scope": scope, "detail": detail})
        return findings

    def _detect_job_failures(self):
        groups = defaultdict(int)
        for event in self._events:
            outcome = event.get("outcome")
            if event.get("type") == "patrol-check" and \
                    outcome in FAILURE_OUTCOMES:
                groups[(outcome, event.get("camera_id") or "")] += 1
        findings = []
        for (kind, camera_id), count in sorted(groups.items()):
            if count < self.job_failure_threshold:
                continue
            scope = f"job:{kind}:{camera_id}"
            if self._already_reported("repeated_job_failure", scope,
                                      self.dedupe_window_s):
                continue
            if kind == "feed-error" and camera_id:
                action = "pause_feed"
                paused = self.pause_feed(camera_id)
                detail = (f"camera {camera_id} failed with "
                          f"feed-error {count} times (threshold "
                          f"{self.job_failure_threshold}); feed "
                          "paused for patrol"
                          if paused else
                          f"camera {camera_id} failed with "
                          f"feed-error {count} times; feed was "
                          "already paused")
            else:
                action = "job_failure_warning"
                detail = (f"{kind} for camera {camera_id or '?'} "
                          f"occurred {count} times (threshold "
                          f"{self.job_failure_threshold})")
            self._emit("repeated_job_failure", action, scope, detail,
                       extra={"camera_id": camera_id or None,
                              "kind": kind, "count": count})
            findings.append({"detector": "repeated_job_failure",
                             "action": action, "scope": scope,
                             "detail": detail})
        return findings

    def _detect_budget(self):
        try:
            status = self.guardrail_status()
            spent = float(status["est_cost_usd"])
            cap = float(status["test_budget_usd"])
        except Exception:
            return []  # unreadable guardrail state: no invented finding
        if cap <= 0 or spent < self.budget_warn_fraction * cap:
            return []
        scope = "budget"
        if self._already_reported("spend_approaching_limit", scope,
                                  self.dedupe_window_s):
            return []
        detail = (f"guardrail spend ${spent:.2f} is at "
                  f"{spent / cap:.0%} of the ${cap:.2f} test cap "
                  f"(warning at {self.budget_warn_fraction:.0%}); "
                  "the guardrail itself is unchanged and still "
                  "refuses at the cap — the supervisor cannot and "
                  "does not raise it")
        self._emit("spend_approaching_limit", "budget_warning", scope,
                   detail, extra={"est_cost_usd": spent,
                                  "test_budget_usd": cap})
        return [{"detector": "spend_approaching_limit",
                 "action": "budget_warning", "scope": scope,
                 "detail": detail}]

    def _evidence_key(self, source):
        """The evidence-hash key alone, or None. Orchestrator
        DECISION events carry the incident's camera + division on
        every decision, so for those only a hash can show the
        SAME evidence was investigated again — a second decision
        about an incident is normal operation, not a loop."""
        for field in EVIDENCE_HASH_FIELDS:
            value = source.get(field)
            if isinstance(value, str) and value:
                return f"hash:{value}"
        return None

    def _investigation_key(self, source):
        key = self._evidence_key(source)
        if key:
            return key
        camera_id = source.get("camera_id") or ""
        division = source.get("division") or ""
        if camera_id or division:
            return f"lens:{camera_id}|{division}"
        return None

    def _detect_orchestrator_loops(self):
        attempts = Counter()
        for record in self._incidents:
            incident_id = record.get("id")
            for step in record.get("timeline") or []:
                if step.get("step") not in ("investigation",
                                            "orchestrator"):
                    continue
                key = self._investigation_key(step)
                if key:
                    attempts[(incident_id, key)] += 1
        for event in self._events:
            incident_id = event.get("incident_id")
            if not incident_id:
                continue
            if event.get("type") == "investigation":
                # One event per investigation RUN (crew.py): the
                # lens fallback is sound here.
                key = self._investigation_key(event)
            elif event.get("type") in ("orchestrator",
                                       "orchestrator-decision"):
                # Decision events fire on every decision; only a
                # repeated evidence hash proves a loop.
                key = self._evidence_key(event)
            else:
                continue
            if key:
                attempts[(incident_id, key)] += 1
        findings = []
        by_id = {r.get("id"): r for r in self._incidents}
        for (incident_id, key), count in sorted(attempts.items()):
            if count < self.loop_threshold:
                continue
            record = by_id.get(incident_id) or {}
            already_stopped = any(
                step.get("step") == "supervisor" and
                step.get("action") == "stop_investigation"
                for step in record.get("timeline") or [])
            if already_stopped or \
                    (record.get("status") in TERMINAL_STATUSES):
                continue
            scope = f"loop:{incident_id}:{key}"
            if self._already_reported("orchestrator_loop", scope,
                                      self.dedupe_window_s):
                continue
            detail = (f"incident investigated {count} times on "
                      f"the same evidence ({key}); investigation "
                      "stopped by the supervisor — no further "
                      "spend on this evidence")
            self._emit("orchestrator_loop", "stop_investigation",
                       scope, detail, incident_id=incident_id,
                       timeline_status="investigation-stopped")
            findings.append({"detector": "orchestrator_loop",
                             "action": "stop_investigation",
                             "scope": scope,
                             "incident_id": incident_id,
                             "detail": detail})
        return findings

    # -- one pass ------------------------------------------------------------

    def run(self):
        self._events = self.records.recent_events(EVENTS_WINDOW)
        self._incidents = self.records.list_incidents()
        findings = []
        for detect in (self._detect_patrol_stale,
                       self._detect_incidents_stuck,
                       self._detect_disagreement,
                       self._detect_job_failures,
                       self._detect_budget,
                       self._detect_orchestrator_loops):
            try:
                findings.extend(detect())
            except Exception:
                # Defensive by design: one detector's bad input
                # must never silence the other five. The finding
                # that matters is the one that fires.
                continue
        return {"at": _iso(self._now()), "findings": findings,
                "actions": len(findings)}


def summary_line(result):
    findings = result["findings"]
    if not findings:
        return "supervisor: no findings"
    parts = ", ".join(f"{f['detector']}:{f['action']}"
                      for f in findings)
    return f"supervisor: {len(findings)} finding(s): {parts}"


def _env_float(name, default):
    try:
        return float(os.environ[name])
    except (KeyError, ValueError):
        return default


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true",
                    help="one supervisor pass, then exit (the only "
                         "mode: every invocation is a single pass)")
    ap.add_argument("--patrol-stale-s", type=float,
                    default=_env_float("TRIO_SUPERVISOR_PATROL_STALE_S",
                                       DEFAULT_PATROL_STALE_S))
    ap.add_argument("--incident-stuck-s", type=float,
                    default=_env_float(
                        "TRIO_SUPERVISOR_INCIDENT_STUCK_S",
                        DEFAULT_INCIDENT_STUCK_S))
    ap.add_argument("--budget-warn-fraction", type=float,
                    default=_env_float(
                        "TRIO_SUPERVISOR_BUDGET_WARN_FRACTION",
                        DEFAULT_BUDGET_WARN_FRACTION))
    args = ap.parse_args()
    supervisor = Supervisor(
        patrol_stale_s=args.patrol_stale_s,
        incident_stuck_s=args.incident_stuck_s,
        budget_warn_fraction=args.budget_warn_fraction)
    result = supervisor.run()
    print(summary_line(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
