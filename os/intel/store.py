"""intel/store.py — Redis records for Relay Intelligence (FND-004).

All intel state lives under the relay key prefix (relay_common
.key_prefix(), default "muse-bus", override MUSE_RELAY_KEY_PREFIX):

  <prefix>:intel:brief:<room>:<ts>    string, JSON brief record.
                                      <room> is relay_common.clean_room()
                                      output; the default room is "main".
                                      <ts> is the brief's unix timestamp.
  <prefix>:intel:alert:<id>           string, JSON alert record.
                                      WDG-010 shape: {id, kind, severity,
                                      room, subjects, explanation,
                                      suggested_fix, created_at,
                                      resolved_at, dedupe_key} plus any
                                      detector evidence fields (nick,
                                      job, ages, ...). resolved_at is
                                      null while the alert is open.
                                      Written via write_alert(), which
                                      validates the shape before storing.
  <prefix>:intel:alert:index         sorted set, the WDG-023 alert
                                      history index: member = alert id,
                                      score = created_at of the current
                                      occurrence. write_alert() maintains
                                      it (raw put_alert() does not);
                                      query_alerts() reads it, so only
                                      validated alert records are
                                      queryable.
                                      WDG-013 adds last_seen: the last
                                      tick that re-reported this alert
                                      inside the dedupe cooldown (equal
                                      to created_at on first write).
                                      WDG-014 adds the lifecycle:
                                      status "open" (fresh record,
                                      resolved_at null) ->
                                      "acknowledged" (acknowledged_at
                                      set, still unresolved) ->
                                      "resolved" (resolved_at set, by
                                      hand via resolve_alert() or
                                      automatically via
                                      auto_resolve_cleared() when a
                                      tick no longer re-fires it).
                                      A resolved record that fires
                                      again starts a fresh open
                                      occurrence (WDG-013); an
                                      acknowledged record re-fired
                                      inside the cooldown keeps its
                                      acknowledged status with only
                                      last_seen advanced.
  <prefix>:intel:notify:<id>          string, JSON notification record
                                      (notification system, Del order
                                      2026-10-28): {id, source, severity,
                                      topic, text, target, room,
                                      created_at, last_seen, count,
                                      dedupe_key, status,
                                      acknowledged_at, acknowledged_by,
                                      resolved_at}. The general
                                      notification record for every OS
                                      producer (jobs, overseer, drivers,
                                      uplink, watchman, brief); alerts
                                      stay the watchdog's detector
                                      subset. Lifecycle mirrors alerts:
                                      open -> acknowledged -> resolved.
                                      Written via write_notify(), which
                                      validates before storing; a
                                      re-notify of an unresolved record
                                      advances last_seen and count
                                      instead of duplicating it.
  <prefix>:intel:notify:index        sorted set, the notification
                                      history index: member = notify
                                      id, score = created_at of the
                                      current occurrence.
                                      write_notify() maintains it;
                                      query_notify() reads it.
  <prefix>:intel:dispatch:<id>        string, JSON dispatch (plan) record.
  <prefix>:intel:watchdog_status:<room>:<ts>
                                      string, JSON watchdog status record
                                      (WDG-028): {room, ts, counts
                                      (unresolved, by severity), open,
                                      resolved, total, top_alert,
                                      line}. Written by the caller
                                      that builds the brief, from the
                                      alert store it just queried, so
                                      the brief's counts and the
                                      store agree by construction.
  <prefix>:intel:wd:bootstatus:<room>:<ts>
                                      string, JSON boot status record
                                      (OS-041): {room, ts, units_up,
                                      units_total, units_down,
                                      workers_alive, workers_count,
                                      last_alert, line}. The one line
                                      Rowan's boot checklist (OS-043)
                                      renders; freshness is judged by
                                      boot_status_is_stale() (30s).
  <prefix>:intel:wd:<nick>            hash, watchdog state per nick
                                      (FND-029): fields last_seen and
                                      last_progress (unix seconds) and
                                      claimed_jobs (comma-separated job
                                      ids, jobs.py field style).
                                      Alert dedupe keys (FND-029, the
                                      other half of the key shape):
                                      presence-stall:<nick>:<job>,
                                      progress-stall:<nick>:<job>,
                                      lease-risk:<nick>:<job>,
                                      dead-dep:<job>:<dep>,
                                      missing-dep:<job>:<dep>,
                                      file-collision:<job>:<job>:<path>,
                                      attempt-warning:<job>,
                                      attempt-exhaustion:<job>,
                                      silent-room[:<room>],
                                      budget-warning:<lane>,
                                      system-failure:<unit>,
                                      worker-restart:<nick>:<job>.
                                      One live record per key (WDG-013);
                                      the store id defaults to the
                                      dedupe key (WDG-010). Journal
                                      dedupe keys (ladder:<job>:<rung>,
                                      baton:<job>, park:<job>) live in
                                      their own modules, not here.
  <prefix>:intel:spend                list, the Spark spend ledger
                                      (FND-007): one JSON entry per
                                      served call, {ts, lane_feature,
                                      tokens_in, tokens_out, est_cost,
                                      usage}, oldest first. usage is
                                      "reported" | "estimated" |
                                      "unreported"; when a completion
                                      carries no token counts (agent
                                      transport), tokens and est_cost
                                      are null — never fabricated.

Records are written and read through relay_common (api_get / api_post /
bus_push), the same REST surface every other module in the repo uses,
so the test suite's FakeUpstash covers this module unchanged. No TTLs
are set here: record retention is a caller decision, not a store one.
"""
import hashlib
import json
import time
import urllib.parse

import relay_common as rc

