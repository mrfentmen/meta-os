#!/usr/bin/env python3
"""OS-093: relay-uplink, the order door for one Meta OS machine.

A small CLI program, not an agent. It holds the machine's side of
the cloud connection: a plain-English order sent from Dale's phone
lands here, is validated, deduplicated, and signed, and becomes a
job-set intake record the queue owns from that moment on. That is
the whole job of this program.

Source of truth, stated first: the order record itself (id, text,
origin), never a bus message counter. The uplink reads orders, not
messages: replaying bus messages, skipping them, or corrupting a
stored counter changes nothing, because an order that exists and
has not been taken in is a fact, not a count.

What this program is not:

- It makes no model calls and holds no session of its own. It
  does not turn the order into a plan: planning is the DSP
  dispatch path (DSP-001 prompt, DSP-002 parser, DSP-007
  approval gate, DSP-008 poster). An intake record is a job set
  waiting for that path, not a posted job, so the uplink can
  never auto-post past the approval gate.
- It posts nothing to the bus and moves no claim. An intake
  record is printed by the caller-facing CLI and stored by the
  caller, not announced.
- It invents nothing. An order with no id, empty text, or no
  origin is rejected with its reason, never repaired with a
  guessed id or a placeholder goal. A job-set record carries
  the order's raw text as its spec and is marked ORDER, with
  no invented files and no invented accept lines (the DSP-017
  fallback honesty rule, applied to orders).
- It holds no credential. Signing uses a caller-supplied key
  (HMAC-SHA256 over order id + text, the jobs.py v2 signing
  shape); with no key the intake is marked unsigned, and in
  crew mode an unsigned intake is refused outright (the
  DSP-009 rule) while the order stays pending, not lost.

Connection health is a pure state machine over the same state
the intake runs on:

- record_failure() counts consecutive failures and sets
  next_retry_at by exponential backoff: 5s, 10s, 20s, ...,
  capped at 300s. A network kill mid-flight therefore costs
  a bounded wait, never a hot retry loop and never a
  forgotten order.
- record_success() resets the failure count and clears the
  retry time: one good connection proves the door is open
  again, no matter how long it was shut.
- tick() drains pending orders in received order the moment
  the connection is back, deduplicated by order id, so an
  order queued while the machine was off is picked up at
  boot (the OS-099 machine-off hour, at the intake layer)
  with zero duplicates and zero loss.

Inputs (pure functions; the CLI loads them from JSON files):

- orders: a list of order dicts. Fields read: id (required),
  text (required, non-empty), origin (required, e.g. the
  phone), received_at (unix seconds, for the record only,
  never invented when absent).
- state: a dict the caller owns. Fields read: seen_ids (list
  of order ids already taken in), pending (list of order
  dicts queued while offline), failures (consecutive
  connection failures), next_retry_at (unix seconds or
  None). tick() never mutates its inputs; it returns
  (events, new_state) and the caller owns storing new_state.

Events, one per order per tick, each naming the order id:

- intake: the order became a signed (or, outside crew mode,
  honestly unsigned) job-set record.
- queued: the connection is down, so the valid order waits
  in pending instead of being lost.
- duplicate: an order id already taken in, or already
  pending, is seen again; no second record is made.
- rejected: the order fails validation; the reason names
  exactly what is missing.
- unsigned-refused: crew mode with no signing key; the
  order stays pending for a keyed run, never dropped.
"""

import argparse
import hashlib
import hmac
import json
import sys

BACKOFF_BASE_SECONDS = 5
BACKOFF_CAP_SECONDS = 300


def backoff_seconds(failures):
    """Wait after `failures` consecutive failures: 5, 10, 20, ... capped 300."""
    if failures <= 0:
        return 0
    wait = BACKOFF_BASE_SECONDS * (2 ** (failures - 1))
    return min(wait, BACKOFF_CAP_SECONDS)


def empty_state():
    return {"seen_ids": [], "pending": [], "failures": 0, "next_retry_at": None}


def validate_order(order):
    """Return (True, '') for a takeable order, else (False, reason)."""
    if not isinstance(order, dict):
        return False, "order is not an object"
    if not order.get("id"):
        return False, "order id missing"
    if not isinstance(order.get("text"), str) or not order["text"].strip():
        return False, "order text empty"
    if not order.get("origin"):
        return False, "order origin missing"
    return True, ""


