"""intel/notify.py — the OS notification service.

One entry point every OS producer (jobs, overseer, drivers,
uplink, watchman, brief) calls to notify a human or a crewmate:

    from intel import notify
    record, line = notify.notify(
        "overseer", "warning", "Job 12 stalled for 30m",
        topic="jobs", target="mrfentmen", room="1",
        dedupe_key="job-12-stall")

notify() writes a durable notification record (intel.store
write_notify: <prefix>:intel:notify:<id> plus the history
index) and returns it with its bus line. The line format
mirrors the frozen WDG-015 alert line:

    NOTIFY:<id> <severity> [<topic>] <text>

with "@<target>" right after the topic when the notification
targets one nick instead of everyone.

This module posts nothing itself (the WDG-015 posting rule):
callers that own a bus surface take the returned line and post
it, or call post_line(). The relay viewer's Notifications
panel renders NOTIFY lines (and ALERT lines) from any room,
with an unread badge, so a posted line reaches the human on
every surface the bus reaches: viewer panel, browser
notification, phone push fan-out.

Lifecycle mirrors alerts (WDG-014): open -> acknowledged ->
resolved, via intel.store.acknowledge_notify() /
resolve_notify(). A re-notify of an unresolved record bumps
its count and last_seen instead of duplicating it; a resolved
record that fires again starts a fresh occurrence.

CLI (the poster of last resort, run by a human or an agent
that owns its bus surface):

    python3 -m intel.notify send overseer warning "Job 12 stalled" \
        --topic jobs --target mrfentmen --room 1 --post
    python3 -m intel.notify list [--room 1] [--status open]
    python3 -m intel.notify ack <id> [--by nick]
    python3 -m intel.notify resolve <id>
"""

import argparse
import sys

import relay_common as rc

from . import store as _store

__all__ = ["notify", "render_line", "post_line", "pending",
           "acknowledge", "resolve", "SEVERITIES"]

SEVERITIES = _store.NOTIFY_SEVERITIES


def render_line(record):
    """The one-line bus rendering of a notification record.

    Format: "NOTIFY:<id> <severity> [<topic>] <text>", exactly
    one line (embedded newlines flatten to spaces, so a line
    can never smuggle a second message onto the bus). A record
    targeted at one nick renders "@<target>" after the topic.
    """
    if not isinstance(record, dict):
        return None
    text = record.get("text")
    if not isinstance(text, str) or not text:
        return None
    target = record.get("target")
    mention = f" @{target}" if target and target != "all" else ""
    line = (f"NOTIFY:{record.get('id')} {record.get('severity')} "
            f"[{record.get('topic')}]" + mention + f" {text}")
    return " ".join(line.splitlines())


def notify(source, severity, text, topic="general", target="all",
           room="main", dedupe_key=None, now=None):
    """Write a notification record; return (record, line).

    The record is durable and idempotent per dedupe key (see
    store.write_notify). Nothing is posted to any bus here.
    """
    record = _store.write_notify(
        source, severity, text, topic=topic, target=target,
        room=room, dedupe_key=dedupe_key, now=now)
    return record, render_line(record)


def post_line(line, room="main", nick=None):
    """Post a rendered NOTIFY line to a room's bus list.

    The line is prefixed "<nick>: " like every bus message;
    the nick defaults to this process's configured relay nick.
    Returns the bus_push response. Callers own this call (the
    WDG-015 posting rule): library code never reaches it.
    """
    if not line:
        return None
    who = nick or rc.NICK
    return rc.bus_push(f"{who}: {line}", key=rc.bus_key(room))


def pending(room=None, target=None, status="open"):
    """Unresolved notifications, oldest first (brief/dashboard/CLI)."""
    return _store.query_notify(room=room, target=target, status=status)


def acknowledge(notify_id, by=None, now=None):
    """open -> acknowledged (see store.acknowledge_notify)."""
    return _store.acknowledge_notify(notify_id, by=by, now=now)


def resolve(notify_id, now=None):
    """open/acknowledged -> resolved (see store.resolve_notify)."""
    return _store.resolve_notify(notify_id, now=now)


def _print_record(record):
    line = render_line(record) or record.get("id", "?")
    print(f"{record.get('id')} [{_store.notify_status(record)} "
          f"x{record.get('count')}] {line}")


def main(argv=None):
    ap = argparse.ArgumentParser(prog="intel.notify")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_send = sub.add_parser("send", help="write a notification record")
    p_send.add_argument("source")
    p_send.add_argument("severity", choices=list(SEVERITIES))
    p_send.add_argument("text")
    p_send.add_argument("--topic", default="general")
    p_send.add_argument("--target", default="all")
    p_send.add_argument("--room", default="main")
    p_send.add_argument("--dedupe-key", default=None)
    p_send.add_argument("--post", action="store_true",
                        help="also post the NOTIFY line to the room")

    p_list = sub.add_parser("list", help="list notifications")
    p_list.add_argument("--room", default=None)
    p_list.add_argument("--status", default=None,
                        choices=list(_store.NOTIFY_STATUSES))
    p_list.add_argument("--target", default=None)

    p_ack = sub.add_parser("ack", help="acknowledge a notification")
    p_ack.add_argument("notify_id")
    p_ack.add_argument("--by", default=None)

    p_res = sub.add_parser("resolve", help="resolve a notification")
    p_res.add_argument("notify_id")

    args = ap.parse_args(argv)
    try:
        if args.cmd == "send":
            record, line = notify(
                args.source, args.severity, args.text, topic=args.topic,
                target=args.target, room=args.room,
                dedupe_key=args.dedupe_key)
            _print_record(record)
            if args.post:
                post_line(line, room=args.room)
                print(f"POSTED to {rc.bus_key(args.room)}")
            return 0
        if args.cmd == "list":
            records = _store.query_notify(
                room=args.room, status=args.status, target=args.target)
            for record in records:
                _print_record(record)
            if not records:
                print("NO_NOTIFICATIONS")
            return 0
        if args.cmd == "ack":
            record = acknowledge(args.notify_id, by=args.by)
            if record is None:
                print(f"NOT_FOUND {args.notify_id}", file=sys.stderr)
                return 2
            _print_record(record)
            return 0
        if args.cmd == "resolve":
            record = resolve(args.notify_id)
            if record is None:
                print(f"NOT_FOUND {args.notify_id}", file=sys.stderr)
                return 2
            _print_record(record)
            return 0
    except ValueError as e:
        print(f"ERROR: {e}", file=sys.stderr)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main())