try:
    from . import thresholds
except ImportError:  # direct module load, not via the intel package
    import thresholds


def _prefix():
    return rc.key_prefix()


# --- key layout ---------------------------------------------------------

def brief_key(room, ts):
    """Redis key for the brief record of `room` generated at `ts`."""
    clean = rc.clean_room(room) or "main"
    return f"{_prefix()}:intel:brief:{clean}:{int(ts)}"


def alert_key(alert_id):
    """Redis key for an alert record."""
    q = urllib.parse.quote(str(alert_id), safe="")
    return f"{_prefix()}:intel:alert:{q}"


def dispatch_key(dispatch_id):
    """Redis key for a dispatch (plan) record."""
    q = urllib.parse.quote(str(dispatch_id), safe="")
    return f"{_prefix()}:intel:dispatch:{q}"


def wd_key(nick):
    """Redis key for a nick's watchdog state hash."""
    q = urllib.parse.quote(str(nick), safe="")
    return f"{_prefix()}:intel:wd:{q}"


def spend_key():
    """Redis key for the Spark spend ledger list."""
    return f"{_prefix()}:intel:spend"


# --- string records (brief / alert / dispatch) --------------------------

def _put_record(key, record):
    rc.api_post(f"set/{key}", json.dumps(record, sort_keys=True))
    return key


def _get_record(key):
    raw = json.loads(rc.api_get(f"get/{key}")).get("result")
    if not raw:
        return None
    try:
        rec = json.loads(raw)
    except ValueError:
        return None
    return rec if isinstance(rec, dict) else None


def put_brief(room, ts, record):
    """Store a brief record dict; returns its Redis key."""
    return _put_record(brief_key(room, ts), record)


def get_brief(room, ts):
    """Return the brief record dict for (room, ts), or None."""
    return _get_record(brief_key(room, ts))


def put_alert(alert_id, record):
    """Store an alert record dict; returns its Redis key.

    Raw storage, unchanged by WDG-010: callers that want the
    validated WDG-010 shape should use write_alert() instead.
    """
    return _put_record(alert_key(alert_id), record)


# --- alert records (WDG-010) --------------------------------------------

ALERT_SEVERITIES = ("critical", "warning", "info")

# WDG-014 lifecycle statuses, in order: open -> acknowledged -> resolved.
ALERT_STATUSES = ("open", "acknowledged", "resolved")

ALERT_REQUIRED_FIELDS = ("id", "kind", "severity", "room", "subjects",
                         "explanation", "suggested_fix", "created_at",
                         "resolved_at", "dedupe_key")


def validate_alert(record):
    """Validate a WDG-010 alert record; raise ValueError if invalid.

    A record is valid when it is a dict carrying every required
    field: id, kind, severity, room, explanation, suggested_fix
    and dedupe_key are non-empty strings, severity is one of
    critical/warning/info (the WDG-024 mapping), subjects is a
    non-empty list of non-empty strings, created_at is an int
    timestamp, and resolved_at is null (open) or an int
    timestamp. Extra detector evidence fields are allowed and
    ignored by validation. Returns the record unchanged.
    """
    if not isinstance(record, dict):
        raise ValueError("alert record must be a dict")
    missing = [f for f in ALERT_REQUIRED_FIELDS if f not in record]
    if missing:
        raise ValueError(
            "alert record missing required fields: "
            + ", ".join(missing))
    for field in ("id", "kind", "severity", "room", "explanation",
                  "suggested_fix", "dedupe_key"):
        value = record[field]
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"alert record field {field!r} must be a "
                "non-empty string")
    if record["severity"] not in ALERT_SEVERITIES:
        raise ValueError(
            "alert record severity must be one of "
            + ", ".join(ALERT_SEVERITIES))
    subjects = record["subjects"]
    if (not isinstance(subjects, list) or not subjects
            or any(not isinstance(s, str) or not s for s in subjects)):
        raise ValueError(
            "alert record subjects must be a non-empty list "
            "of non-empty strings")
    if isinstance(record["created_at"], bool) or not isinstance(
            record["created_at"], int):
        raise ValueError("alert record created_at must be an int")
    resolved = record["resolved_at"]
    if resolved is not None and (
            isinstance(resolved, bool)
            or not isinstance(resolved, int)):
        raise ValueError(
            "alert record resolved_at must be null or an int")
    # WDG-014 lifecycle fields, validated only when present so
    # records stored before WDG-014 (no status field) still read
    # and validate: build_alert_record always writes them.
    status = record.get("status")
    if status is not None and status not in ALERT_STATUSES:
        raise ValueError(
            "alert record status must be one of "
            + ", ".join(ALERT_STATUSES))
    acknowledged = record.get("acknowledged_at")
    if acknowledged is not None and (
            isinstance(acknowledged, bool)
            or not isinstance(acknowledged, int)):
        raise ValueError(
            "alert record acknowledged_at must be null or an int")
    if status == "open" and (resolved is not None
                             or acknowledged is not None):
        raise ValueError(
            "alert record status 'open' requires null "
            "acknowledged_at and resolved_at")
    if status == "acknowledged" and (
            acknowledged is None or resolved is not None):
        raise ValueError(
            "alert record status 'acknowledged' requires an "
            "acknowledged_at and a null resolved_at")
    if status == "resolved" and resolved is None:
        raise ValueError(
            "alert record status 'resolved' requires a resolved_at")
    return record


