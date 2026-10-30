"""intel/watchdog.py — silent-failure detectors (WDG workstream, Milo).

Watches claims, leases, and heartbeats through ingest snapshots and
the per-nick watchdog state in intel.store (muse-bus:intel:wd:<nick>,
FND-029); flags stalled workers, dead dependencies, and file
collisions as alert records with a plain explanation and a suggested
fix. Thresholds live in intel/thresholds.py (FND-030). Watchdog v1
never mutates job state — it alerts; humans (or mos tick) act
(hard rule, MASTER_PLAN).

WDG-001 (this module's loop): tick(snapshot) evaluates every
registered detector over one snapshot and returns the alert dicts
found; an optional emit callback receives each alert. The store
writer is intel.store.write_alert (WDG-010): pass it as emit, or
collect the return value, to persist each alert as a validated
record; nothing is posted anywhere by this loop. The CLI offers
--once (one tick, exit 0) and --loop (repeat until interrupted).
WDG-012's optional Spark polish pass rides tick's polish_client
argument: explanations are rewritten for clarity only when a
client is supplied, and the template text stands whenever Spark
fails or answers empty.

Detectors land one per task in WDG-002..WDG-009 and register
themselves in DETECTORS; the loop itself never hardcodes a
detector. WDG-002 (presence-stall), WDG-003 (progress-stall),
WDG-004 (lease-risk), WDG-005 (dead-dep), WDG-006
(missing-dep), WDG-007 (file-collision), WDG-008
(attempt-exhaustion), and WDG-009 (silent-room, info only)
are registered, so a quiet snapshot still yields zero alerts.
INT-010 adds one more detector outside the WDG-002..WDG-009
series: rejected-dispatch, which turns a worker's REJECTED
refusal line (jobs.py claim verification) into an alert
record, so a refused dispatch is visible in the brief and
the dashboard instead of scrolling past in chat.
Live-room reading waits
on Pax's FND-014 snapshot API (intel/ingest.py is still a
skeleton), so --once reads a snapshot JSON file, or an empty
snapshot when no file is given. WDG-015 announcements: this
loop itself posts nothing to the bus — Dale's posting rule
(never post without his word) means announcements are gated
behind an explicit opt-in. tick()'s optional announce
callback receives one frozen-format ALERT line per new
critical alert and nothing for warnings or info records;
without a callback, lines are only available through
format_announcement()/announcements_for(), i.e. held, not
posted. The caller that owns the bus post (a future live
loop under Dale's approval) supplies the callback; this
module never touches the bus on its own. WDG-016 self-heartbeat:
tick's optional beat callback receives the tick timestamp once per
tick, quiet ticks included — a quiet tick is still a live watchdog,
and the beat is what proves it. The store half is
intel.store.wd_self_beat (key muse-bus:intel:wd:beat, TTL from
intel.thresholds); pass it as the callback and every tick renews
the key the dashboard (bus.html, DSH-015) reads. A failing beat
never fails a tick: the beat is best-effort liveness, and a missed
beat is itself the honest signal (the dashboard goes stale).
WDG-017 tick budget guard: tick() never evaluates unbounded
message history. Messages are walked page by page through
paginate() (digest.py's PAGE shape, oldest first) and the tick
window keeps only the newest thresholds.TICK_MAX_MESSAGES;
older messages are dropped before any detector runs, and the
drop is recorded in the snapshot's tick_window record (same
idea as brief.py's source_window). The cap is verdict-safe:
the only message reader is WDG-009 silent-room, which needs
just the newest message. Jobs, presence, and caps are never
capped — a dropped job could hide a stall or a collision —
and job detectors already evaluate one record at a time,
retaining only alerts plus the small dep index / claimed set.
WDG-025 walk-on tracking: detect_walk_on_workers() is a
standalone tracking function, not a detector — a claimed job
whose claimer was never in the caps registry yields one
tracking record naming nick, job, and last-activity age,
from jobs data alone. It is not in DETECTORS and tick()
never emits it as an alert: WDG-002/WDG-003 skip walk-on
claimers by design, and the tracking record is the
visibility half that keeps those skips honest.
WDG-026 clock skew: every age in a tick is computed from
one resolved "now", never from a mix of clocks. tick()
resolves it in this order: an explicit now argument wins
(the injected clock tests use, and the live caller's
override); else the snapshot's server_time field when it
carries a usable Redis server timestamp (see
resolve_tick_now for the accepted shapes); else the local
wall clock. Detectors never call time.time() themselves —
they take the resolved now — so a skewed local clock
shifts every age in a tick together but can never make
one detector's age come from one clock and another's from
a different one. The documented assumption, when
server_time is absent, is that the local wall clock is
close to the Redis server clock; a snapshot producer that
can read Redis TIME (the future live loop, FND-014)
should stamp server_time on the snapshot it hands tick().
Until then, file snapshots may carry server_time by hand.
WDG-028 watchdog status line: the one-line brief summary of
the alert store lives in intel.store.build_watchdog_status
(counts of unresolved alerts by severity, top alert id, the
frozen line) with its put/get pair, and the template brief
renders that line at the head of its Watch items section
whenever the snapshot's alerts carry severities. The status
record is built from the alert store the brief just queried,
so the brief's counts and the store agree by construction;
the Spark-composed brief and dashboard rendering of the
line are Hana's/Rowan's consumption side, covered by INT-020.
OS-037 journal watch: the watchdog's second loop input, beside
snapshots. journald is the machine's own account of itself
(META_OS.md, crew activity journaling), and a relay unit's
failure there becomes a SYSTEM alert record in the same alert
store the dashboard reads — kind system-failure, subjects the
unit name, no nick and no job, so a unit failure can never be
mistaken for a worker stall. detect_journal_failures() reads
journalctl -o json lines (or already-parsed entry dicts) and
yields one alert per failed unit; journal_watch_tick() is one
loop iteration over those entries, emit-gated like tick().
It is deliberately NOT in DETECTORS: journal entries are not
snapshot data, and a snapshot tick must never wait on
journalctl. The watchdog never restarts a unit itself — under
the OS-034 contract systemd owns process death, so the
suggested fix points at journalctl -u and a unit restart by
the operator, not at watchdog action. Live force-fail proof
needs the test image (no image in this repo); the drill and
tests prove the watchdog half on fixtures.
"""

import argparse
import itertools
import json
import re
import sys
import time
from collections import deque

try:
    from . import thresholds
    from . import explanations
except ImportError:  # direct module load, not via the intel package
    import thresholds
    import explanations

__all__ = ["tick", "main", "DETECTORS", "SEVERITY_BY_KIND",
           "format_announcement",
           "announcements_for", "paginate", "cap_tick_snapshot",
           "resolve_tick_now",
           "detect_presence_stall",
           "detect_progress_stall", "detect_walk_on_workers",
           "detect_lease_risk",
           "detect_dead_dep", "detect_missing_dep",
           "detect_file_collision", "detect_attempt_exhaustion",
           "detect_silent_room", "detect_rejected_dispatch",
           "detect_budget_warning"]


def _last_activity(job):
    """Last known activity timestamp for a claimed job, or None.

    Prefers an explicit progress timestamp when the snapshot carries
    one (last_progress / progress_at / note_ts / last_progress_at),
    else the claim time. last_progress_at is the field the real
    snapshot carries (intel/ingest.py rows use the jobs.py list
    --json shape, INT-003): without it the stall detectors could
    never fire on a real snapshot, only on hand-built ones.
    A job with no timestamp at all yields None: the detector never
    invents an age for it (WDG-002 skips it, it is not a stall).
    """
    for field in ("last_progress", "progress_at", "note_ts",
                  "last_progress_at", "claimed_at"):
        value = job.get(field)
        if isinstance(value, (int, float)):
            return int(value)
    return None


