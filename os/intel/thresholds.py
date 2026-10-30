"""Watchdog threshold constants (FND-030).

Single shared module: the watchdog and its tests import thresholds from
here only, never hardcode minutes elsewhere. Values come from the lane
plan (plan/lanes/MILO.md), tuned in WDG-027 and LOCKED in INT-022:
the INT-022 rerun of intel/evals/watchdog_tuning.py (26 cases, 0 false
positives, 0 false negatives) plus the grown integration fixtures
(INT-020 e2e surfaces, INT-021 drill tournament 3/3) gave no failing
case, so no value changed at lock time. A later change needs a failing
fixture and a new tuning-table run, not a guess; the demo profile
(DEM-013/OS-038) overrides these through the environment only and
never edits this file.

WDG-018 env overrides: every threshold below is env-overridable
through a WATCHDOG_* variable named in its comment, read once at
import time. A long-running process picks up a changed value by
reloading this module (importlib.reload) — every consumer (watchdog
detectors, store writer, tick cap) reads the attribute at call time,
never a copied value, so a reload changes detector behavior with
no code edit. That is also how the demo thresholds profile
(DEM-013/OS-038) is meant to work: same code, shorter windows,
set through the environment on the demo image only. An unset,
blank, unparseable, or below-minimum variable falls back to the
documented default silently: a typo in the environment must
never crash the watchdog or invent a threshold.

All ages are in minutes unless the name says seconds. Ages are computed
from Redis server time where available (WDG-026); otherwise wall clock.
"""

import os


def _env_int(name, default, minimum):
    """One env-overridable integer threshold.

    Returns the WATCHDOG_* variable's int value when it parses
    and is at least minimum, else the default. Blank and
    unparseable values fall back rather than raising: the
    watchdog must keep running on a bad environment, on the
    documented default, not on a guessed number.
    """
    raw = os.environ.get(name)
    if raw is None:
        return default
    raw = raw.strip()
    if not raw:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    if value < minimum:
        return default
    return value

# Stall: no progress AND no heartbeat for this long (FND-030 default).
# Env: WATCHDOG_STALL_MINUTES.
STALL_MINUTES = _env_int("WATCHDOG_STALL_MINUTES", 10, 0)

# Progress stall uses the same window: heartbeat alive, but the job's
# progress note has not changed for this long (WDG-003).
# Env: WATCHDOG_PROGRESS_STALL_MINUTES.
PROGRESS_STALL_MINUTES = _env_int("WATCHDOG_PROGRESS_STALL_MINUTES",
                                  10, 0)

# Lease-risk warning (WDG-004): warn when a claimed job's lease expires
# within this window AND no heartbeat arrived in the quiet window.
# Env: WATCHDOG_LEASE_RISK_WINDOW_MINUTES,
# WATCHDOG_LEASE_RISK_QUIET_MINUTES.
LEASE_RISK_WINDOW_MINUTES = _env_int(
    "WATCHDOG_LEASE_RISK_WINDOW_MINUTES", 5, 0)
LEASE_RISK_QUIET_MINUTES = _env_int(
    "WATCHDOG_LEASE_RISK_QUIET_MINUTES", 2, 0)

# Alert dedupe cooldown (WDG-013): same dedupe key inside this window
# updates last_seen instead of creating a new alert.
# Env: WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES.
ALERT_DEDUPE_COOLDOWN_MINUTES = _env_int(
    "WATCHDOG_ALERT_DEDUPE_COOLDOWN_MINUTES", 30, 0)

# Silent-room info record (WDG-009): build room with claimed jobs but
# zero messages for this long during work hours. LOCKED in INT-022
# (60 min; no failing case at lock time, see tuning doc).
# Env: WATCHDOG_SILENT_ROOM_MINUTES.
SILENT_ROOM_MINUTES = _env_int("WATCHDOG_SILENT_ROOM_MINUTES", 60, 0)

# Watchdog self-heartbeat (WDG-016): the beat key
# muse-bus:intel:wd:beat carries a TTL of five missed 60-second
# loop ticks (intel/watchdog.py --interval default), matching
# the dashboard's BEAT_STALE_S (bus.html, DSH-015). A beat older
# than this is gone from Redis, so the dashboard can never
# render a stale tick as alive.
# Env: WATCHDOG_BEAT_TTL_SECONDS.
WATCHDOG_BEAT_TTL_SECONDS = _env_int("WATCHDOG_BEAT_TTL_SECONDS",
                                    300, 1)

# Tick budget guard (WDG-017): a tick never evaluates unbounded
# message history. Messages are walked page by page like digest.py
# (PAGE = 1000 there, TICK_PAGE_SIZE here) and the tick window
# keeps only the newest TICK_MAX_MESSAGES; older messages are
# dropped before any detector runs. The only message reader
# (WDG-009 silent-room) needs just the newest message, so the
# cap cannot change any verdict. Jobs are never capped: every
# detector needs full job visibility, and jobs are evaluated
# one record at a time, not as history.
# Env: WATCHDOG_TICK_PAGE_SIZE, WATCHDOG_TICK_MAX_MESSAGES.
# Both need a positive value: paginate() raises on a non-positive
# page size and a zero message cap would drop every message, so
# the minimum is 1 and anything smaller falls back to the default.
TICK_PAGE_SIZE = _env_int("WATCHDOG_TICK_PAGE_SIZE", 1000, 1)
TICK_MAX_MESSAGES = _env_int("WATCHDOG_TICK_MAX_MESSAGES", 1000, 1)

# Watchman staleness (OS-122): a watchman whose bell is
# older than this is dead, even if its alive flag still
# says True. Added for OS-122; it is not part of the
# INT-022 locked set, because watching the watchman did
# not exist at lock time. Env: WATCHDOG_WATCHMAN_STALE_MINUTES.
WATCHMAN_STALE_MINUTES = _env_int(
    "WATCHDOG_WATCHMAN_STALE_MINUTES", 5, 0)

# Timer fallback sweep interval (OS-121): how often the
# slow timer sweeps the board when the watchman is dead.
# Added for OS-121; it is not part of the INT-022 locked
# set, because the timer fallback did not exist at lock
# time. Env: WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS.
TIMER_SWEEP_INTERVAL_SECONDS = _env_int(
    "WATCHDOG_TIMER_SWEEP_INTERVAL_SECONDS", 300, 1)

# Reference only, owned by jobs.py (LEASE_DEFAULT = 1800s there):
# the watchdog reads lease values off the job hash, never redefines them.
# Deliberately NOT env-overridable here: it is jobs.py's lease, and
# two modules overriding the same number would disagree silently.
LEASE_DEFAULT_SECONDS = 1800