def alert_status(record):
    """WDG-014: the lifecycle status of a record, legacy-safe.

    A record carrying status reports it verbatim; a record
    stored before WDG-014 derives it from its timestamps:
    resolved_at set means resolved, acknowledged_at set means
    acknowledged, otherwise open. Returns None for a record
    that is not a dict.
    """
    if not isinstance(record, dict):
        return None
    status = record.get("status")
    if status in ALERT_STATUSES:
        return status
    if record.get("resolved_at") is not None:
        return "resolved"
    if record.get("acknowledged_at") is not None:
        return "acknowledged"
    return "open"


def _alert_subjects(detector_alert):
    """Subjects for a detector alert dict, in a stable order.

    Detector dicts name their subjects in their own fields
    (nick, job, dep, other_job, shared_path, claimed_jobs);
    the record's subjects list collects those names, each
    once, in that order, so a reader can tell at a glance
    who and what the alert is about without knowing each
    detector's field layout. A detector dict that already
    carries a subjects list keeps it verbatim.
    """
    existing = detector_alert.get("subjects")
    if isinstance(existing, list):
        return list(existing)
    subjects = []
    for field in ("nick", "job", "dep", "other_job", "shared_path"):
        value = detector_alert.get(field)
        if isinstance(value, str) and value and value not in subjects:
            subjects.append(value)
    claimed = detector_alert.get("claimed_jobs")
    if isinstance(claimed, (list, tuple)):
        for job_id in claimed:
            value = str(job_id)
            if value and value not in subjects:
                subjects.append(value)
    return subjects


def build_alert_record(detector_alert, room="main", alert_id=None,
                       now=None):
    """Build a WDG-010 record from a watchdog detector dict.

    The detector dict supplies kind, severity, explanation,
    suggested_fix, dedupe_key and created_at; this function
    adds id (explicit alert_id, else the dedupe_key — one
    record per dedupe key, which is the seat WDG-013 dedupe
    keys off), room (cleaned like brief_key, default
    "main"), subjects (derived from the detector's nick/job/
    dep/other_job/shared_path/claimed_jobs fields),
    status "open" with acknowledged_at and resolved_at None
    (WDG-014), and last_seen (the record's
    created_at, unless the detector already carried a valid
    int last_seen). Nothing is invented: a missing kind,
    severity, explanation, suggested_fix or dedupe_key
    fails validation with ValueError instead of being filled
    in. Detector evidence fields ride along untouched.
    """
    if not isinstance(detector_alert, dict):
        raise ValueError("detector alert must be a dict")
    record = dict(detector_alert)
    record["id"] = alert_id or detector_alert.get("id") \
        or detector_alert.get("dedupe_key")
    raw_room = room if room is not None else detector_alert.get("room")
    record["room"] = rc.clean_room(raw_room) or "main"
    record["subjects"] = _alert_subjects(detector_alert)
    if record.get("created_at") is None:
        record["created_at"] = int(time.time() if now is None else now)
    # WDG-014: every fresh occurrence starts open, whatever the
    # detector dict carried — a re-fire after resolve is a new
    # incident, not a continuation of the resolved one.
    record["status"] = "open"
    record["acknowledged_at"] = None
    record["resolved_at"] = None
    last_seen = record.get("last_seen")
    if isinstance(last_seen, bool) or not isinstance(last_seen, int):
        record["last_seen"] = record["created_at"]
    return validate_alert(record)


def write_alert(detector_alert, room="main", alert_id=None, now=None):
    """Validate a detector alert and store it; returns the record.

    This is the watchdog's writer (WDG-010): tick() returns
    detector dicts, and a caller passes each one here (or as
    tick's emit callback) to persist it as a validated alert
    record under muse-bus:intel:alert:<id>. The returned
    record is exactly what get_alert(id) reads back.

    WDG-013 dedupe: one live record per id (which defaults
    to the dedupe_key). When an open record with the same id
    already exists and the new report lands inside
    thresholds.ALERT_DEDUPE_COOLDOWN_MINUTES of that
    record's last_seen, no new alert is created: the stored
    record is returned with only last_seen advanced to the
    new report's time (original created_at, explanation and
    evidence stand — the alert is the same ongoing incident,
    re-reported). A report at or past the cooldown, or
    re-firing after the record resolved, starts a fresh
    occurrence: the new record replaces the old one under
    the same id. A report older than last_seen (clock skew)
    never moves last_seen backwards; the stored record is
    returned unchanged.
    """
    record = build_alert_record(detector_alert, room=room,
                                alert_id=alert_id, now=now)
    existing = get_alert(record["id"])
    if existing is not None and existing.get("resolved_at") is None:
        last = existing.get("last_seen")
        if isinstance(last, bool) or not isinstance(last, int):
            last = existing.get("created_at")
        if isinstance(last, int) and not isinstance(last, bool):
            cooldown = thresholds.ALERT_DEDUPE_COOLDOWN_MINUTES * 60
            if record["created_at"] - last < cooldown:
                if record["created_at"] > last:
                    updated = dict(existing)
                    updated["last_seen"] = record["created_at"]
                    # WDG-014: a re-fired acknowledged alert
                    # keeps its status; a legacy record with no
                    # status field is open (it is unresolved).
                    updated.setdefault("status", "open")
                    updated.setdefault("acknowledged_at", None)
                    put_alert(updated["id"], updated)
                    _index_alert(updated)
                    return updated
                return existing
    put_alert(record["id"], record)
    _index_alert(record)
    return record


def get_alert(alert_id):
    """Return the alert record dict for alert_id, or None."""
    return _get_record(alert_key(alert_id))


def alert_index_key():
    """Redis key for the WDG-023 alert history index."""
    return f"{_prefix()}:intel:alert:index"


