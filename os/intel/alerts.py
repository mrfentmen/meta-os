"""intel/alerts.py — alert record lifecycle helpers.

Alert records live at muse-bus:intel:alert:<id> (see intel.store).
This module owns their lifecycle on top of the store: raise, read,
acknowledge, resolve — one shape consumed identically by the
watchdog (writer), the dashboard alerts feed, and the intel CLI.
Lifecycle semantics are WDG-014; the store round-trip underneath is
FND-004, the record shape is WDG-010, dedupe is WDG-013.

Lifecycle, in order: open -> acknowledged -> resolved. A record
starts open (status "open", acknowledged_at and resolved_at null).
acknowledge_alert() stamps acknowledged_at; resolve_alert() stamps
resolved_at (by hand, or via the CLI's --resolve). A tick that no
longer fires an alert resolves it automatically through
auto_resolve_cleared(): the caller passes the ids it tracks and
the latest tick's live ids, and every tracked alert not live is
resolved. A resolved record that fires again starts a fresh open
occurrence under the same id (WDG-013); an acknowledged record
re-fired inside the cooldown keeps its acknowledged status.

These helpers are thin wrappers over intel.store, which owns the
transitions and validation; they exist so the CLI, the dashboard,
and the watchdog all call the lifecycle by the same names.
"""

from . import store as _store

__all__ = ["acknowledge_alert", "resolve_alert",
           "auto_resolve_cleared", "alert_status"]


def acknowledge_alert(alert_id, now=None):
    """WDG-014: open -> acknowledged; None if missing, ValueError
    if already resolved (see intel.store.acknowledge_alert)."""
    return _store.acknowledge_alert(alert_id, now=now)


def resolve_alert(alert_id, now=None):
    """WDG-014: open/acknowledged -> resolved; None if missing
    (see intel.store.resolve_alert)."""
    return _store.resolve_alert(alert_id, now=now)


def auto_resolve_cleared(known_ids, live_ids, now=None):
    """WDG-014: resolve every tracked alert the latest tick no
    longer fires; returns the resolved records in known order
    (see intel.store.auto_resolve_cleared)."""
    return _store.auto_resolve_cleared(known_ids, live_ids, now=now)


def alert_status(record):
    """WDG-014: lifecycle status of a record, legacy-safe
    (see intel.store.alert_status)."""
    return _store.alert_status(record)