def sign_intake(key, order_id, text):
    """HMAC-SHA256 over order id + text, the jobs.py v2 signing shape."""
    msg = (str(order_id) + "\n" + text).encode("utf-8")
    return hmac.new(key.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def record_failure(state, now):
    """One failed connection attempt: bump failures, set the next retry."""
    new = dict(state)
    failures = int(state.get("failures", 0)) + 1
    new["failures"] = failures
    new["next_retry_at"] = now + backoff_seconds(failures)
    return new


def record_success(state):
    """One good connection: the failure count and retry time clear."""
    new = dict(state)
    new["failures"] = 0
    new["next_retry_at"] = None
    return new


def _intake_record(order, key):
    record = {
        "order_id": order["id"],
        "text": order["text"],
        "origin": order["origin"],
        "received_at": order.get("received_at"),
        "kind": "ORDER",
        "signed": bool(key),
        "signature": sign_intake(key, order["id"], order["text"]) if key else None,
    }
    return record


def _take_in(state, order, key, crew_mode):
    """Take one validated order in. Returns (event, new_state)."""
    seen = list(state.get("seen_ids", []))
    pending = list(state.get("pending", []))
    if order["id"] in seen or any(p.get("id") == order["id"] for p in pending):
        return {"type": "duplicate", "order_id": order["id"]}, state
    if crew_mode and not key:
        new = dict(state)
        new["pending"] = pending + [order]
        return {"type": "unsigned-refused", "order_id": order["id"],
                "reason": "crew mode requires a signing key"}, new
    new = dict(state)
    new["seen_ids"] = seen + [order["id"]]
    new["pending"] = [p for p in pending if p.get("id") != order["id"]]
    return {"type": "intake", "order_id": order["id"],
            "record": _intake_record(order, key)}, new


def tick(state, orders, now, connected, key=None, crew_mode=False):
    """One uplink cycle. Returns (events, new_state); inputs untouched.

    When disconnected, valid new orders queue in pending and no
    intake is made. When connected, pending orders drain first
    in received order, then new orders, each deduplicated by id.
    Invalid orders are rejected with a reason in either mode.
    """
    events = []
    cur = {
        "seen_ids": list(state.get("seen_ids", [])),
        "pending": list(state.get("pending", [])),
        "failures": state.get("failures", 0),
        "next_retry_at": state.get("next_retry_at"),
    }
    if connected:
        cur = record_success(cur)
        drain = list(cur["pending"])
        cur["pending"] = []
        for order in drain:
            ok, reason = validate_order(order)
            if not ok:
                events.append({"type": "rejected", "order_id": order.get("id"),
                               "reason": reason})
                continue
            event, cur = _take_in(cur, order, key, crew_mode)
            events.append(event)
        for order in orders:
            ok, reason = validate_order(order)
            if not ok:
                events.append({"type": "rejected", "order_id": order.get("id"),
                               "reason": reason})
                continue
            event, cur = _take_in(cur, order, key, crew_mode)
            events.append(event)
    else:
        cur = record_failure(cur, now)
        for order in orders:
            ok, reason = validate_order(order)
            if not ok:
                events.append({"type": "rejected", "order_id": order.get("id"),
                               "reason": reason})
                continue
            if order["id"] in cur["seen_ids"] or any(
                    p.get("id") == order["id"] for p in cur["pending"]):
                events.append({"type": "duplicate", "order_id": order["id"]})
                continue
            cur["pending"] = list(cur["pending"]) + [order]
            events.append({"type": "queued", "order_id": order["id"]})
    return events, cur


def _load_json(path, default):
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default
    except (OSError, ValueError) as exc:
        print("relay-uplink: cannot read %s: %s" % (path, exc), file=sys.stderr)
        sys.exit(2)


def main(argv=None):
    parser = argparse.ArgumentParser(description="OS-093 relay-uplink (first light)")
    parser.add_argument("--once", action="store_true", help="run one cycle and exit")
    parser.add_argument("--loop", action="store_true", help="repeat cycles until stopped")
    parser.add_argument("--interval", type=int, default=10, help="seconds between loop cycles")
    parser.add_argument("--max-cycles", type=int, default=0, help="loop cycles then exit (0 = forever)")
    parser.add_argument("--orders-file", required=True)
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--key-file", default=None)
    parser.add_argument("--crew-mode", action="store_true")
    parser.add_argument("--disconnected", action="store_true",
                        help="run the cycle with the connection down")
    parser.add_argument("--now", type=int, default=0)
    args = parser.parse_args(argv)
    if not args.once and not args.loop:
        parser.error("one of --once or --loop is required")
    key = None
    if args.key_file:
        try:
            with open(args.key_file, "r", encoding="utf-8") as fh:
                key = fh.read().strip() or None
        except OSError as exc:
            print("relay-uplink: cannot read key file: %s" % exc, file=sys.stderr)
            return 2
    cycles = 0
    while True:
        orders = _load_json(args.orders_file, [])
        if not isinstance(orders, list):
            print("relay-uplink: orders file must hold a JSON list", file=sys.stderr)
            return 2
        state = _load_json(args.state_file, empty_state())
        if not isinstance(state, dict):
            print("relay-uplink: state file must hold a JSON object", file=sys.stderr)
            return 2
        events, new_state = tick(state, orders, args.now,
                                 connected=not args.disconnected,
                                 key=key, crew_mode=args.crew_mode)
        for event in events:
            print(json.dumps(event, sort_keys=True), flush=True)
        with open(args.state_file, "w", encoding="utf-8") as fh:
            json.dump(new_state, fh, sort_keys=True)
        cycles += 1
        if args.once or (args.max_cycles and cycles >= args.max_cycles):
            return 0
        import time
        time.sleep(args.interval)


if __name__ == "__main__":
    sys.exit(main())