def _index_alert(record):
    """Add a validated alert record to the history index (WDG-023).

    The index member is the alert id, scored by the current
    occurrence's created_at, so query_alerts() can enumerate
    history without a key scan (the relay surface has none).
    A record with no usable created_at is stored but not
    indexed; query callers never see it, rather than seeing
    it in the wrong order.
    """
    created = record.get("created_at")
    if isinstance(created, bool) or not isinstance(created, int):
        return
    q = urllib.parse.quote(str(record["id"]), safe="")
    rc.api_get(f"zadd/{alert_index_key()}/{created}/{q}")


def query_alerts(room=None, since=None, kind=None):
    """WDG-023: alert history query for briefs and the dashboard.

    Returns validated alert records matching every filter given,
    oldest first: room matches the record's cleaned room,
    kind matches the record's kind exactly, since keeps only
    records created at or after the unix timestamp. No filters
    returns the whole indexed history. Index entries whose
    record is missing or unparseable are skipped, never fatal:
    the index is a best-effort enumeration, not the record
    itself. Records written via raw put_alert() are not
    indexed and do not appear here; write_alert() is the
    queryable writer.
    """
    data = json.loads(rc.api_get(f"zrange/{alert_index_key()}/0/-1"))
    ids = data.get("result") or []
    if not ids:
        return []
    keys = "/".join(alert_key(i) for i in ids)
    data = json.loads(rc.api_get(f"mget/{keys}"))
    raws = data.get("result") or []
    clean_room = rc.clean_room(room) if room is not None else None
    out = []
    for raw in raws:
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        if clean_room is not None and record.get("room") != clean_room:
            continue
        if kind is not None and record.get("kind") != kind:
            continue
        if since is not None:
            created = record.get("created_at")
            if isinstance(created, bool) or not isinstance(created, int):
                continue
            if created < since:
                continue
        out.append(record)
    out.sort(key=lambda r: r.get("created_at") or 0)
    return out


# --- watchdog status line (WDG-028) ------------------------------------

def watchdog_status_key(room, ts):
    """Redis key for the watchdog status record of `room` at `ts`."""
    clean = rc.clean_room(room) or "main"
    return f"{_prefix()}:intel:watchdog_status:{clean}:{int(ts)}"


def build_watchdog_status(records, room="main", ts=None):
    """WDG-028: the watchdog status line, as a store record.

    Takes alert records (as query_alerts() returns them, or any
    dicts in that shape) and returns {room, ts, counts, open,
    resolved, total, top_alert, line}. counts covers unresolved
    records only, by severity — a resolved alert is history,
    not something the morning brief should still count as
    live; resolved records are counted separately in resolved,
    and total counts every record considered. open counts
    every unresolved record, including any with an unknown
    severity, so the line never hides an alert it could not
    classify. top_alert is the id of the highest-severity
    unresolved record (critical before warning before info),
    earliest created_at first, id as the tie-break; it is
    None when no unresolved record carries a known severity
    (an unknown-severity record is never promoted to top, so
    the brief never headlines an alert it cannot classify).
    Non-dict entries are skipped, never counted. line is the
    one frozen sentence the brief renders: "Watchdog: N
    critical, M warning, K info open" plus the top alert id
    when there is one, or "no open alerts" when there is
    none. ts defaults to now; the caller that stores the
    record (put_watchdog_status) supplies the brief's own
    timestamp so the record and the brief it feeds share it.
    """
    counts = {severity: 0 for severity in ALERT_SEVERITIES}
    rank = {"critical": 0, "warning": 1, "info": 2}
    open_count = 0
    resolved_count = 0
    total = 0
    best = None
    for record in records or []:
        if not isinstance(record, dict):
            continue
        total += 1
        if alert_status(record) == "resolved":
            resolved_count += 1
            continue
        open_count += 1
        severity = record.get("severity")
        if severity not in rank:
            continue
        counts[severity] += 1
        alert_id = record.get("id")
        if not isinstance(alert_id, str) or not alert_id:
            continue
        created = record.get("created_at")
        if isinstance(created, bool) or not isinstance(created, int):
            created = None
        candidate = (rank[severity],
                     created is None,
                     created if created is not None else 0,
                     alert_id)
        if best is None or candidate < best[0]:
            best = (candidate, alert_id)
    top_alert = best[1] if best is not None else None
    line = ("Watchdog: {c} critical, {w} warning, {i} info open"
            .format(c=counts["critical"], w=counts["warning"],
                    i=counts["info"]))
    if top_alert is not None:
        line += f" — top alert: {top_alert}"
    else:
        line += " — no open alerts"
    return {
        "room": rc.clean_room(room) or "main",
        "ts": int(time.time() if ts is None else ts),
        "counts": counts,
        "open": open_count,
        "resolved": resolved_count,
        "total": total,
        "top_alert": top_alert,
        "line": line,
    }


def put_watchdog_status(room, ts, record):
    """Store a watchdog status record dict; returns its key."""
    return _put_record(watchdog_status_key(room, ts), record)


def get_watchdog_status(room, ts):
    """Return the watchdog status record for (room, ts), or None."""
    return _get_record(watchdog_status_key(room, ts))


# --- watchdog boot self-check record (OS-036) --------------------------

def selfcheck_key(room, ts):
    """Redis key for the boot self-check record of `room` at `ts`."""
    clean = rc.clean_room(room) or "main"
    return f"{_prefix()}:intel:wd:selfcheck:{clean}:{int(ts)}"


def put_selfcheck(room, ts, record):
    """Store a boot self-check record dict; returns its key."""
    return _put_record(selfcheck_key(room, ts), record)


def get_selfcheck(room, ts):
    """Return the boot self-check record for (room, ts), or None."""
    return _get_record(selfcheck_key(room, ts))