def detect_presence_stall(snapshot, now):
    """WDG-002: presence-stall detector.

    A nick in the caps registry (caps keys) that is absent from the
    current presence list while holding a claimed job, with no
    activity on that job for longer than thresholds.STALL_MINUTES,
    is stalled: present-registry, gone-presence, work unmoving.
    One alert per (nick, job) pair. A nick that is present, has no
    claimed job, is not in caps (a walk-on worker, WDG-025's case),
    or whose job is still fresh yields no alert here — a present
    worker with no progress is WDG-003's case, not this one.
    Walk-on claimers are tracked, not alerted, by
    detect_walk_on_workers (WDG-025).
    """
    snapshot = snapshot or {}
    caps = snapshot.get("caps") or {}
    if not isinstance(caps, dict):
        caps = {}
    presence = snapshot.get("presence") or []
    if not isinstance(presence, (list, tuple, set)):
        presence = []
    present = set(presence)
    jobs = snapshot.get("jobs") or []
    if not isinstance(jobs, (list, tuple)):
        jobs = []
    threshold_seconds = thresholds.STALL_MINUTES * 60
    alerts = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("status") != "claimed":
            continue
        nick = job.get("claim")
        if not nick or nick not in caps or nick in present:
            continue
        last = _last_activity(job)
        if last is None:
            continue
        age = int(now) - last
        if age <= threshold_seconds:
            continue
        job_id = str(job.get("id", ""))
        alerts.append({
            "kind": "presence-stall",
            "severity": "critical",
            "nick": nick,
            "job": job_id,
            "job_title": job.get("title", ""),
            "last_progress_age_seconds": age,
            "last_progress_age_minutes": age // 60,
            "explanation": explanations.render(
                "presence-stall", nick=nick, job=job_id,
                stall_minutes=thresholds.STALL_MINUTES,
                age_minutes=age // 60)[0],
            "suggested_fix": explanations.render(
                "presence-stall", nick=nick, job=job_id,
                stall_minutes=thresholds.STALL_MINUTES,
                age_minutes=age // 60)[1],
            "dedupe_key": f"presence-stall:{nick}:{job_id}",
            "created_at": int(now),
        })
    return alerts


def detect_progress_stall(snapshot, now):
    """WDG-003: progress-stall detector.

    A nick in the caps registry that IS present (heartbeat alive)
    while holding a claimed job with no activity for longer than
    thresholds.PROGRESS_STALL_MINUTES is stuck, not gone: the
    worker lives, the work does not move. One alert per (nick,
    job) pair. Distinct from presence-stall by construction:
    that detector fires only when the nick is absent from
    presence; this one only when the nick is present, so one
    snapshot never yields both kinds for the same job. A nick
    not in caps is WDG-025's walk-on case and is skipped here,
    same as WDG-002 — tracked by detect_walk_on_workers
    instead. A job with no timestamp at all yields no
    alert: the detector never invents an age for it.
    """
    snapshot = snapshot or {}
    caps = snapshot.get("caps") or {}
    if not isinstance(caps, dict):
        caps = {}
    presence = snapshot.get("presence") or []
    if not isinstance(presence, (list, tuple, set)):
        presence = []
    present = set(presence)
    jobs = snapshot.get("jobs") or []
    if not isinstance(jobs, (list, tuple)):
        jobs = []
    threshold_seconds = thresholds.PROGRESS_STALL_MINUTES * 60
    alerts = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("status") != "claimed":
            continue
        nick = job.get("claim")
        if not nick or nick not in caps or nick not in present:
            continue
        last = _last_activity(job)
        if last is None:
            continue
        age = int(now) - last
        if age <= threshold_seconds:
            continue
        job_id = str(job.get("id", ""))
        alerts.append({
            "kind": "progress-stall",
            "severity": "critical",
            "nick": nick,
            "job": job_id,
            "job_title": job.get("title", ""),
            "last_progress_age_seconds": age,
            "last_progress_age_minutes": age // 60,
            "explanation": explanations.render(
                "progress-stall", nick=nick, job=job_id,
                age_minutes=age // 60,
                window_minutes=thresholds.PROGRESS_STALL_MINUTES)[0],
            "suggested_fix": explanations.render(
                "progress-stall", nick=nick, job=job_id,
                age_minutes=age // 60,
                window_minutes=thresholds.PROGRESS_STALL_MINUTES)[1],
            "dedupe_key": f"progress-stall:{nick}:{job_id}",
            "created_at": int(now),
        })
    return alerts


def detect_walk_on_workers(snapshot, now):
    """WDG-025: walk-on worker tracking records.

    A claimed job whose claimer was never in the caps registry
    (a walk-on worker) is tracked from jobs data alone: one
    tracking record per such job, naming the nick, the job,
    and the last-activity age when the job carries a
    timestamp. This is deliberately NOT a detector and NOT
    registered in DETECTORS: WDG-002/WDG-003 skip walk-on
    claimers by design (a worker the registry never saw is
    not a registered worker going silent), and tick() must
    keep returning zero alerts for a walk-on fixture — the
    existing negative tests lock that in. Tracking is not a
    stall verdict: a record is yielded whether the nick is
    present or absent, fresh or stale, because the point is
    visibility, not accusation. A job with no timestamp at
    all still yields a record, with None ages: tracking never
    invents an age for it, same rule as WDG-002. Malformed
    snapshot sections (caps not a dict, jobs not a list)
    yield nothing, never a crash.
    """
    snapshot = snapshot or {}
    caps = snapshot.get("caps") or {}
    if not isinstance(caps, dict):
        caps = {}
    jobs = snapshot.get("jobs") or []
    if not isinstance(jobs, (list, tuple)):
        jobs = []
    records = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("status") != "claimed":
            continue
        nick = job.get("claim")
        if not nick or nick in caps:
            continue
        last = _last_activity(job)
        age = int(now) - last if last is not None else None
        records.append({
            "kind": "walk-on-worker",
            "nick": nick,
            "job": str(job.get("id", "")),
            "job_title": job.get("title", ""),
            "last_progress_age_seconds": age,
            "last_progress_age_minutes": (age // 60
                                           if age is not None
                                           else None),
            "tracked_from": "jobs",
            "created_at": int(now),
        })
    return records


def detect_lease_risk(snapshot, now):
    """WDG-004: lease-risk detector.

    A claimed job whose lease expires within
    thresholds.LEASE_RISK_WINDOW_MINUTES and with no heartbeat in
    the last thresholds.LEASE_RISK_QUIET_MINUTES minutes gets a
    warning alert before expiry — the last chance to renew before
    the sweep requeues it. Severity is warning, not critical
    (WDG-024 mapping): the job is not lost yet, just about to be.

    Last heartbeat: an explicit heartbeat timestamp on the job
    (heartbeat_at / last_heartbeat) wins when present; otherwise
    it is derived, not invented from nothing — a heartbeat renews
    the lease to now + lease (jobs.py cmd_heartbeat), so the last
    heartbeat is lease_until minus the lease duration (the job's
    lease field, else thresholds.LEASE_DEFAULT_SECONDS, the
    jobs.py default). A job with no lease_until yields no alert:
    without an expiry there is nothing to warn about. An already
    expired lease yields no alert either: that is the sweep's
    job, not a warning — and once the sweep requeues the job
    (status back to open) this detector stops firing on it, which
    is the auto-resolve half of the acceptance; the alert
    lifecycle itself lands with WDG-014.

    Caps membership is not required here, unlike WDG-002/WDG-003:
    a lease is job data, and a walk-on worker's lease expiring
    is equally worth warning about (WDG-025's direction).
    """
    snapshot = snapshot or {}
    jobs = snapshot.get("jobs") or []
    if not isinstance(jobs, (list, tuple)):
        jobs = []
    window_seconds = thresholds.LEASE_RISK_WINDOW_MINUTES * 60
    quiet_seconds = thresholds.LEASE_RISK_QUIET_MINUTES * 60
    alerts = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("status") != "claimed":
            continue
        lease_until = job.get("lease_until")
        if not isinstance(lease_until, (int, float)):
            continue
        lease_until = int(lease_until)
        seconds_to_expiry = lease_until - int(now)
        if seconds_to_expiry <= 0 or seconds_to_expiry > window_seconds:
            continue
        heartbeat = None
        for field in ("heartbeat_at", "last_heartbeat"):
            value = job.get(field)
            if isinstance(value, (int, float)):
                heartbeat = int(value)
                break
        if heartbeat is None:
            lease = job.get("lease")
            if not isinstance(lease, (int, float)):
                lease = thresholds.LEASE_DEFAULT_SECONDS
            heartbeat = lease_until - int(lease)
        if int(now) - heartbeat < quiet_seconds:
            continue
        nick = job.get("claim") or ""
        job_id = str(job.get("id", ""))
        alerts.append({
            "kind": "lease-risk",
            "severity": "warning",
            "nick": nick,
            "job": job_id,
            "job_title": job.get("title", ""),
            "seconds_to_expiry": seconds_to_expiry,
            "minutes_to_expiry": seconds_to_expiry // 60,
            "last_heartbeat_age_seconds": int(now) - heartbeat,
            "explanation": explanations.render(
                "lease-risk", job=job_id, nick=nick,
                minutes_to_expiry=seconds_to_expiry // 60,
                quiet_minutes=thresholds.LEASE_RISK_QUIET_MINUTES)[0],
            "suggested_fix": explanations.render(
                "lease-risk", job=job_id, nick=nick,
                minutes_to_expiry=seconds_to_expiry // 60,
                quiet_minutes=thresholds.LEASE_RISK_QUIET_MINUTES)[1],
            "dedupe_key": f"lease-risk:{nick}:{job_id}",
            "created_at": int(now),
        })
    return alerts


def _parse_deps(value):
    """Dep ids off a job, in jobs.py's comma-separated form.

    jobs.py stores deps as one comma-separated string (FND-009);
    a list form is accepted too so snapshots built by hand do
    not silently drop deps. Empty entries are dropped.
    """
    if isinstance(value, (list, tuple)):
        return [str(d).strip() for d in value if str(d).strip()]
    if isinstance(value, str):
        return [d.strip() for d in value.split(",") if d.strip()]
    return []


def detect_dead_dep(snapshot, now):
    """WDG-005: dead-dependency detector.

    An open or claimed job whose dependency is blocked or
    failed-final cannot proceed until a human unblocks or
    replaces that dep. One alert per (job, dep) pair, severity
    critical (WDG-024 mapping). The blocking reason is the
    dep's note verbatim when the dep carries one — jobs.py
    cmd_blocked stamps the reason into note — otherwise the
    dep's status itself (a failed-final dep usually carries no
    note; its status is the reason). No age gate: this mirrors
    jobs.py's FND-012 DEP_DEAD sweep report exactly, where the
    dep's blocked/failed-final state IS the threshold (the
    blocked_at stamp exists for future age tuning in WDG-027,
    not for gating v1 alerts, so the watchdog and the sweep
    never disagree about a job). A dep that does not exist in
    the snapshot is not dead, it is missing: WDG-006 owns that
    case and this detector stays silent on it. A done, blocked,
    or failed-final job itself is not waiting on anything, so
    only open/claimed jobs are scanned. The watchdog never
    mutates job state; it alerts.
    """
    snapshot = snapshot or {}
    jobs = snapshot.get("jobs") or []
    if not isinstance(jobs, (list, tuple)):
        jobs = []
    by_id = {}
    for job in jobs:
        if isinstance(job, dict) and job.get("id") is not None:
            by_id.setdefault(str(job.get("id")), job)
    alerts = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("status") not in ("open", "claimed"):
            continue
        job_id = str(job.get("id", ""))
        for dep_id in _parse_deps(job.get("deps")):
            dep = by_id.get(dep_id)
            if dep is None:
                continue
            dep_status = dep.get("status")
            if dep_status not in ("blocked", "failed-final"):
                continue
            note = dep.get("note")
            reason = note if isinstance(note, str) and note else dep_status
            blocking_note = (f" Blocking reason: {note}"
                             if isinstance(note, str) and note else "")
            explanation = explanations.render(
                "dead-dep", job=job_id, dep=dep_id,
                dep_status=dep_status,
                blocking_note=blocking_note)[0]
            suggested_fix = explanations.render(
                "dead-dep", job=job_id, dep=dep_id,
                dep_status=dep_status,
                blocking_note=blocking_note)[1]
            alerts.append({
                "kind": "dead-dep",
                "severity": "critical",
                "nick": job.get("claim") or "",
                "job": job_id,
                "job_title": job.get("title", ""),
                "dep": dep_id,
                "dep_status": dep_status,
                "blocking_reason": reason,
                "explanation": explanation,
                "suggested_fix": suggested_fix,
                "dedupe_key": f"dead-dep:{job_id}:{dep_id}",
                "created_at": int(now),
            })
    return alerts


def detect_missing_dep(snapshot, now):
    """WDG-006: missing-dependency detector.

    An open or claimed job whose dependency id does not exist
    in the job index at all was posted against a job that was
    never posted, was deleted, or was mistyped: it can never
    proceed, and the bad post should be caught early rather
    than sitting silently in the queue. One alert per (job,
    dep) pair, severity critical (same family as dead-dep in
    the WDG-024 mapping direction: the job cannot run). This
    is the complement of WDG-005, which stays silent on a
    missing dep by design: dead means the dep exists and is
    blocked/failed-final; missing means there is no dep job
    to unblock. A dep that exists in any status yields no
    alert here, even if it is blocked (that is WDG-005's
    case). A done job with a dangling dep yields no alert:
    it is not waiting on anything. The watchdog never
    mutates job state; it alerts.
    """
    snapshot = snapshot or {}
    jobs = snapshot.get("jobs") or []
    if not isinstance(jobs, (list, tuple)):
        jobs = []
    known = set()
    for job in jobs:
        if isinstance(job, dict) and job.get("id") is not None:
            known.add(str(job.get("id")))
    alerts = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("status") not in ("open", "claimed"):
            continue
        job_id = str(job.get("id", ""))
        for dep_id in _parse_deps(job.get("deps")):
            if dep_id in known:
                continue
            alerts.append({
                "kind": "missing-dep",
                "severity": "critical",
                "nick": job.get("claim") or "",
                "job": job_id,
                "job_title": job.get("title", ""),
                "dep": dep_id,
                "explanation": explanations.render(
                    "missing-dep", job=job_id, dep=dep_id)[0],
                "suggested_fix": explanations.render(
                    "missing-dep", job=job_id, dep=dep_id)[1],
                "dedupe_key": f"missing-dep:{job_id}:{dep_id}",
                "created_at": int(now),
            })
    return alerts


def _parse_files(value):
    """File paths off a job, in jobs.py's comma-separated form.

    jobs.py stores files as one comma-separated string (FND-008);
    a list form is accepted too so snapshots built by hand do
    not silently drop files. Empty entries are dropped, and a
    path listed twice on one job counts once.
    """
    if isinstance(value, (list, tuple)):
        raw = [str(f).strip() for f in value if str(f).strip()]
    elif isinstance(value, str):
        raw = [f.strip() for f in value.split(",") if f.strip()]
    else:
        return []
    seen = set()
    out = []
    for path in raw:
        if path not in seen:
            seen.add(path)
            out.append(path)
    return out


def detect_file_collision(snapshot, now):
    """WDG-007: file-collision detector.

    Two claimed jobs whose files fields overlap are about to
    step on each other: both workers editing the same path
    means one of them will lose work at merge time. One alert
    per (job pair, shared path), severity critical (WDG-024
    mapping), naming both job ids and the shared path.

    The second case is a claimed job overlapping a
    done-but-unmerged branch's files: a job with status done
    that still carries a branch name (jobs.py cmd_done stamps
    the job done but nothing merges the branch — that is a
    human/integration step), so a new claim on one of its
    paths risks redoing or clobbering finished work. This
    case fires only when the done job actually carries branch
    data (a non-empty branch field); a done job with no
    branch recorded is finished work with no branch to
    collide with, and stays silent. Open jobs are never
    scanned on either side: nobody is working them yet, so
    there is nothing to collide with. The watchdog never
    mutates job state; it alerts.
    """
    snapshot = snapshot or {}
    jobs = snapshot.get("jobs") or []
    if not isinstance(jobs, (list, tuple)):
        jobs = []
    claimed = []
    done_branches = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("status") == "claimed":
            claimed.append(job)
        elif job.get("status") == "done":
            branch = job.get("branch")
            if isinstance(branch, str) and branch:
                done_branches.append(job)
    alerts = []

    def _alert(first, second, path, other_status=None, branch=None):
        first_id = str(first.get("id", ""))
        second_id = str(second.get("id", ""))
        if other_status == "done":
            explanation, suggested_fix = explanations.render(
                "file-collision-done", job=first_id,
                other_job=second_id, shared_path=path,
                branch=branch)
        else:
            explanation, suggested_fix = explanations.render(
                "file-collision", job=first_id,
                other_job=second_id, shared_path=path)
        alert = {
            "kind": "file-collision",
            "severity": "critical",
            "nick": first.get("claim") or "",
            "job": first_id,
            "other_job": second_id,
            "job_title": first.get("title", ""),
            "other_title": second.get("title", ""),
            "shared_path": path,
            "explanation": explanation,
            "suggested_fix": suggested_fix,
            "dedupe_key": f"file-collision:{first_id}:{second_id}:{path}",
            "created_at": int(now),
        }
        if other_status == "done":
            alert["other_status"] = "done"
            alert["branch"] = branch
        return alert

    for i, first in enumerate(claimed):
        first_files = _parse_files(first.get("files"))
        if not first_files:
            continue
        for second in claimed[i + 1:]:
            for path in first_files:
                if path in _parse_files(second.get("files")):
                    alerts.append(_alert(first, second, path))
        for done in done_branches:
            for path in first_files:
                if path in _parse_files(done.get("files")):
                    alerts.append(_alert(first, done, path,
                                         other_status="done",
                                         branch=done.get("branch")))
    return alerts


def _as_int(value, default=None):
    """An int off a job field, accepting Redis string form.

    jobs.py stores attempts/max_attempts as ints in memory but
    Redis hashes hold strings; a snapshot built by hand may
    carry either. Unparseable or missing values yield the
    default, never an invented number.
    """
    if isinstance(value, bool):
        return default
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError:
            return default
    return default


def detect_attempt_exhaustion(snapshot, now):
    """WDG-008: attempt-exhaustion detector.

    A job's attempt budget is enforced by jobs.py at requeue
    time (FND-010): attempts >= max_attempts marks the job
    failed-final instead of requeueing it, otherwise the
    requeue bumps attempts by one. The watchdog watches the
    approach, so the crew hears about it before the budget
    is gone, not after:

    - attempts == max_attempts - 1: one attempt left. A
      warning heads-up alert (severity warning, the WDG-024
      mapping for attempt alerts): the next requeue burns
      the last attempt, so this is the moment to fix the
      blocker or rethink the job.
    - attempts >= max_attempts: the budget is spent. A
      critical alert naming the job as failed-final: either
      the sweep already marked it, or the next requeue will.

    One alert per job, never both kinds for the same job in
    one tick: at max the critical alert replaces the warning,
    so a fixture walk over attempts 0..max produces the
    warning exactly at max-1 and the critical exactly at
    max and beyond. A job with no max_attempts carries no
    budget and yields no alert, however many attempts it has
    burned. A done job yields no alert either: it finished,
    whatever its attempt count was. Open, claimed, blocked,
    and failed-final jobs are all scanned — the warning
    matters most on a live job, the critical matters most
    on the failed-final record itself. The watchdog never
    mutates job state; it alerts.
    """
    snapshot = snapshot or {}
    jobs = snapshot.get("jobs") or []
    if not isinstance(jobs, (list, tuple)):
        jobs = []
    alerts = []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("status") not in ("open", "claimed", "blocked",
                                     "failed-final"):
            continue
        max_attempts = _as_int(job.get("max_attempts"))
        if max_attempts is None:
            continue
        attempts = _as_int(job.get("attempts"), 0)
        if attempts is None:
            attempts = 0
        job_id = str(job.get("id", ""))
        nick = job.get("claim") or ""
        if attempts >= max_attempts:
            alerts.append({
                "kind": "attempt-exhaustion",
                "severity": "critical",
                "nick": nick,
                "job": job_id,
                "job_title": job.get("title", ""),
                "attempts": attempts,
                "max_attempts": max_attempts,
                "attempts_remaining": 0,
                "explanation": explanations.render(
                    "attempt-exhaustion", job=job_id,
                    attempts=attempts,
                    max_attempts=max_attempts)[0],
                "suggested_fix": explanations.render(
                    "attempt-exhaustion", job=job_id,
                    attempts=attempts,
                    max_attempts=max_attempts)[1],
                "dedupe_key": f"attempt-exhaustion:{job_id}",
                "created_at": int(now),
            })
        elif attempts == max_attempts - 1:
            alerts.append({
                "kind": "attempt-warning",
                "severity": "warning",
                "nick": nick,
                "job": job_id,
                "job_title": job.get("title", ""),
                "attempts": attempts,
                "max_attempts": max_attempts,
                "attempts_remaining": 1,
                "explanation": explanations.render(
                    "attempt-warning", job=job_id,
                    attempts=attempts,
                    max_attempts=max_attempts)[0],
                "suggested_fix": explanations.render(
                    "attempt-warning", job=job_id,
                    attempts=attempts,
                    max_attempts=max_attempts)[1],
                "dedupe_key": f"attempt-warning:{job_id}",
                "created_at": int(now),
            })
    return alerts


def detect_silent_room(snapshot, now):
    """WDG-009: silent-room detector (informational, never an alert).

    A build room with claimed jobs but zero messages for longer
    than thresholds.SILENT_ROOM_MINUTES is quiet in a way worth
    noticing: likely everyone is stuck, or everyone is heads-down
    deep in work. Exactly one room-level record per tick, severity
    "info" — never "critical" or "warning", so the dashboard and
    the brief (WDG-024's mapping) can render it as information
    and never as an ALERT, and WDG-015 never announces it.

    Silence is measured from the latest timestamped message in
    the snapshot (brief.py's message shape carries "ts"); the
    record fires only when that age exceeds the threshold. A
    snapshot with no timestamped messages yields no record: an
    empty message list proves nothing about duration — the room
    may be brand new — and this detector never invents an age
    for it, same discipline as WDG-002/WDG-003. A room with no
    claimed jobs yields no record either: a quiet room with
    nothing claimed is normal, not a signal. Plain bus strings
    carry no timestamp and are ignored for the silence clock.

    "During work hours" in the lane plan is NOT gated here: the
    plan defines no work-hours window, and a fake-clock test
    suite cannot honestly gate on wall-clock hours. WDG-024's
    severity-mapping table (and WDG-027 tuning) is where a
    window, if the crew defines one, gets pinned; until then
    the record fires on the silence condition alone and says
    so. The watchdog never mutates job state; it records.
    """
    snapshot = snapshot or {}
    jobs = snapshot.get("jobs") or []
    if not isinstance(jobs, (list, tuple)):
        jobs = []
    claimed = [job for job in jobs
               if isinstance(job, dict)
               and job.get("status") == "claimed"]
    if not claimed:
        return []
    messages = snapshot.get("messages") or []
    if not isinstance(messages, (list, tuple)):
        messages = []
    last_ts = None
    for page in paginate(messages):
        for message in page:
            if not isinstance(message, dict):
                continue
            ts = _as_int(message.get("ts"))
            if ts is None:
                continue
            if last_ts is None or ts > last_ts:
                last_ts = ts
    if last_ts is None:
        return []
    age = int(now) - last_ts
    threshold_seconds = thresholds.SILENT_ROOM_MINUTES * 60
    if age <= threshold_seconds:
        return []
    claimed_ids = [str(job.get("id", "")) for job in claimed]
    room = snapshot.get("room")
    dedupe_key = "silent-room"
    if isinstance(room, str) and room:
        dedupe_key = f"silent-room:{room}"
    record = {
        "kind": "silent-room",
        "severity": "info",
        "claimed_jobs": claimed_ids,
        "claimed_count": len(claimed_ids),
        "last_message_age_seconds": age,
        "last_message_age_minutes": age // 60,
        "explanation": explanations.render(
            "silent-room",
            claimed_ids=", ".join(claimed_ids),
            age_minutes=age // 60,
            window_minutes=thresholds.SILENT_ROOM_MINUTES)[0],
        "suggested_fix": explanations.render(
            "silent-room",
            claimed_ids=", ".join(claimed_ids),
            age_minutes=age // 60,
            window_minutes=thresholds.SILENT_ROOM_MINUTES)[1],
        "dedupe_key": dedupe_key,
        "created_at": int(now),
    }
    if isinstance(room, str) and room:
        record["room"] = room
    return [record]


_REJECTED_LINE = re.compile(
    r"REJECTED:(\d+) (BAD|EXPIRED)\b"
    r"(?:\s+signed_by=(\S+))?"
    r"(?:\s+rejected_by=(\S+))?")


def _message_text(message):
    """One message's body text, for either snapshot shape.

    Ingest snapshots carry raw bus strings ("nick: text");
    brief-shaped snapshots carry dicts with a "text" field.
    Anything else yields "", never a crash: a malformed
    message is skipped, not mistaken for a refusal.
    """
    if isinstance(message, dict):
        text = message.get("text")
        return text if isinstance(text, str) else ""
    if isinstance(message, str):
        return message
    return ""


def detect_rejected_dispatch(snapshot, now):
    """INT-010: refused-dispatch detector.

    A worker that refuses a dispatched job (jobs.py claim
    verification) announces one line to the room:
    "REJECTED:<job> <BAD|EXPIRED> signed_by=<poster>
    rejected_by=<refuser>". That line scrolls past in chat;
    this detector turns it into a critical alert record so
    the refusal is visible in the brief and the dashboard,
    with the same job id and verdict on every surface.

    One alert per (job, verdict) per tick: the same refusal
    reappearing in the window does not double-alert. The
    detector verifies nothing itself — it reports the
    refusal the worker already computed. That is the honest
    boundary: the watchdog holds no crew secret, so it
    cannot re-derive BAD/EXPIRED, and it must not invent
    a verdict for a job no worker refused. A bare
    "REJECTED" line with no job id, a verdict other than
    BAD/EXPIRED, or a job nobody refused yields no alert.
    An unsigned job yields no alert either: unsigned is
    allowed by design (jobs.py claims it with a warning),
    and alerting on it would contradict that rule.

    Severity is critical for both verdicts: a refused
    dispatch is a security incident until a human says
    otherwise, and the verdict field carries BAD vs
    EXPIRED so the reader can tell an attack-shaped
    refusal from a stale signature. The watchdog never
    mutates job state; it records.
    """
    snapshot = snapshot or {}
    messages = snapshot.get("messages") or []
    if not isinstance(messages, (list, tuple)):
        messages = []
    seen = set()
    alerts = []
    for message in messages:
        text = _message_text(message)
        if not text:
            continue
        for match in _REJECTED_LINE.finditer(text):
            job_id, verdict, signed_by, rejected_by = match.groups()
            key = f"rejected-dispatch:{job_id}:{verdict}"
            if key in seen:
                continue
            seen.add(key)
            explanation, suggested_fix = explanations.render(
                "rejected-dispatch", job=job_id, verdict=verdict,
                signed_by=signed_by or "?",
                rejected_by=rejected_by or "?")
            alerts.append({
                "kind": "rejected-dispatch",
                "severity": "critical",
                "job": job_id,
                "verdict": verdict,
                "signed_by": signed_by or "?",
                "rejected_by": rejected_by or "?",
                "explanation": explanation,
                "suggested_fix": suggested_fix,
                "dedupe_key": key,
                "created_at": int(now),
            })
    return alerts


def detect_budget_warning(snapshot, now):
    """OS-085: budget-warning detector.

    A lane that has spent past the warning threshold of its
    cap (intel/budgets.py BUDGET_WARN_PERCENT, default 80%)
    gets a warning alert — the warning before the cap, so the
    crew hears about the lane while it can still finish its
    current work, not after the silence. Severity is warning
    (WDG-024 mapping, extended): the lane is not dead yet,
    just about to stop claiming. A lane at cap yields no
    warning here: the cap hold is the louder signal, and
    warning about a lane that is already held would
    double-report the same condition — the hold itself is
    visible in the brief's budget line (OS-079) and in the
    queue gate (intel/budgets.py claim_allowed).

    The snapshot carries budgets as a "budgets" list of
    OS-079-shaped entries (lane, spent, cap); entries without
    a usable cap are unbudgeted and yield nothing, and
    malformed entries are skipped, never guessed. One alert
    per lane per tick; the dedupe key is budget-warning:<lane>
    so the WDG-013 cooldown collapses repeat ticks into one
    record with an advancing last_seen. The watchdog never
    mutates spend or holds claims itself; it records.
    """
    from . import budgets

    snapshot = snapshot or {}
    alerts = []
    seen = set()
    for entry in budgets.budgets_from_snapshot(snapshot):
        lane = entry.get("lane")
        if lane in seen:
            continue
        seen.add(lane)
        spent = entry.get("spent")
        cap = entry.get("cap")
        if not budgets.at_warning(spent, cap):
            continue
        explanation, suggested_fix = explanations.render(
            "budget-warning", lane=lane, spent=spent, cap=cap,
            remaining=cap - spent,
            warn_percent=budgets.BUDGET_WARN_PERCENT)
        alerts.append({
            "kind": "budget-warning",
            "severity": "warning",
            "lane": lane,
            "spent": spent,
            "cap": cap,
            "remaining": cap - spent,
            "explanation": explanation,
            "suggested_fix": suggested_fix,
            "dedupe_key": f"budget-warning:{lane}",
            "created_at": int(now),
        })
    return alerts


def paginate(items, page_size=None):
    """WDG-017: yield successive pages of a sequence, oldest first.

    Same shape as digest.py's LRANGE loop (PAGE = 1000 there):
    one page at a time, stopping on a short final page. A caller
    that holds only one page at a time never loads the whole
    history at once; a sized sequence is sliced page by page
    (each slice is one page copy, never a second full copy),
    and a bare iterator is chunked with islice instead. A
    non-positive page size is a caller bug, not a silent
    default: it raises rather than slurping everything.
    """
    if page_size is None:
        page_size = thresholds.TICK_PAGE_SIZE
    if (isinstance(page_size, bool)
            or not isinstance(page_size, int) or page_size <= 0):
        raise ValueError("page_size must be a positive int")
    try:
        total = len(items)
    except TypeError:
        total = None
    if total is not None:
        start = 0
        while start < total:
            yield list(items[start:start + page_size])
            start += page_size
        return
    iterator = iter(items)
    while True:
        page = list(itertools.islice(iterator, page_size))
        if not page:
            break
        yield page


def cap_tick_snapshot(snapshot, max_messages=None, page_size=None):
    """WDG-017: cap a snapshot's message window before a tick.

    Returns a new snapshot dict whose messages are the newest
    max_messages (default thresholds.TICK_MAX_MESSAGES), oldest
    dropped first — ingest order is oldest first, so the tail
    survives. The walk goes page by page through paginate(),
    keeping a rolling tail, so the cap itself never holds more
    than one page plus the kept tail. The returned snapshot
    carries a "tick_window" record {max_messages, page_size,
    messages_kept, messages_dropped}, mirroring brief.py's
    source_window; a second cap accumulates the earlier drop
    count instead of resetting it (brief.py BRF-024's lesson).
    Jobs, presence, caps, and alerts pass through unchanged:
    capping jobs could hide a stall or a collision on a
    dropped job. The message readers are WDG-009
    silent-room, which needs just the newest message, and
    INT-010 rejected-dispatch, which reads recent refusal
    lines: dropping messages older than the cap means a
    capped tick does not re-report an old refusal, but the
    alert record written from the first tick persists in
    the store, so the incident stays visible. A snapshot
    with no list-shaped messages yields an empty list and
    a zero drop count, never an invented message.
    """
    if max_messages is None:
        max_messages = thresholds.TICK_MAX_MESSAGES
    if page_size is None:
        page_size = thresholds.TICK_PAGE_SIZE
    snapshot = snapshot or {}
    messages = snapshot.get("messages") or []
    if not isinstance(messages, (list, tuple)):
        messages = []
    total = len(messages)
    kept = deque(maxlen=max_messages) if max_messages > 0 else deque()
    for page in paginate(messages, page_size):
        kept.extend(page)
    dropped = total - len(kept)
    prior = snapshot.get("tick_window")
    if isinstance(prior, dict):
        prior_dropped = prior.get("messages_dropped")
        if isinstance(prior_dropped, int):
            dropped += prior_dropped
    capped = dict(snapshot)
    capped["messages"] = list(kept)
    capped["tick_window"] = {
        "max_messages": max_messages,
        "page_size": page_size,
        "messages_kept": len(kept),
        "messages_dropped": dropped,
    }
    return capped


# Detector registry (WDG-002..WDG-009 register here, plus
# INT-010's rejected-dispatch detector).
# Each detector is a callable(snapshot, now) -> list of alert dicts.
# Alert record shape is fixed by WDG-010 (intel.store.write_alert
# validates and persists); this loop passes detector dicts through
# untouched, and the writer converts them.
DETECTORS = [detect_presence_stall, detect_progress_stall,
             detect_lease_risk, detect_dead_dep,
             detect_missing_dep, detect_file_collision,
             detect_attempt_exhaustion, detect_silent_room,
             detect_rejected_dispatch, detect_budget_warning]


# WDG-024: the canonical severity mapping, the single source of
# truth the dashboard and the brief read. Rule from the lane plan:
# stall / dead-dep / collision = critical, lease-risk / attempt
# = warning, silent-room = info. One refinement the plan's
# shorthand hides: WDG-008 emits two attempt kinds — the
# max_attempts-1 heads-up is the warning, the spent budget
# (attempt-exhaustion, failed-final) is critical, because the
# job is already dead, not merely at risk. INT-010 adds
# rejected-dispatch = critical: a refused dispatch is a
# security incident until a human says otherwise. OS-085 adds
# budget-warning = warning: a lane past its warning threshold
# is at risk of stopping, not stopped — the cap hold itself
# is the louder signal and is not double-reported as a warning.
# Detectors still write
# their severity literal in the alert dict; SeverityMappingTest
# locks every detector's emitted severity to this table, so a
# detector that drifts from the table fails the suite rather
# than shipping a quiet mismatch. Dashboard colors keyed to
# these severities live in bus.html / index.html (DSH-018,
# same palette, icon + text label, never color alone):
# critical #f85149, warning #d29922, info #58a6ff.
SEVERITY_BY_KIND = {
    "presence-stall": "critical",
    "progress-stall": "critical",
    "lease-risk": "warning",
    "dead-dep": "critical",
    "missing-dep": "critical",
    "file-collision": "critical",
    "attempt-warning": "warning",
    "attempt-exhaustion": "critical",
    "silent-room": "info",
    "rejected-dispatch": "critical",
    "budget-warning": "warning",
}


def format_announcement(alert):
    """WDG-015: one frozen-format announcement line for an alert.

    Format: "ALERT:<id> <kind>: <explanation>", exactly one
    line (embedded newlines in an explanation are flattened
    to spaces, so a line can never smuggle a second message
    onto the bus). The id is the alert's id when present,
    else its dedupe_key — the same id the store (WDG-010)
    files the record under, so the announcement and the
    record always name the same incident.

    Only severity "critical" announces: warnings accumulate
    silently for the brief/dashboard, and info records
    (WDG-009 silent-room) never announce. Anything else —
    warning, info, unknown severity, or a non-dict — yields
    None, never a line. This is the gate: a critical alert
    produces a line, everything else produces silence.
    """
    if not isinstance(alert, dict):
        return None
    if alert.get("severity") != "critical":
        return None
    alert_id = alert.get("id") or alert.get("dedupe_key")
    if not alert_id:
        return None
    kind = alert.get("kind") or "alert"
    explanation = alert.get("explanation")
    if not isinstance(explanation, str) or not explanation:
        explanation = kind
    line = f"ALERT:{alert_id} {kind}: {explanation}"
    return " ".join(line.splitlines())


def announcements_for(alerts):
    """WDG-015: the announcement lines for an alert list.

    Every critical alert yields exactly one line, in list
    order; warnings and info records yield nothing. A caller
    that wants the lines without running a tick (the brief,
    the dashboard backfill) uses this; a caller running a
    tick passes tick()'s announce callback instead. Either
    way the lines are held until the caller posts them —
    this module posts nothing itself (Dale's posting rule).
    """
    if not isinstance(alerts, (list, tuple)):
        return []
    lines = []
    for alert in alerts:
        line = format_announcement(alert)
        if line is not None:
            lines.append(line)
    return lines


def restart_event_note(nick, job_id, now, downtime_seconds=None):
    """OS-034: the watchdog's event note for a systemd-restarted worker.

    The restart-ownership contract (META_OS.md, supervision
    contract): systemd's Restart= owns process death, the
    watchdog owns silent-but-alive stalls, and neither
    double-acts on the other's case. So a worker that dies
    and comes back under systemd Restart gets exactly this
    — an INFO record, never a stall alert — while a worker
    that lives but stops progressing gets a progress-stall
    alert and no restart fight (systemd sees a live process
    and does nothing). The note is a detector-shaped dict so
    it validates and stores through intel.store's writer
    (WDG-010) like any alert, but its severity is info, so
    format_announcement() yields nothing for it: a handled
    restart is visible in the brief and the dashboard, never
    a bus announcement. downtime_seconds, when the caller
    knows it (death to re-presence), rides along as evidence
    and is named in the explanation; when unknown it is
    omitted, never guessed — a note must not invent a gap
    length the supervisor did not observe.
    """
    if not nick or not job_id:
        raise ValueError("restart_event_note needs a nick and a job id")
    if downtime_seconds is None:
        down = "after a brief absence"
    else:
        down = f"after {int(downtime_seconds)}s down"
    explanation = (
        f"Worker {nick} on job {job_id} died and was restarted "
        f"by systemd {down}; no stall alert fired because the "
        f"worker is back and progressing."
    )
    return {
        "kind": "worker-restart",
        "severity": "info",
        "nick": nick,
        "job": str(job_id),
        "job_title": "",
        "explanation": explanation,
        "suggested_fix": ("No action: systemd handled the death. "
                          "Investigate only if restarts repeat."),
        "dedupe_key": f"worker-restart:{nick}:{job_id}",
        "created_at": int(now),
        "downtime_seconds": downtime_seconds,
    }


# ---------------------------------------------------------------------------
# OS-037 journal watch: relay unit failures -> SYSTEM alert records.
# ---------------------------------------------------------------------------

JOURNAL_RELAY_UNIT_PREFIX = "relay-"

# systemd's own failure phrasing in journald (journalctl -o json,
# MESSAGE field). A relay unit's message matching any of these is a
# failure even at a benign priority, because systemd only writes
# these lines when a unit actually failed; the priority rule below
# covers the other direction (a relay unit logging at err/crit).
_JOURNAL_FAILURE_PATTERNS = (
    re.compile(r"failed with result", re.IGNORECASE),
    re.compile(r"main process exited", re.IGNORECASE),
    re.compile(r"failed to start", re.IGNORECASE),
    re.compile(r"entered failed state", re.IGNORECASE),
)

# journald priorities at or below err (3): emerg 0, alert 1, crit 2,
# err 3. A relay unit logging at these levels is treated as failed:
# the unit's own stderr at err is the machine reporting its own
# failure, and the alert quotes the message verbatim so a human
# can judge whether it was transient.
_JOURNAL_FAILURE_MAX_PRIORITY = 3


def _journal_entry_fields(entry):
    """Normalize one journal entry to (unit, message, priority).

    Accepts journalctl -o json dicts (_SYSTEMD_UNIT, MESSAGE,
    PRIORITY) and the plain-keyed equivalents (unit, message,
    priority) the drills build by hand, plus a JSON string of
    either shape. Returns None for anything unusable — a blank
    line, unparseable JSON, a non-dict, or an entry with no unit
    — because an unattributed failure must never be filed under
    an invented unit name. Priority parses to an int or None;
    an unparseable priority means "unknown", never a guessed
    level, so such an entry can only fire on its message text.
    """
    if isinstance(entry, str):
        text = entry.strip()
        if not text:
            return None
        try:
            entry = json.loads(text)
        except ValueError:
            return None
    if not isinstance(entry, dict):
        return None
    unit = (entry.get("_SYSTEMD_UNIT") or entry.get("SYSTEMD_UNIT")
            or entry.get("unit") or "")
    if not isinstance(unit, str) or not unit.strip():
        return None
    message = entry.get("MESSAGE")
    if message is None:
        message = entry.get("message", "")
    if not isinstance(message, str):
        message = str(message)
    priority = entry.get("PRIORITY")
    if priority is None:
        priority = entry.get("priority")
    parsed_priority = None
    if isinstance(priority, bool):
        parsed_priority = None
    elif isinstance(priority, int):
        parsed_priority = priority
    elif isinstance(priority, str) and priority.strip():
        try:
            parsed_priority = int(priority.strip())
        except ValueError:
            parsed_priority = None
    return (unit.strip(), message, parsed_priority)


def journal_entry_is_failure(entry):
    """OS-037: is this journal entry a relay unit failure?

    Only relay units count (unit name starting with "relay-"):
    a failing sshd or cron unit is the host's business, not the
    crew's, and must never become a crew alert. Within relay
    units, failure is either a systemd failure message or an
    err-or-worse priority. Relay info/start/stop lines and
    non-relay failures both yield False — the watch must be
    quiet on a healthy boot, or the dashboard learns to ignore
    it, which is worse than no watch at all.
    """
    fields = _journal_entry_fields(entry)
    if fields is None:
        return False
    unit, message, priority = fields
    if not unit.startswith(JOURNAL_RELAY_UNIT_PREFIX):
        return False
    if priority is not None and priority <= _JOURNAL_FAILURE_MAX_PRIORITY:
        return True
    return any(p.search(message) for p in _JOURNAL_FAILURE_PATTERNS)


def parse_journal_entries(text):
    """Parse journalctl -o json output into normalized entries.

    One JSON object per line; blank lines and unparseable lines
    are skipped, never fatal — a corrupt line in a long journal
    tail must not blind the watch to the failures around it.
    Returns a list of (unit, message, priority) triples; entries
    with no unit are dropped here for the same reason as in
    _journal_entry_fields (no invented attribution).
    """
    entries = []
    if not isinstance(text, str):
        return entries
    for line in text.splitlines():
        fields = _journal_entry_fields(line)
        if fields is not None:
            entries.append(fields)
    return entries


def detect_journal_failures(entries, now):
    """OS-037: relay unit failures -> one SYSTEM alert per unit.

    entries is a journalctl -o json string, or a list of entry
    dicts/strings in either key shape. Failures group by unit:
    a unit that fails, restarts, and fails again in one window
    is one incident, not a storm — the alert carries
    failure_count, and the store writer (WDG-013) dedupes
    re-reports of the same unit inside the cooldown by
    advancing last_seen only. The alert is a SYSTEM record by
    construction: kind "system-failure", subjects [unit],
    system_alert True, and no nick or job field at all, so no
    reader — brief, dashboard, or human — can mistake it for
    a worker stall. Severity is critical: a relay unit down
    is a crew-down event, not a warning. The explanation
    quotes the first failure message (truncated at 300 chars
    for the record; the full text rides in journal_message),
    and the suggested fix names journalctl -u and an operator
    restart — the watchdog never restarts a unit itself, per
    the OS-034 contract (systemd owns process death).
    """
    if isinstance(entries, str):
        parsed = parse_journal_entries(entries)
    elif isinstance(entries, (list, tuple)):
        parsed = []
        for entry in entries:
            fields = _journal_entry_fields(entry)
            if fields is not None:
                parsed.append(fields)
    else:
        parsed = []
    by_unit = {}
    order = []
    for unit, message, priority in parsed:
        if not unit.startswith(JOURNAL_RELAY_UNIT_PREFIX):
            continue
        if not (priority is not None
                and priority <= _JOURNAL_FAILURE_MAX_PRIORITY
                or any(p.search(message)
                       for p in _JOURNAL_FAILURE_PATTERNS)):
            continue
        if unit not in by_unit:
            by_unit[unit] = {"first_message": message, "count": 0}
            order.append(unit)
        by_unit[unit]["count"] += 1
    alerts = []
    for unit in order:
        info = by_unit[unit]
        first = info["first_message"]
        excerpt = first if len(first) <= 300 else first[:297] + "..."
        alerts.append({
            "kind": "system-failure",
            "severity": "critical",
            "subjects": [unit],
            "unit": unit,
            "system_alert": True,
            "failure_count": info["count"],
            "journal_message": first,
            "explanation": (
                f"System unit {unit} failed: {excerpt}"
                if excerpt else
                f"System unit {unit} failed (no message logged)."),
            "suggested_fix": (
                f"Check journalctl -u {unit} for the failure, "
                f"then restart the unit; the watchdog reports "
                f"unit failures but never restarts units itself."),
            "dedupe_key": f"system-failure:{unit}",
            "created_at": int(now),
        })
    return alerts


def journal_watch_tick(entries, now=None, emit=None):
    """OS-037: one journal-watch loop iteration.

    The journal half of a watchdog loop: detect failures in
    entries (journalctl -o json text, or parsed entry dicts),
    emit each alert through emit when given (pass
    intel.store.write_alert and the alert lands in the same
    alert store the dashboard reads, within this one call —
    that is the acceptance's "within one watchdog loop"), and
    return the alert list regardless. now defaults to the wall
    clock; tests pass an injected clock. Never raises on a bad
    entry: parse failures are skipped upstream, and an emit
    failure for one alert must not hide the next unit's
    failure, so emit exceptions are swallowed per alert.
    """
    current = int(time.time() if now is None else now)
    alerts = detect_journal_failures(entries, current)
    if emit is not None:
        for alert in alerts:
            try:
                emit(alert)
            except Exception:
                continue
    return alerts


def _parse_server_time(value):
    """A Redis server timestamp off a snapshot, or None.

    Accepted shapes, in the order a snapshot producer may
    plausibly carry them: an int/float epoch (Redis TIME's
    seconds, or a plain epoch); a numeric string (Redis
    hashes and JSON snapshots both store numbers as
    strings); a two-element [seconds, microseconds] pair
    (Redis TIME's literal reply shape — the sub-second
    part is dropped, ages are whole seconds everywhere
    else in this module). Anything else — a non-numeric
    string, a bool, a wrong-length sequence, None — yields
    None, never an invented timestamp: an unusable
    server_time falls back to the wall clock, and that
    fallback is the honest one, not a guessed epoch.
    """
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str) and value.strip():
        try:
            return int(value.strip())
        except ValueError:
            try:
                return int(float(value.strip()))
            except ValueError:
                return None
    if isinstance(value, (list, tuple)) and len(value) == 2:
        seconds = _parse_server_time(value[0])
        if seconds is None:
            return None
        microseconds = _parse_server_time(value[1])
        if microseconds is None:
            return None
        return seconds
    return None


def resolve_tick_now(snapshot, now=None):
    """WDG-026: the one "now" a tick computes ages from.

    Returns (timestamp, source) with source one of:
    - "explicit": the caller passed now (the injected clock
      tests use, and a live caller's deliberate override);
    - "server_time": the snapshot's server_time field parsed
      (Redis server time, where the snapshot carries it);
    - "wall_clock": local time.time(), the fallback when
      neither is available.

    Precedence is fixed and documented, not first-come:
    an explicit now always beats server_time, so a test
    (or a drill) that injects a clock can never be silently
    overridden by a stale server_time stamped on its
    fixture, and a snapshot with server_time always beats
    the wall clock, so a skewed local clock can never
    silently override the server's time. A malformed
    server_time is treated as absent, never as zero.
    """
    if now is not None:
        return int(now), "explicit"
    snapshot = snapshot or {}
    server_time = _parse_server_time(snapshot.get("server_time"))
    if server_time is not None:
        return server_time, "server_time"
    return int(time.time()), "wall_clock"


def tick(snapshot, now=None, emit=None, polish_client=None,
         announce=None, beat=None, max_messages=None):
    """WDG-001: evaluate one snapshot, return the alerts found.

    snapshot is a plain dict in the shape intel/brief.py
    documents ({messages, jobs, presence, caps, alerts});
    missing sections are treated as empty, never invented.
    now is a Unix timestamp (defaults to the resolved tick
    clock, WDG-026: explicit now, else the snapshot's
    server_time, else the local wall clock) so tests can
    run on a fake clock, and so every detector in the tick
    computes ages from the same single timestamp — a tick
    never mixes clocks. When emit is given it is
    called once per alert, in detector order; the return value
    is the same alert list regardless. Never raises on a bad
    detector: a crashing detector is skipped, because one
    broken detector must not blind the rest of the loop.

    polish_client (WDG-012) is the optional Spark polish
    toggle: when given, each alert's explanation is passed
    through intel.explanations.polish_explanation before
    the alert is returned or emitted, so the stored record
    (WDG-010, via emit) carries the polished text. When it
    is None the template text stands; when Spark fails or
    answers empty, polish_explanation keeps the template,
    so a bad polish can never blank or break an alert.
    Alerts without a string explanation are passed through
    untouched. The suggested fix is never polished.

    announce (WDG-015) is the optional announcement gate:
    when given, it is called once per critical alert with
    that alert's frozen-format line (format_announcement);
    warnings and info records never reach it. It is None by
    default — with no callback, tick announces nothing, and
    the lines stay held for the caller to post only under
    Dale's posting rule. The callback receives the line, not
    the bus: posting is the caller's job, never this loop's.

    beat (WDG-016) is the optional self-heartbeat callback:
    when given, it is called once per tick with the tick
    timestamp, after the detectors run, whether or not any
    alert fired — a quiet tick still proves the watchdog is
    alive. Pass intel.store.wd_self_beat as the callback and
    the beat key renews on every tick. A beat callback that
    raises is swallowed, not propagated: a failed beat write
    must not fail the tick or hide its alerts — the missed
    beat is itself the signal, and the dashboard renders it
    as stale. With no callback, tick writes no beat anywhere.

    max_messages (WDG-017) is the tick budget guard: before any
    detector runs, the snapshot is capped through
    cap_tick_snapshot() to the newest max_messages messages
    (default thresholds.TICK_MAX_MESSAGES). The cap is
    verdict-safe — the only message reader needs just the
    newest message — and jobs are never capped. Pass a larger
    max_messages to widen the window for a drill; there is no
    way to pass "unbounded" through this argument, because an
    unbounded tick is exactly what the guard exists to prevent.
    """
    snapshot = snapshot or {}
    current, _now_source = resolve_tick_now(snapshot, now)
    snapshot = cap_tick_snapshot(snapshot, max_messages=max_messages)
    alerts = []
    for detector in list(DETECTORS):
        try:
            found = detector(snapshot, current)
        except Exception:
            continue
        if not found:
            continue
        for alert in found:
            if (polish_client is not None
                    and isinstance(alert, dict)
                    and isinstance(alert.get("explanation"), str)
                    and alert["explanation"]):
                alert["explanation"] = explanations.polish_explanation(
                    alert["explanation"], polish_client)
            alerts.append(alert)
            if emit is not None:
                emit(alert)
            if announce is not None:
                line = format_announcement(alert)
                if line is not None:
                    announce(line)
    if beat is not None:
        try:
            beat(current)
        except Exception:
            pass
    return alerts


def _load_snapshot(path):
    if not path:
        return {}
    with open(path) as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("snapshot file must hold a JSON object")
    return data


def main(argv=None):
    """Watchdog CLI: --once runs one tick, --loop repeats it.

    --snapshot <file> supplies the snapshot JSON; without it
    the tick runs on an empty (quiet) snapshot. --journal
    <file> supplies journalctl -o json lines for one OS-037
    journal-watch iteration, reported alongside the snapshot
    tick (stdout only, never a bus post). --interval sets
    the loop pause in seconds; --max-ticks bounds a loop run
    (a drill/test hook — unset means run until interrupted).
    --announce prints each critical alert's WDG-015 line to
    stdout after the count (a drill view, not a bus post:
    this CLI never posts anywhere). --beat renews the WDG-016
    self-heartbeat key (muse-bus:intel:wd:beat) on every tick
    via intel.store.wd_self_beat — this is the flag the
    OS-033 relay-watchdog.service unit passes, so the unit's
    ticks are what the dashboard (DSH-015) reads as alive;
    without --beat the CLI writes no beat anywhere, and a
    stopped unit's beat simply expires after its 300s TTL
    into the dashboard's watchdog-silent state. Prints the
    alert count per tick and exits 0 on a clean --once run.
    Exits 1 only when the snapshot file is unusable.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--once", action="store_true",
                        help="run one tick and exit")
    parser.add_argument("--loop", action="store_true",
                        help="repeat ticks until interrupted")
    parser.add_argument("--snapshot", default=None,
                        help="JSON snapshot file (default: empty)")
    parser.add_argument("--journal", default=None,
                        help="journalctl -o json file for the OS-037 "
                             "journal watch (one loop iteration, "
                             "reported alongside the snapshot tick)")
    parser.add_argument("--interval", type=float, default=60.0,
                        help="seconds between loop ticks")
    parser.add_argument("--max-ticks", type=int, default=None,
                        help="stop a loop after this many ticks")
    parser.add_argument("--room", default="main",
                        help="room name (recorded, not read yet: "
                             "live reading waits on FND-014)")
    parser.add_argument("--announce", action="store_true",
                        help="print WDG-015 announcement lines "
                             "for critical alerts (stdout only, "
                             "never a bus post)")
    parser.add_argument("--beat", action="store_true",
                        help="renew muse-bus:intel:wd:beat on "
                             "every tick (OS-033 service mode)")
    args = parser.parse_args(argv)
    if not args.once and not args.loop:
        parser.error("watchdog needs --once or --loop")
    beat_cb = None
    if args.beat:
        try:
            from . import store as istore
        except ImportError:  # run as a plain script file
            import store as istore
        beat_cb = istore.wd_self_beat
    try:
        snapshot = _load_snapshot(args.snapshot)
    except (OSError, ValueError) as exc:
        print(f"watchdog: cannot load snapshot: {exc}", file=sys.stderr)
        return 1
    journal_text = None
    if args.journal:
        try:
            with open(args.journal) as handle:
                journal_text = handle.read()
        except OSError as exc:
            print(f"watchdog: cannot load journal: {exc}",
                  file=sys.stderr)
            return 1
    if journal_text is not None:
        journal_alerts = journal_watch_tick(journal_text)
    else:
        journal_alerts = []

    def _report(alerts):
        print(f"watchdog: {len(alerts)} alert(s)")
        if args.announce:
            for line in announcements_for(alerts):
                print(line)

    if args.once:
        _report(tick(snapshot, beat=beat_cb) + journal_alerts)
        return 0
    count = 0
    try:
        while args.max_ticks is None or count < args.max_ticks:
            _report(tick(snapshot, beat=beat_cb))
            count += 1
            if args.max_ticks is not None and count >= args.max_ticks:
                break
            time.sleep(args.interval)
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