# --- watchdog boot status line (OS-041) -------------------------------

BOOT_STATUS_STALE_SECONDS = 30


def boot_status_key(room, ts):
    """Redis key for the boot status record of `room` at `ts`."""
    clean = rc.clean_room(room) or "main"
    return f"{_prefix()}:intel:wd:bootstatus:{clean}:{int(ts)}"


def build_boot_status(units, workers_alive, alerts, room="main",
                      ts=None):
    """OS-041: the watchdog status line for the boot screen, as a
    store record Rowan's boot checklist (OS-043) renders.

    This is live health, not the brief's alert summary (WDG-028):
    units is a list of {unit, state} dicts (state "active" counts
    up, anything else counts down and is named in units_down);
    workers_alive is the list of nicks currently present (from
    the snapshot presence list the stall detectors already use),
    deduplicated in order; alerts is the alert store's records
    in query_alerts() shape. last_alert is the most recently
    created unresolved record (created_at max, id as tie-break)
    as {id, severity, created_at}, or None when no unresolved
    record carries a usable id — "last" means latest, where
    WDG-028's top_alert means highest-severity. Resolved
    records are history, not live health, and non-dict entries
    are skipped, never counted. line is the one frozen sentence
    the checklist renders: "Boot: N/M units up, W workers alive"
    plus " — down: <units>" when any unit is down, plus
    " — last alert: <id> (<severity>)" or " — no open alerts".
    The record carries no staleness verdict of its own: the
    checklist decides freshness with boot_status_is_stale(),
    so a line older than BOOT_STATUS_STALE_SECONDS is never
    trusted as current health — a killed unit can hide behind
    an old green line for at most 30 seconds.
    """
    units_up = 0
    units_total = 0
    units_down = []
    for entry in units or []:
        if not isinstance(entry, dict):
            continue
        units_total += 1
        name = entry.get("unit")
        if entry.get("state") == "active":
            units_up += 1
        elif isinstance(name, str) and name:
            units_down.append(name)
    workers = []
    for nick in workers_alive or []:
        if isinstance(nick, str) and nick and nick not in workers:
            workers.append(nick)
    last = None
    for record in alerts or []:
        if not isinstance(record, dict):
            continue
        if alert_status(record) == "resolved":
            continue
        alert_id = record.get("id")
        if not isinstance(alert_id, str) or not alert_id:
            continue
        created = record.get("created_at")
        if isinstance(created, bool) or not isinstance(created, int):
            created = None
        candidate = (created is None,
                     created if created is not None else 0,
                     alert_id)
        if last is None or candidate > last[0]:
            last = (candidate, {"id": alert_id,
                                "severity": record.get("severity"),
                                "created_at": created})
    last_alert = last[1] if last is not None else None
    line = (f"Boot: {units_up}/{units_total} units up, "
            f"{len(workers)} workers alive")
    if units_down:
        line += " — down: " + ", ".join(units_down)
    if last_alert is not None:
        line += (f" — last alert: {last_alert['id']} "
                 f"({last_alert['severity']})")
    else:
        line += " — no open alerts"
    return {
        "room": rc.clean_room(room) or "main",
        "ts": int(time.time() if ts is None else ts),
        "units_up": units_up,
        "units_total": units_total,
        "units_down": units_down,
        "workers_alive": workers,
        "workers_count": len(workers),
        "last_alert": last_alert,
        "line": line,
    }


def boot_status_is_stale(record, now=None):
    """OS-041: is this boot status record too old to trust.

    Stale when now - ts exceeds BOOT_STATUS_STALE_SECONDS
    (30s): a record rendered 30s ago is still fresh at exactly
    30s, stale at 31s. A record with no usable ts is stale —
    the checklist must never render undated health as live.
    """
    if not isinstance(record, dict):
        return True
    ts = record.get("ts")
    if isinstance(ts, bool) or not isinstance(ts, int):
        return True
    now = int(time.time() if now is None else now)
    return now - ts > BOOT_STATUS_STALE_SECONDS


def put_boot_status(room, ts, record):
    """Store a boot status record dict; returns its key."""
    return _put_record(boot_status_key(room, ts), record)


def get_boot_status(room, ts):
    """Return the boot status record for (room, ts), or None."""
    return _get_record(boot_status_key(room, ts))


def acknowledge_alert(alert_id, now=None):
    """WDG-014: move an alert open -> acknowledged; return it.

    Sets status "acknowledged" and acknowledged_at (now, or the
    current time); resolved_at stays null. Acknowledging an
    already-acknowledged alert is idempotent — the record is
    returned unchanged, acknowledged_at untouched. Returns None
    when no such alert exists. Raises ValueError when the alert
    is already resolved: a resolved incident is closed, not
    acknowledged, and the stored record is left untouched.
    """
    record = get_alert(alert_id)
    if record is None:
        return None
    status = alert_status(record)
    if status == "resolved":
        raise ValueError("cannot acknowledge a resolved alert")
    if status == "acknowledged":
        return record
    updated = dict(record)
    updated["status"] = "acknowledged"
    updated["acknowledged_at"] = int(
        time.time() if now is None else now)
    updated.setdefault("resolved_at", None)
    validate_alert(updated)
    put_alert(updated["id"], updated)
    return updated


def resolve_alert(alert_id, now=None):
    """WDG-014: move an alert open/acknowledged -> resolved.

    Sets status "resolved" and resolved_at (now, or the current
    time); an acknowledged_at already on the record is kept, so
    the record shows the full walk. Resolving an already-
    resolved alert is idempotent — the record is returned
    unchanged. Returns None when no such alert exists.
    """
    record = get_alert(alert_id)
    if record is None:
        return None
    if alert_status(record) == "resolved":
        return record
    updated = dict(record)
    updated["status"] = "resolved"
    updated["resolved_at"] = int(time.time() if now is None else now)
    updated.setdefault("acknowledged_at", None)
    validate_alert(updated)
    put_alert(updated["id"], updated)
    return updated


def auto_resolve_cleared(known_ids, live_ids, now=None):
    """WDG-014: auto-resolve the alerts a tick no longer fires.

    known_ids are the alert ids the caller is tracking (for
    example, every id previously written for a room); live_ids
    are the ids (or alert dicts, whose id or dedupe_key is
    used) from the latest tick. Every known alert that is not
    live and not already resolved is resolved at now, and the
    resolved records are returned in known_ids order. A known
    id with no stored record is skipped, never invented. This
    is the auto-resolve half of the lifecycle: the detector
    firing is the condition, so a tick that stops firing it
    means the condition cleared — the same mechanism behind
    WDG-004's lease-risk note that a swept job stops firing.
    """
    live = set()
    for item in live_ids or []:
        if isinstance(item, dict):
            value = item.get("id") or item.get("dedupe_key")
        else:
            value = item
        if value is not None:
            live.add(str(value))
    resolved = []
    for alert_id in known_ids or []:
        if str(alert_id) in live:
            continue
        record = get_alert(alert_id)
        if record is None or alert_status(record) == "resolved":
            continue
        resolved.append(resolve_alert(alert_id, now=now))
    return resolved


# --- notification records (notification system, 2026-10-28) -------------

NOTIFY_SEVERITIES = ALERT_SEVERITIES
NOTIFY_STATUSES = ALERT_STATUSES

NOTIFY_REQUIRED_FIELDS = ("id", "source", "severity", "topic", "text",
                          "target", "room", "created_at", "last_seen",
                          "count", "dedupe_key", "status",
                          "acknowledged_at", "acknowledged_by",
                          "resolved_at")


def notify_key(notify_id):
    """Redis key for a notification record."""
    q = urllib.parse.quote(str(notify_id), safe="")
    return f"{_prefix()}:intel:notify:{q}"


def notify_index_key():
    """Redis key for the notification history index."""
    return f"{_prefix()}:intel:notify:index"


def put_notify(notify_id, record):
    """Store a notification record dict; returns its Redis key.

    Raw storage: callers that want the validated shape should use
    write_notify() instead.
    """
    return _put_record(notify_key(notify_id), record)


def get_notify(notify_id):
    """Return the notification record dict for notify_id, or None."""
    return _get_record(notify_key(notify_id))


def notify_status(record):
    """Lifecycle status of a notification record (alerts' rules)."""
    return alert_status(record)


def validate_notify(record):
    """Validate a notification record; raise ValueError if invalid.

    Required: id, source, topic, text and room are non-empty
    strings; severity is one of NOTIFY_SEVERITIES; target is a
    non-empty string ("all" or a nick); created_at and last_seen
    are int timestamps; count is a positive int; dedupe_key is a
    string or None; status is one of NOTIFY_STATUSES with the
    same timestamp consistency rules as alert records, plus
    acknowledged_by a string or None. Returns the record.
    """
    if not isinstance(record, dict):
        raise ValueError("notification record must be a dict")
    missing = [f for f in NOTIFY_REQUIRED_FIELDS if f not in record]
    if missing:
        raise ValueError(
            "notification record missing required fields: "
            + ", ".join(missing))
    for field in ("id", "source", "topic", "text", "target", "room"):
        value = record[field]
        if not isinstance(value, str) or not value:
            raise ValueError(
                f"notification record field {field!r} must be a "
                "non-empty string")
    if record["severity"] not in NOTIFY_SEVERITIES:
        raise ValueError(
            "notification record severity must be one of "
            + ", ".join(NOTIFY_SEVERITIES))
    for field in ("created_at", "last_seen"):
        value = record[field]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(
                f"notification record {field} must be an int")
    count = record["count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("notification record count must be a positive int")
    if record["dedupe_key"] is not None and not isinstance(
            record["dedupe_key"], str):
        raise ValueError(
            "notification record dedupe_key must be a string or null")
    if record["status"] not in NOTIFY_STATUSES:
        raise ValueError(
            "notification record status must be one of "
            + ", ".join(NOTIFY_STATUSES))
    for field in ("acknowledged_at", "resolved_at"):
        value = record[field]
        if value is not None and (
                isinstance(value, bool) or not isinstance(value, int)):
            raise ValueError(
                f"notification record {field} must be null or an int")
    if record["acknowledged_by"] is not None and not isinstance(
            record["acknowledged_by"], str):
        raise ValueError(
            "notification record acknowledged_by must be a string or null")
    status = record["status"]
    if status == "open" and (record["resolved_at"] is not None
                             or record["acknowledged_at"] is not None):
        raise ValueError(
            "notification record status 'open' requires null "
            "acknowledged_at and resolved_at")
    if status == "acknowledged" and (
            record["acknowledged_at"] is None
            or record["resolved_at"] is not None):
        raise ValueError(
            "notification record status 'acknowledged' requires an "
            "acknowledged_at and a null resolved_at")
    if status == "resolved" and record["resolved_at"] is None:
        raise ValueError(
            "notification record status 'resolved' requires a resolved_at")
    return record


def _notify_id(source, topic, text, dedupe_key, created_at):
    """Deterministic notification id.

    With a dedupe_key the id keys off it alone (one live record
    per dedupe key, the WDG-013 seat). Without one it keys off
    source|topic|text|created_at, so an identical repeat inside
    the same second is the same notification, not a duplicate.
    """
    if dedupe_key:
        basis = "key:" + str(dedupe_key)
    else:
        basis = "auto:" + "|".join(
            [str(source), str(topic), str(text), str(created_at)])
    return "ntf-" + hashlib.sha256(basis.encode("utf-8")).hexdigest()[:16]


def build_notify_record(source, severity, text, topic="general",
                        target="all", room="main", dedupe_key=None,
                        notify_id=None, now=None):
    """Build a fresh open notification record; validates it.

    Nothing is invented: source, text and topic must be given,
    severity must be a known severity. A re-fire after resolve
    starts from this fresh shape (status open, count 1).
    """
    created = int(time.time() if now is None else now)
    record = {
        "id": notify_id or _notify_id(source, topic, text, dedupe_key,
                                      created),
        "source": source,
        "severity": severity,
        "topic": topic,
        "text": text,
        "target": target or "all",
        "room": rc.clean_room(room) or "main",
        "created_at": created,
        "last_seen": created,
        "count": 1,
        "dedupe_key": dedupe_key,
        "status": "open",
        "acknowledged_at": None,
        "acknowledged_by": None,
        "resolved_at": None,
    }
    return validate_notify(record)


def _index_notify(record):
    """Add a validated notification record to the history index."""
    created = record.get("created_at")
    if isinstance(created, bool) or not isinstance(created, int):
        return
    q = urllib.parse.quote(str(record["id"]), safe="")
    rc.api_get(f"zadd/{notify_index_key()}/{created}/{q}")


def write_notify(source, severity, text, topic="general", target="all",
                 room="main", dedupe_key=None, notify_id=None, now=None):
    """Validate a notification and store it; returns the record.

    Dedupe: when an unresolved record with the same id already
    exists, no duplicate is created — the stored record is
    returned with last_seen advanced to now and count bumped by
    one (its acknowledged status stands). A resolved record that
    fires again starts a fresh open occurrence under the same
    id, exactly like alerts (WDG-013). A report older than
    last_seen (clock skew) returns the stored record unchanged.
    """
    record = build_notify_record(
        source, severity, text, topic=topic, target=target, room=room,
        dedupe_key=dedupe_key, notify_id=notify_id, now=now)
    existing = get_notify(record["id"])
    if existing is not None and existing.get("resolved_at") is None:
        last = existing.get("last_seen")
        if isinstance(last, int) and not isinstance(last, bool):
            if record["created_at"] < last:
                return existing
            updated = dict(existing)
            updated["last_seen"] = record["created_at"]
            updated["count"] = (existing.get("count") or 1) + 1
            updated.setdefault("status", "open")
            updated.setdefault("acknowledged_at", None)
            updated.setdefault("acknowledged_by", None)
            validate_notify(updated)
            put_notify(updated["id"], updated)
            _index_notify(updated)
            return updated
    put_notify(record["id"], record)
    _index_notify(record)
    return record


def query_notify(room=None, since=None, severity=None, status=None,
                 target=None):
    """Notification history query for briefs, dashboard and CLI.

    Returns validated records matching every filter given,
    oldest first. Index entries whose record is missing or
    unparseable are skipped, never fatal. Records written via
    raw put_notify() are not indexed and do not appear here.
    """
    data = json.loads(rc.api_get(f"zrange/{notify_index_key()}/0/-1"))
    ids = data.get("result") or []
    if not ids:
        return []
    keys = "/".join(notify_key(i) for i in ids)
    data = json.loads(rc.api_get(f"mget/{keys}"))
    raws = data.get("result") or []
    clean = rc.clean_room(room) if room is not None else None
    out = []
    for raw in raws:
        if not raw:
            continue
        try:
            record = json.loads(raw)
        except ValueError:
            continue
        if not isinstance(record, dict):
            continue
        if clean is not None and record.get("room") != clean:
            continue
        if severity is not None and record.get("severity") != severity:
            continue
        if target is not None and record.get("target") != target:
            continue
        if status is not None and notify_status(record) != status:
            continue
        if since is not None:
            created = record.get("created_at")
            if isinstance(created, bool) or not isinstance(created, int):
                continue
            if created < since:
                continue
        out.append(record)
    out.sort(key=lambda r: r.get("created_at") or 0)
    return out


def acknowledge_notify(notify_id, by=None, now=None):
    """Move a notification open -> acknowledged; return it.

    Stamps acknowledged_at and acknowledged_by (a nick string,
    or None when not supplied). Idempotent on an already-
    acknowledged record. Returns None when no such record
    exists. Raises ValueError on a resolved record, mirroring
    acknowledge_alert.
    """
    record = get_notify(notify_id)
    if record is None:
        return None
    status = notify_status(record)
    if status == "resolved":
        raise ValueError("cannot acknowledge a resolved notification")
    if status == "acknowledged":
        return record
    updated = dict(record)
    updated["status"] = "acknowledged"
    updated["acknowledged_at"] = int(
        time.time() if now is None else now)
    updated["acknowledged_by"] = by
    updated.setdefault("resolved_at", None)
    validate_notify(updated)
    put_notify(updated["id"], updated)
    return updated


def resolve_notify(notify_id, now=None):
    """Move a notification open/acknowledged -> resolved.

    Idempotent on an already-resolved record. Returns None when
    no such record exists, mirroring resolve_alert.
    """
    record = get_notify(notify_id)
    if record is None:
        return None
    if notify_status(record) == "resolved":
        return record
    updated = dict(record)
    updated["status"] = "resolved"
    updated["resolved_at"] = int(time.time() if now is None else now)
    updated.setdefault("acknowledged_at", None)
    updated.setdefault("acknowledged_by", None)
    validate_notify(updated)
    put_notify(updated["id"], updated)
    return updated


def put_dispatch(dispatch_id, record):
    """Store a dispatch record dict; returns its Redis key."""
    return _put_record(dispatch_key(dispatch_id), record)


def get_dispatch(dispatch_id):
    """Return the dispatch record dict for dispatch_id, or None."""
    return _get_record(dispatch_key(dispatch_id))


# --- watchdog state (hash per nick, FND-029) ----------------------------

def wd_beat(nick, last_seen=None, last_progress=None, claimed_jobs=None):
    """Update a nick's watchdog state hash; returns the key.

    Only the fields given are written. claimed_jobs is an iterable of
    job ids, stored comma-separated (the jobs.py field style).
    """
    fields = []
    if last_seen is not None:
        fields += ["last_seen", str(int(last_seen))]
    if last_progress is not None:
        fields += ["last_progress", str(int(last_progress))]
    if claimed_jobs is not None:
        fields += ["claimed_jobs", ",".join(str(j) for j in claimed_jobs)]
    if not fields:
        raise ValueError("wd_beat: no fields to write")
    key = wd_key(nick)
    path = f"hset/{key}/" + "/".join(
        urllib.parse.quote(f, safe="") for f in fields)
    rc.api_get(path)
    return key


def wd_beat_key():
    """Redis key for the watchdog's own self-heartbeat (WDG-016).

    Distinct from wd_key(nick): that is per-worker state, this is
    the watchdog itself saying "I ticked". The dashboard (bus.html,
    DSH-015) reads exactly this key and renders alive/stale from
    its ts; the value shape is {"ts": <Unix int>}, the shape its
    beatTsOf accepts.
    """
    return f"{_prefix()}:intel:wd:beat"


def wd_self_beat(now=None):
    """Write the watchdog self-heartbeat; returns the key (WDG-016).

    Sets muse-bus:intel:wd:beat to {"ts": now} with a TTL of
    thresholds.WATCHDOG_BEAT_TTL_SECONDS, so a dead watchdog's
    beat expires on its own instead of lingering as a stale
    "alive". now defaults to the current time. This is the
    store half of the beat; the loop half is tick's beat
    callback in intel/watchdog.py — pass this function as that
    callback and every tick renews the key.
    """
    stamp = int(time.time() if now is None else now)
    value = json.dumps({"ts": stamp}, sort_keys=True)
    key = wd_beat_key()
    path = (f"setex/{key}/{thresholds.WATCHDOG_BEAT_TTL_SECONDS}/"
            + urllib.parse.quote(value, safe=""))
    rc.api_get(path)
    return key


def wd_self_beat_age(now=None):
    """Age of the watchdog self-heartbeat in seconds, or None.

    None means no beat is readable — never written, expired, or
    unparseable — never a made-up age: a caller that renders
    "watchdog alive" needs a real beat, and a caller that
    renders "watchdog silent" needs the absence, not a zero.
    This is the watchdog_age_seconds half of the dashboard
    payload for any Python payload builder (the JS dashboard
    derives the same age from the beat ts itself).
    """
    raw = json.loads(rc.api_get(f"get/{wd_beat_key()}")).get("result")
    if not raw:
        return None
    try:
        record = json.loads(raw)
    except (ValueError, TypeError):
        return None
    stamp = record.get("ts") if isinstance(record, dict) else None
    if not isinstance(stamp, (int, float)) or isinstance(stamp, bool):
        return None
    current = time.time() if now is None else now
    return current - stamp


def wd_get(nick):
    """Return a nick's watchdog state, or None when no state exists.

    Shape: {"last_seen": int|None, "last_progress": int|None,
            "claimed_jobs": [job id, ...]}.
    """
    data = json.loads(rc.api_get(f"hgetall/{wd_key(nick)}"))
    flat = data.get("result") or []
    if not flat:
        return None
    raw = dict(zip(flat[0::2], flat[1::2]))

    def _int(name):
        try:
            return int(raw[name])
        except (KeyError, TypeError, ValueError):
            return None

    jobs = raw.get("claimed_jobs") or ""
    return {
        "last_seen": _int("last_seen"),
        "last_progress": _int("last_progress"),
        "claimed_jobs": [j for j in jobs.split(",") if j],
    }


# --- Spark spend ledger (FND-007) ----------------------------------------

def record_spend(entry):
    """Append one spend entry dict to the ledger; returns the entry.

    The entry is stored as JSON with sorted keys. Ordering is append
    order (oldest first), matching the bus list convention.
    """
    body = json.dumps(entry, sort_keys=True)
    rc.bus_push(body, key=spend_key())
    return entry


def spend_entries(start=0, stop=-1):
    """Return ledger entries as dicts, oldest first.

    Unparseable entries are skipped rather than crashing the reader:
    the ledger is append-only and shared, so one bad line must not
    blind the spend total.
    """
    data = json.loads(rc.api_get(f"lrange/{spend_key()}/{start}/{stop}"))
    out = []
    for raw in data.get("result") or []:
        try:
            entry = json.loads(raw)
        except (ValueError, TypeError):
            continue
        if isinstance(entry, dict):
            out.append(entry)
    return out


def spend_total():
    """Running total of est_cost across the whole spend ledger."""
    total = 0.0
    for entry in spend_entries():
        try:
            total += float(entry.get("est_cost") or 0)
        except (TypeError, ValueError):
            continue
    return total
