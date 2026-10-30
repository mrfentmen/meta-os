"""Briefing engine: extract structured sections from a snapshot.

Snapshot shape (until Pax's FND-014 snapshot API lands, this is the
shape the extractors accept — a plain dict, no network, no Redis):

    {
      "messages": [ {"nick": str, "text": str, "ts": int}, ... ]
                  or plain bus strings "<nick>: <text>",
      "jobs": [ {"id": str, "title": str, "status": str,
                 "claim": str, "note": str,
                 "claimed_at": int, "lease_until": int}, ... ],
      "presence": [nick, ...],
      "caps": {nick: {"caps": str, "roles": str, ...}, ...},
      "alerts": [ {"id": str, "summary": str}, ... ],
      # OS-051 (boot briefs only): "previous_session" is the
      # record build_previous_session derives from the stored
      # brief and the shutdown job list: {"last_brief_at": str,
      # "jobs_completed": [title, ...], "open_threads": [title,
      # ...]}. The template composer renders it as the digest
      # line only when boot=True; without it, a boot brief says
      # nothing about a previous session.
      # OS-062 (boot briefs only): "system_state" is the live
      # machine state the boot brief reports, one line each:
      # {"drivers": [name, ...], "gateway_healthy": bool or
      # None, "skill_apps": [name, ...]}. The template
      # composer renders it with system_state_lines only when
      # boot=True; a non-boot brief never carries these lines,
      # and a missing or unknown field is reported as not
      # reported, never guessed and never silently omitted.
      # OS-103 (boot briefs only, only when the snapshot
      # carries the key): "environment" is the launch-time
      # surroundings the brief reports as its information
      # layer, one line each: {"repo": {"branch": str,
      # "commit": str, "dirty": int, "as_of": int},
      # "bus": {"rooms": [str, ...], "messages": int,
      # "as_of": int}, "jobs": [job dicts as above],
      # "budget": {"lane": str, "spent": int, "cap": int
      # or "remaining": int, "as_of": int}, "as_of": int
      # for the jobs line}. The template composer renders
      # it with environment_lines only when boot=True and
      # the key is present; a snapshot without the key
      # carries no environment lines at all, so older boot
      # briefs keep their exact shape. A field with no
      # as_of time is labelled as time-not-reported, never
      # silently presented as current.
      # OS-127 (boot briefs only, only when the snapshot
      # carries the key): "recovery" is the lease-sweep
      # reconciliation for in-flight jobs recovered at
      # this boot: {"recovered": [{"id": str, "title":
      # str, "baton_step": str or int}, ...],
      # "sweep_count": int, "corrupted": [{"id": str,
      # "title": str}, ...]}. The template composer
      # renders it with recovery_line only when boot=True
      # and the key is present; a snapshot without the
      # key carries no recovery line at all, so a brief
      # never claims zero recovered without a sweep
      # record to reconcile against, and older boot
      # briefs keep their exact shape.
      # OS-117 (morning briefs, Phase B crew-of-crews):
      # "federation" is the joined-machines record the
      # morning brief reports as one section:
      # {"machines": [{"name": str, "completions":
      # [title, ...], "cross_machine_jobs": [{"id": str,
      # "title": str, "status": str}, ...]}, ...],
      # "trust_events": [{"kind": "join" or "refusal",
      # "machine": str, "detail": str}, ...]}. The
      # template composer renders it with
      # federation_lines only when the record names at
      # least two usable machines; a single-machine
      # record renders the section absent, never
      # empty-padded, and a snapshot without the key
      # carries no section at all, so older briefs keep
      # their exact shape.
    }

Missing sections are treated as empty, never invented. No function
here calls Spark, posts to the bus, or touches a secret. The Spark
pass named in BRF-004 (a language-model pass over decisions) is
NOT implemented here: the plan records real Spark transport as a
hard blocker (FakeTransport rejected, endpoint/key unnamed), so
the extractors below are marker-and-record passes only, and they
say so wherever a Spark pass would have run.
"""

import json
import os
import re
import subprocess
import time

import relay_common as rc

from . import store as _store

# Decision markers, at the start of a message, case-insensitive.
# DONE: and BLOCKED: are the wire announcements jobs.py already
# emits; DECISION: is the explicit marker a crew member writes.
_DECISION_RE = re.compile(
    r"^\s*(DONE|BLOCKED|DECISION)\s*:\s*(.+?)\s*$",
    re.IGNORECASE)


def _message_parts(message):
    """Return (nick, text) for a store entry dict or a bus string."""
    if isinstance(message, dict):
        return message.get("nick", ""), message.get("text", "")
    if isinstance(message, str):
        nick, sep, text = message.partition(": ")
        if sep:
            return nick, text
        return "", message
    return "", ""


def _window_line(snapshot):
    """BRF-013: the window line a brief opens with.

    Returns the snapshot's stated window verbatim when one is
    given, otherwise says plainly that no window was stated.
    A truncated window (history starts mid-story) must state its
    start point, never imply earlier history the machine does not
    have.
    """
    window = snapshot.get("source_window")
    if isinstance(window, dict):
        max_hours = window.get("max_hours")
        # BRF-024: parse_since returns a float, but the window
        # line should read "last 2 hours", not "last 2.0 hours".
        if isinstance(max_hours, float) and max_hours.is_integer():
            max_hours = int(max_hours)
        return (f"Window: last {window.get('max_messages')} messages "
                f"or last {max_hours} hours, "
                f"{window.get('messages_kept')} kept, "
                f"{window.get('messages_dropped')} dropped")
    if window:
        return f"Window: {window}"
    start = snapshot.get("window_start")
    if start:
        return (f"Window: from {start} onward. "
                "Earlier history is not in this window.")
    return "Window: not stated in this snapshot"


BRIEF_SECTIONS = ("Decisions", "In flight", "Owners",
                  "Blocked and why", "Watch items")
BRIEF_KINDS = ("morning", "onjoin", "ondemand")


BRIEF_BUDGETS = {"morning": 220, "onjoin": 150, "ondemand": 300}


# BRF-028: regeneration guard window in seconds. A same room + kind
# + source-window brief requested again inside this window returns
# the stored brief instead of a new Spark call.
BRIEF_REGENERATION_WINDOW_SECONDS = 300


# BRF-026: canned one-liners for the three brief failure cases,
# used verbatim by the dashboard and the CLI. One line each,
# plain English, no invented detail: "unavailable" is a
# requested brief that is not there, "spark_down" is a Spark-only
# brief that could not be written, "no_data" is a room with no
# briefs at all. No other failure copy may be improvised.
BRIEF_FAILURE_COPY = {
    "unavailable": "No brief is available right now. Try again in a few minutes.",
    "spark_down": ("The brief writer is down, so no fresh brief could "
                   "be written. Try again later."),
    "no_data": "No brief yet, this room has no activity to brief on.",
}


def brief_failure_line(kind):
    """BRF-026: the canned one-liner for a brief failure kind.

    kind is one of "unavailable", "spark_down", or "no_data".
    Raises ValueError on an unknown kind — a failure line must
    never be invented on the spot.
    """
    try:
        return BRIEF_FAILURE_COPY[kind]
    except KeyError:
        raise ValueError(
            f"unknown brief failure kind: {kind!r}") from None


def _trim_to_budget(text, budget):
    """BRF-007 rewrite pass: cut a brief to its word budget.

    Drops bullet lines from the end first (Watch items, then
    Blocked, then Owners, then In flight, then Decisions), keeping
    section headings and the window line. If the brief is still
    over budget after every bullet is gone, truncates by words.
    Returns the trimmed text; a brief already within budget is
    returned unchanged.
    """
    if not isinstance(text, str) or len(text.split()) <= budget:
        return text
    lines = text.split("\n")
    while len("\n".join(lines).split()) > budget:
        bullet_indexes = [i for i, line in enumerate(lines)
                          if line.startswith("- ")]
        if not bullet_indexes:
            break
        del lines[bullet_indexes[-1]]
    trimmed = "\n".join(lines)
    if len(trimmed.split()) > budget:
        trimmed = " ".join(trimmed.split()[:budget - 1]) + " (trimmed)"
    return trimmed


BRIEF_PROMPT_FILES = {"morning": "brief_morning.md",
                      "onjoin": "brief_onjoin.md",
                      "ondemand": "brief_ondemand.md"}

# BRF-007 follow-up: v2 prompt files. Only morning and onjoin
# have a v2 (BRF-019); ondemand has none, so a v2 request for
# ondemand has no file on purpose — see load_brief_prompt.
BRIEF_PROMPT_V2_FILES = {"morning": "brief_morning_v2.md",
                          "onjoin": "brief_onjoin_v2.md"}


def brief_prompt_path(kind, prompts_dir=None, version="v1"):
    """BRF-007 follow-up: path of the prompt file for a kind.

    `version` is "v1" or "v2"; anything else has no file, as do
    unknown kinds and (for v2) ondemand, which has no v2 file.
    Those cases return None instead of guessing a filename
    that does not exist.
    """
    if version == "v1":
        files = BRIEF_PROMPT_FILES
    elif version == "v2":
        files = BRIEF_PROMPT_V2_FILES
    else:
        return None
    name = files.get(kind)
    if name is None:
        return None
    base = prompts_dir or os.path.join(os.path.dirname(__file__),
                                       "prompts")
    return os.path.join(base, name)


def load_brief_prompt(kind, prompts_dir=None, version="v1"):
    """BRF-007 follow-up: text of the prompt file for a kind.

    `version` selects v1 (default, exactly as before) or v2.
    Returns "" for an unknown kind, an unknown version, or an
    unreadable file, never raising, so a missing prompt file
    can never fail a brief: the composer then sends no system
    text, exactly as before. A v2 request for ondemand also
    returns "": ondemand has no v2 file, and silently falling
    back to its v1 text would hand Spark v1 rules under a v2
    label, so no fallback is made — the caller gets nothing
    and the brief goes out with no system text, as before.
    """
    path = brief_prompt_path(kind, prompts_dir=prompts_dir,
                             version=version)
    if path is None:
        return ""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except (OSError, ValueError):
        return ""


def compose_brief(snapshot, kind="morning", client=None,
                  max_messages=500, max_hours=24, now=None, boot=False,
                  system_prompt=None):
    """BRF-007: Spark composer with template fallback and budget.

    `client` is a SparkClient (or any object with
    complete(prompt, system=..., lane_feature=...)); when it is
    None, or when the Spark call raises, the BRF-008 template
    brief is used instead — never a made-up brief, never a
    silent failure. The returned text is redacted (BRF-014) and
    trimmed to the kind budget (FND-034). A template fallback
    keeps its TEMPLATE first line, so readers can tell which
    path produced the brief. max_messages/max_hours/now are the
    BRF-024 ad hoc window: they are passed to the window cap, so
    a --since 2h brief caps to 2 hours instead of the 24h default.
    system_prompt is the prompt-file text to send as the client's
    system text — typically load_brief_prompt(kind) — so the
    file's rules reach Spark instead of living only as a spec. It
    defaults to None, which keeps the old call shape exactly, and
    the budget trim and redaction above still apply to the
    returned text, so the file alone can never widen a brief
    past budget or leak a secret-shaped string.
    """
    snapshot = cap_snapshot_window(snapshot or {},
                                   max_messages=max_messages,
                                   max_hours=max_hours, now=now)
    if kind not in BRIEF_BUDGETS:
        kind = "morning"
    budget = BRIEF_BUDGETS[kind]
    if client is None:
        return _trim_to_budget(
            compose_template_brief(snapshot, boot=boot, kind=kind),
            budget)
    sections = {
        "Decisions": extract_decisions(snapshot),
        "Blocked": extract_blocked(snapshot),
        "Owners": extract_owners(snapshot),
        "Alerts": snapshot.get("alerts") or [],
    }
    prompt = (f"Write a {kind} brief from this section data only. "
              f"Do not invent facts. Keep it under {budget} words. "
              f"Sections: {sections!r}")
    try:
        text = client.complete(prompt, system=system_prompt or None,
                               lane_feature="brief")
    except Exception:
        return _trim_to_budget(
            compose_template_brief(snapshot, boot=boot, kind=kind),
            budget)
    return _trim_to_budget(redact_secrets(text or ""), budget)


def compose_spark_brief(snapshot, kind="morning", client=None,
                        system_prompt=None):
    """BRF-026: Spark-only brief, or the spark_down failure line.

    Unlike compose_brief, this never falls back to a template: a
    caller that needs a Spark brief (the dashboard's fresh-brief
    path) gets either the Spark text — redacted and trimmed to
    the kind budget — or the canned spark_down one-liner, never a
    silent template substitution and never a blank brief. A client
    of None, a raising client, or an empty Spark reply all count
    as Spark down. system_prompt works as in compose_brief:
    prompt-file text (typically load_brief_prompt(kind)) sent as
    the client's system text, defaulting to None.
    """
    if kind not in BRIEF_BUDGETS:
        kind = "morning"
    budget = BRIEF_BUDGETS[kind]
    if client is None:
        return brief_failure_line("spark_down")
    sections = {
        "Decisions": extract_decisions(snapshot),
        "Blocked": extract_blocked(snapshot),
        "Owners": extract_owners(snapshot),
        "Alerts": (snapshot or {}).get("alerts") or [],
    }
    prompt = (f"Write a {kind} brief from this section data only. "
              f"Do not invent facts. Keep it under {budget} words. "
              f"Sections: {sections!r}")
    try:
        text = client.complete(prompt, system=system_prompt or None,
                               lane_feature="brief")
    except Exception:
        return brief_failure_line("spark_down")
    if not text:
        return brief_failure_line("spark_down")
    return _trim_to_budget(redact_secrets(text), budget)


def morning_brief_today(snapshot, room, dry_run=False):
    """BRF-011 fix (2026-10-26, Dale's order): run TODAY, not
    tomorrow morning.

    Generates and stores a morning brief right now, at the
    current time, with no wait for the next 08:00 ET. The
    08:00 ET daily cadence is not the today plan — today's
    build runs today.
    """
    return generate_morning_brief(snapshot, room, now=None,
                                  dry_run=dry_run)


def next_morning_run(now=None, hour=8):
    """BRF-011: next 08:00 ET run time, as a Unix timestamp.

    Uses America/New_York, so the 08:00 ET brief stays at 08:00
    across daylight-saving changes. Returns the next 08:00
    strictly after `now` (or after the current time).
    """
    from datetime import datetime, time as _time, timedelta
    from zoneinfo import ZoneInfo
    tz = ZoneInfo("America/New_York")
    current = datetime.fromtimestamp(
        int(time.time() if now is None else now), tz=tz)
    candidate = current.replace(hour=hour, minute=0, second=0,
                                microsecond=0)
    if candidate <= current:
        candidate = candidate + timedelta(days=1)
    return int(candidate.timestamp())


_SINCE_PART_RE = re.compile(r"(\d+(?:\.\d+)?)\s*([mhd])")
_SINCE_UNIT_HOURS = {"m": 1 / 60, "h": 1, "d": 24}


def parse_since(value):
    """BRF-024: parse a --since window into hours (float).

    Accepts "2h", "30m", "7d", combined forms like "1h30m", and a
    plain number (read as hours). Raises ValueError on anything
    else — "yesterday", "0h", "" — so the CLI fails loudly
    instead of silently scoping a brief to the wrong window.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        hours = float(value)
        if hours <= 0:
            raise ValueError(f"invalid --since value: {value!r}")
        return hours
    text = str(value).strip().lower()
    if not text:
        raise ValueError("invalid --since value: empty string")
    parts = _SINCE_PART_RE.findall(text)
    rebuilt = "".join(f"{num}{unit}" for num, unit in parts)
    if not parts or rebuilt != text.replace(" ", ""):
        raise ValueError(f"invalid --since value: {value!r}")
    hours = sum(float(num) * _SINCE_UNIT_HOURS[unit]
                for num, unit in parts)
    if hours <= 0:
        raise ValueError(f"invalid --since value: {value!r}")
    return hours


def _brief_text_from_record(record):
    """BRF-028: text for a stored brief record.

    Records stored by generate_brief carry their text verbatim, so
    a guard hit returns exactly the brief that was generated. Older
    records (stored before the text field existed) are rendered
    from their stored sections instead — same facts, template
    layout — never re-derived from the snapshot, so a guard hit
    can never carry a fact the stored brief did not have.
    """
    record = record or {}
    text = record.get("text")
    if isinstance(text, str) and text.strip():
        return text
    lines = []
    window = record.get("source_window")
    if isinstance(window, str):
        lines.append(f"Window: {window}")
    elif isinstance(window, dict):
        lines.append(f"Window: last {window.get('max_messages')} messages "
                     f"or last {window.get('max_hours')} hours, "
                     f"{window.get('messages_kept')} kept, "
                     f"{window.get('messages_dropped')} dropped")
    for section in BRIEF_SECTIONS:
        lines.append("")
        lines.append(section)
        items = (record.get("sections") or {}).get(section) or []
        if items:
            lines.extend(f"- {item}" for item in items)
        else:
            lines.append("Nothing reported in this window")
    return "\n".join(lines) + "\n"


def find_recent_brief(room, kind, source_window, now=None):
    """BRF-028: find a stored brief for the same room, kind, window.

    Returns the stored record when one was generated inside the
    last BRIEF_REGENERATION_WINDOW_SECONDS (5 minutes), with the
    same kind and an equal source_window — or None. A store read
    failure returns None (fail open): the guard must never block
    a fresh brief, and callers that cannot reach the store simply
    generate as before. Entries are scanned newest first, so the
    most recent matching brief wins.
    """
    import time as _time
    current = int(_time.time() if now is None else now)
    try:
        entries = list_briefs(room)
    except Exception:  # noqa: BLE001 - guard failure is not fatal
        return None
    for entry in reversed(entries):
        if not isinstance(entry, dict):
            continue
        ts = entry.get("ts")
        if ts is None:
            ts = entry.get("generated_at")
        if not isinstance(ts, (int, float)) or isinstance(ts, bool):
            continue
        if ts > current:
            continue
        if current - ts > BRIEF_REGENERATION_WINDOW_SECONDS:
            continue
        try:
            record = get_brief(room, ts)
        except Exception:  # noqa: BLE001 - skip unreadable entries
            continue
        if not isinstance(record, dict):
            continue
        if record.get("kind") != kind:
            continue
        if record.get("source_window") != source_window:
            continue
        return record
    return None


def generate_brief(snapshot, room, kind="ondemand", since=None,
                   now=None, dry_run=False, client=None, boot=False,
                   system_prompt=None):
    """BRF-024: build (and, unless dry_run, store) an ad hoc brief.

    BRF-007 follow-up: `system_prompt` is prompt-file text
    (typically load_brief_prompt(kind, version=...)) passed
    through to compose_brief as the client's system text, so
    the stored-brief path can carry a prompt file at all —
    before this, generate_brief took a client but no prompt,
    so a caller that wanted prompt-file wiring had to call
    compose_brief directly and give up storage and the
    BRF-028 guard. Default None keeps the old call shape
    exactly: no system text is sent.

    `since` is a --since value (see parse_since) or a number of
    hours; None means the BRF-023 default window (500 messages
    or 24h). The snapshot is capped once to that window, and the
    text, the sections, and the record's source_window all come
    from the capped snapshot — so a --since 2h brief cannot
    carry a decision from 3 hours ago in any of the three places.
    Returns (text, record). Kind defaults to ondemand, the kind
    for ad hoc demo-rehearsal briefs; pass kind="morning" to
    scope a morning brief the same way. BRF-028: a second call
    for the same room, kind, and window inside 5 minutes returns
    the stored brief (identical generated_at) with no new Spark
    call, instead of generating a fresh one. OS-049: a boot
    brief (boot=True, kind morning) skips that guard: a boot
    brief is a new session's first brief, never a regeneration
    of the previous session's brief, so a reboot inside 5
    minutes still generates fresh. A boot record carries
    "boot": True so readers can tell it apart from an
    ordinary morning brief; the validator ignores the extra
    field, like the stored text field.
    """
    import time as _time
    generated_at = int(_time.time() if now is None else now)
    since_hours = parse_since(since)
    max_hours = since_hours if since_hours is not None else 24
    capped = cap_snapshot_window(snapshot or {}, max_messages=500,
                                 max_hours=max_hours, now=generated_at)
    # BRF-028: same room + kind + window inside 5 minutes returns
    # the stored brief, with no new Spark call and no new spend.
    # A dry run still returns the stored brief when one exists —
    # it just does not store a new one — and a guard miss falls
    # through to a fresh brief below.
    recent = find_recent_brief(room, kind,
                                capped.get("source_window", "not stated"),
                                now=generated_at)
    if recent is not None and not boot:
        return _brief_text_from_record(recent), recent
    text = compose_brief(capped, kind=kind, client=client,
                         max_messages=500, max_hours=max_hours,
                         now=generated_at, boot=boot,
                         system_prompt=system_prompt)
    sections = {
        "Decisions": [f"{d['kind']}: {d['text']}"
                      for d in extract_decisions(capped)],
        "In flight": [f"{j.get('id', '')} {j.get('title', '')}"
                       for j in capped.get("jobs") or []
                       if isinstance(j, dict)
                       and j.get("status") in ("open", "claimed")],
        "Owners": [f"{o['nick']}: "
                   + ", ".join(j["title"] for j in o["jobs"])
                   for o in extract_owners(capped)],
        "Blocked and why": [f"{j['id']} {j['title']}: {j['reason']}"
                            for j in extract_blocked(capped)],
        "Watch items": [f"{item['id']}: {item['summary']}"
                        for item in extract_watch_items(capped)],
    }
    # STR-002: the record gains the screenshot digest, built
    # from the same capped snapshot as the text and sections,
    # so a --since brief cannot carry a screenshot from outside
    # its window. The digest is refs only, never a SAM verdict:
    # verdicts come from the SAM pass (STR-004/STR-005), which
    # has not run on these refs yet.
    record = {
        "room": room,
        "generated_at": generated_at,
        "kind": kind,
        "sections": sections,
        "source_window": capped.get("source_window", "not stated"),
        # INT-008: the record names the path that actually wrote
        # the text. A client that failed mid-call falls back to
        # the template brief inside compose_brief, and its text
        # keeps the TEMPLATE first line, so the record must say
        # template too, not spark, or the dashboard would show
        # a Spark-composed label over template text.
        "model": ("template" if client is None
                  or text.startswith("TEMPLATE") else "spark"),
        "spend_id": None,
        # BRF-028: the generated text itself, so a guard hit can
        # return the stored brief verbatim instead of recomposing
        # it. Extra record fields are ignored by validation.
        "text": text,
        "screenshot_refs": extract_screenshot_refs(capped),
    }
    if boot:
        record["boot"] = True
    errors = validate_brief_record(record)
    if errors:
        raise ValueError(f"invalid brief record: {errors}")
    if not dry_run:
        store_brief(room, record)
    return text, record


def generate_morning_brief(snapshot, room, now=None, dry_run=False):
    """BRF-011: build (and, unless dry_run, store) a morning brief.

    Returns (text, record). In a dry run the record is built and
    validated but not stored, so a fake clock can prove the
    brief without touching the store. The record's sections
    come from the extractors, so every claim traces to the
    snapshot. Delegates to generate_brief (BRF-024) with the
    default window, so morning sections are window-consistent
    with the morning text.
    """
    return generate_brief(snapshot, room, kind="morning", since=None,
                          now=now, dry_run=dry_run, client=None)


def brief_index_key(room):
    """Redis key for the brief index of one room.

    The index is a single JSON list record, because the relay
    surface has no key-scan: one set/get per room, no scan
    needed. Entries are {ts, kind, generated_at}, oldest first.
    """
    clean = rc.clean_room(room) or "main"
    return f"{rc.key_prefix()}:intel:brief_index:{clean}"


def store_brief(room, record):
    """BRF-009: validate, store, and index one generated brief.

    Raises ValueError with the validation errors for an invalid
    record, so a bad brief is never stored silently. Returns the
    brief's Redis key. The record must carry source_window and
    spend_id (null for a template brief) per FND-032.
    """
    errors = validate_brief_record(record)
    if errors:
        raise ValueError(f"invalid brief record: {errors}")
    ts = record["generated_at"]
    key = _store.put_brief(room, ts, record)
    index = list_briefs(room)
    if all(entry.get("ts") != ts for entry in index):
        index.append({"ts": ts, "kind": record["kind"],
                      "generated_at": ts})
        index.sort(key=lambda entry: entry["ts"])
        rc.api_post(f"set/{brief_index_key(room)}",
                    json.dumps(index, sort_keys=True))
    return key


def get_brief(room, ts):
    """BRF-009: retrieve one stored brief by room and timestamp."""
    return _store.get_brief(room, ts)


def list_briefs(room):
    """BRF-009: index entries for a room, oldest first.

    Returns [] when no brief has been stored for the room yet,
    never an error — an empty room is not a failure.
    """
    raw = json.loads(rc.api_get(f"get/{brief_index_key(room)}"))
    result = raw.get("result") if isinstance(raw, dict) else None
    if not result:
        return []
    try:
        index = json.loads(result)
    except ValueError:
        return []
    return index if isinstance(index, list) else []


def brief_exceeds_budget(kind, text):
    """FND-034: does a brief exceed its kind budget?

    Word count counts every word in the text, including headings.
    Returns True when the count is over the budget for kind, False
    otherwise. An unknown kind has no budget to exceed, so it
    returns False — callers must validate kind separately
    (see validate_brief_record), not rely on this to catch it.
    """
    budget = BRIEF_BUDGETS.get(kind)
    if budget is None:
        return False
    if not isinstance(text, str):
        return False
    return len(text.split()) > budget


def validate_brief_record(record):
    """FND-032: validate a brief record against intel/README.md.

    Returns a list of error strings; an empty list means the
    record is valid. Never raises on a bad record — callers need
    the error list, not an exception, to log what was wrong.
    """
    errors = []
    if not isinstance(record, dict):
        return ["brief record is not a dict"]
    room = record.get("room")
    if not isinstance(room, str) or not room:
        errors.append("room must be a non-empty string")
    generated_at = record.get("generated_at")
    if not isinstance(generated_at, int) or isinstance(generated_at, bool):
        errors.append("generated_at must be a Unix timestamp int")
    kind = record.get("kind")
    if kind not in BRIEF_KINDS:
        errors.append(f"kind must be one of {list(BRIEF_KINDS)}")
    sections = record.get("sections")
    if not isinstance(sections, dict):
        errors.append("sections must be a dict")
    else:
        for section in BRIEF_SECTIONS:
            value = sections.get(section)
            if not isinstance(value, list) or not all(
                    isinstance(item, str) for item in value):
                errors.append(
                    f"sections[{section!r}] must be a list of strings")
    source_window = record.get("source_window")
    if not isinstance(source_window, (str, dict)):
        errors.append("source_window must be a string or dict")
    model = record.get("model")
    if not isinstance(model, str) or not model:
        errors.append("model must be a non-empty string")
    spend_id = record.get("spend_id")
    if spend_id is not None and not isinstance(spend_id, str):
        errors.append("spend_id must be a string or null")
    return errors


def format_brief_announcement(record):
    """BRF-010: one frozen-format announcement line for a brief.

    Returns "BRIEF:<room>:<ts> <kind>" for a brief record, or None
    when the record cannot carry a line. <room> is the
    relay_common.clean_room() output for the brief's room, with
    "main" when that cleans to empty (the same rule as
    intel/store.py brief_key); <ts> is the brief's generated_at
    Unix timestamp, the same <ts> as its store key; <kind> is one
    of BRIEF_KINDS. The line carries no section text: sections
    live only in the stored brief record. Pure: it posts nothing,
    claims nothing, and writes no record. Posting stays held
    under GOV-002 until Dale rules on the room and the wire
    format, so this builder is the whole BRF-010 surface — there
    is no post call site behind it.
    """
    if not isinstance(record, dict):
        return None
    room = record.get("room")
    if not isinstance(room, str):
        return None
    try:
        clean = rc.clean_room(room) or "main"
    except ValueError:
        return None
    generated_at = record.get("generated_at")
    if not isinstance(generated_at, int) or isinstance(generated_at, bool):
        return None
    kind = record.get("kind")
    if kind not in BRIEF_KINDS:
        return None
    return f"BRIEF:{clean}:{generated_at} {kind}"


def brief_age_seconds(record, now=None):
    """BRF-020: age of a brief record in seconds.

    record is a brief record dict with "generated_at" as a Unix
    timestamp (int/float). now defaults to the current time.
    Returns None when generated_at is missing or not a number —
    a brief with no generation time must not be presented with
    a made-up age. Dashboard payloads carry both fields:
    generated_at (as stored) and age_seconds (this function).
    A brief older than 2 hours (7200 seconds) is stale; the
    caller, not this function, decides how to label it.
    """
    import time as _time
    generated_at = (record or {}).get("generated_at")
    if not isinstance(generated_at, (int, float)):
        return None
    current = now if now is not None else _time.time()
    return current - generated_at


def cap_snapshot_window(snapshot, max_messages=500, max_hours=24,
                        now=None):
    """BRF-023: cap a snapshot's source window.

    Default cap: last 500 messages or last 24 hours, whichever is
    smaller. Messages are kept in snapshot order; when the cap
    cuts, the oldest messages go first. Messages without a
    numeric ts are kept (they cannot be aged out by time, only
    by the message count cap). Returns a new snapshot dict with
    the capped messages and a "source_window" record naming the
    cap values actually applied: {"max_messages", "max_hours",
    "messages_kept", "messages_dropped"}. Jobs, presence, caps,
    and alerts pass through unchanged — the cap is a message
    window cap, not a job cap.
    """
    import time as _time
    snapshot = snapshot or {}
    messages = list(snapshot.get("messages") or [])
    current = now if now is not None else _time.time()
    dropped = 0
    if max_hours is not None:
        cutoff = current - max_hours * 3600
        timed = []
        untimed = []
        for message in messages:
            ts = message.get("ts") if isinstance(message, dict) else None
            if isinstance(ts, (int, float)):
                if ts >= cutoff:
                    timed.append(message)
            else:
                untimed.append(message)
        # Untimed messages cannot be aged out; they count toward
        # the message cap below, after timed ones in order is lost
        # only if the count cap cuts — keep original order by
        # re-filtering the original list instead.
        kept_by_time = set(id(m) for m in timed + untimed)
        # BRF-024: messages aged out by the time cap count as
        # dropped too. Before this, only the count cap was
        # counted, so a --since 2h brief over an old history
        # reported "0 dropped" while dropping most of it.
        dropped = len(messages) - len(
            [m for m in messages if id(m) in kept_by_time])
        messages = [m for m in messages if id(m) in kept_by_time]
    if max_messages is not None and len(messages) > max_messages:
        dropped += len(messages) - max_messages
        messages = messages[-max_messages:]
    # BRF-024: capping an already-capped snapshot must not reset
    # the drop count. The messages list here is already the
    # post-first-cap list, so drops from the earlier cap are
    # still dropped, and the total is the old count plus the
    # newly dropped ones. Without this, generate_brief's text
    # (capped a second time inside compose_brief) would report
    # 0 dropped while the record reported the true count.
    prior = snapshot.get("source_window")
    if isinstance(prior, dict):
        prior_dropped = prior.get("messages_dropped")
        if isinstance(prior_dropped, int):
            dropped += prior_dropped
    capped = dict(snapshot)
    capped["messages"] = messages
    capped["source_window"] = {
        "max_messages": max_messages,
        "max_hours": max_hours,
        "messages_kept": len(messages),
        "messages_dropped": dropped,
    }
    return capped


def redact_secrets(text):
    """BRF-014: strip credential-shaped strings from brief text.

    Replaces each match with "[redacted]" and leaves the rest of
    the text untouched. Patterns cover the shapes the crew actually
    handles: GitHub tokens, OpenAI-style sk- keys, AWS access key
    ids, Bearer tokens, and named key/token/secret/password
    assignments. Deliberately NOT included: plain hex strings, so
    commit hashes (40 hex chars, which briefs legitimately quote
    from DONE: lines) are never redacted away. No secret-pattern
    list exists in the jobs signing docs to reuse — the task text
    assumed one — so this list is defined here, in the open, and
    any new shape must be added here with a test, never silently.
    Redaction is the one exception to the verbatim blocked-reason
    rule: a secret in a blocked reason is redacted, not quoted.
    """
    if not text:
        return text
    patterns = [
        # GitHub tokens: ghp_, gho_, ghu_, ghs_, ghr_, github_pat_
        r"(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{20,}",
        r"github_pat_[A-Za-z0-9_]{20,}",
        # OpenAI-style keys
        r"sk-[A-Za-z0-9]{20,}",
        # AWS access key ids
        r"AKIA[0-9A-Z]{16}",
        # Bearer tokens
        r"Bearer\s+[A-Za-z0-9._\-]{10,}",
        # Named assignments: token=..., api_key: ..., secret "..."
        r"(?i)(api[_-]?key|access[_-]?token|secret|password)"
        r"(\s*[:=]\s*)([\"']?)[^\s\"']+\3",
    ]
    out = text
    for pattern in patterns:
        out = re.sub(pattern, "[redacted]", out)
    return out


def _format_brief_time(ts):
    """Format a stored brief timestamp as "YYYY-MM-DD HH:MM ET".

    Uses America/New_York, the same zone the BRF-011 morning
    schedule uses. Returns None for a non-numeric timestamp —
    a digest line must never carry a made-up time.
    """
    if isinstance(ts, bool) or not isinstance(ts, (int, float)):
        return None
    from datetime import datetime
    from zoneinfo import ZoneInfo
    return datetime.fromtimestamp(
        int(ts), tz=ZoneInfo("America/New_York")).strftime(
            "%Y-%m-%d %H:%M ET")


def build_previous_session(last_brief, jobs):
    """OS-051: derive a previous-session record from stored state.

    `last_brief` is a stored brief record (or brief index entry)
    from the store: its "generated_at" (or "ts") Unix timestamp
    becomes the last-brief time. `jobs` is the job list as it
    stood at shutdown: status "done" jobs are the jobs
    completed, status "open"/"claimed" jobs are the open
    threads — this repo has no separate thread store, so the
    job list is the thread list. Returns None when no usable
    last-brief time exists, so no digest is ever built on a
    guessed time. The returned dict is the "previous_session"
    record a boot snapshot carries.
    """
    if not isinstance(last_brief, dict):
        return None
    ts = last_brief.get("generated_at", last_brief.get("ts"))
    last_brief_at = _format_brief_time(ts)
    if last_brief_at is None:
        last_brief_at = last_brief.get("last_brief_at")
    if not isinstance(last_brief_at, str) or not last_brief_at:
        return None
    jobs = jobs or []
    completed = [job.get("title", "") for job in jobs
                 if isinstance(job, dict)
                 and job.get("status") == "done"
                 and job.get("title")]
    open_threads = [job.get("title", "") for job in jobs
                    if isinstance(job, dict)
                    and job.get("status") in ("open", "claimed")
                    and job.get("title")]
    return {"last_brief_at": last_brief_at,
            "jobs_completed": completed,
            "open_threads": open_threads}


def previous_session_digest(record):
    """OS-051: the one-line previous-session digest for a boot brief.

    `record` is a "previous_session" dict: "last_brief_at" (a
    string time), "jobs_completed" (job titles), "open_threads"
    (open thread titles). Returns a single line, never more:
    "Previous session: last brief <time>, N jobs completed
    (<titles>), M open threads (<titles>)", with the parenthesised
    titles dropped when a list is empty. Returns None when the
    record is missing or carries no last-brief time — a boot
    brief with no previous-session record says nothing about a
    previous session at all (OS-050 rule 3), it never invents
    one. The line is redacted by the composer, not here.
    """
    if not isinstance(record, dict):
        return None
    last_brief_at = record.get("last_brief_at")
    if not isinstance(last_brief_at, str) or not last_brief_at:
        return None
    completed = [title for title in (record.get("jobs_completed") or [])
                 if isinstance(title, str) and title]
    threads = [title for title in (record.get("open_threads") or [])
               if isinstance(title, str) and title]
    completed_part = f"{len(completed)} job{'s' if len(completed) != 1 else ''} completed"
    if completed:
        completed_part += " (" + "; ".join(completed) + ")"
    threads_part = f"{len(threads)} open thread{'s' if len(threads) != 1 else ''}"
    if threads:
        threads_part += " (" + "; ".join(threads) + ")"
    return (f"Previous session: last brief {last_brief_at}, "
            f"{completed_part}, {threads_part}")


def system_state_lines(state):
    """OS-062: the three drivers + tools + apps lines for a
    boot brief, in that order, one line each.

    `state` is the snapshot's "system_state" dict: "drivers"
    (agent driver names available on the machine),
    "gateway_healthy" (True when the MCP gateway answers,
    False when it is down, anything else when its health is
    not known), and "skill_apps" (skill app names mounted).
    The MCP gateway is the machine's tool service: the one
    local service every agent process reaches its tools
    through. A field that is missing is reported as not
    reported, never guessed; an empty list is reported as
    none, never padded with a name. A down gateway is
    reported as down, never omitted (OS-050 honesty rule):
    a reader must be able to tell a down gateway from a
    brief that simply forgot to mention it. The lines are
    redacted by the composer, not here, and they are not
    bullet lines, so the BRF-007 budget trim never drops
    them ahead of a watch item.
    """
    if not isinstance(state, dict):
        state = {}
    if "drivers" not in state:
        drivers_line = "Drivers: not reported in this snapshot"
    else:
        drivers = [name for name in (state.get("drivers") or [])
                   if isinstance(name, str) and name]
        if drivers:
            drivers_line = ("Drivers: " + ", ".join(drivers)
                            + " available")
        else:
            drivers_line = "Drivers: no drivers reported"
    gateway = state.get("gateway_healthy")
    if gateway is True:
        tools_line = "Tools: MCP gateway healthy"
    elif gateway is False:
        tools_line = ("Tools: MCP gateway down, so agents cannot "
                      "reach their tools through it")
    else:
        tools_line = ("Tools: MCP gateway health not reported "
                      "in this snapshot")
    if "skill_apps" not in state:
        apps_line = "Skill apps: not reported in this snapshot"
    else:
        apps = [name for name in (state.get("skill_apps") or [])
                if isinstance(name, str) and name]
        if apps:
            apps_line = "Skill apps: " + ", ".join(apps) + " mounted"
        else:
            apps_line = "Skill apps: no skill apps mounted"
    return [drivers_line, tools_line, apps_line]


def _environment_age_label(as_of):
    """OS-103: the age label for one environment line.

    `as_of` is a Unix timestamp for when the line's source
    was read. A numeric time formats as "(as of YYYY-MM-DD
    HH:MM ET)" through _format_brief_time; anything else
    yields "(snapshot time not reported)", so a field whose
    age is unknown is never silently presented as current.
    """
    formatted = _format_brief_time(as_of)
    if formatted:
        return f" (as of {formatted})"
    return " (snapshot time not reported)"


def environment_repo_record(repo_path=None, now=None):
    """OS-103 follow-up: the "repo" part of an environment record,
    read from a local git checkout at generation time.

    Returns {"branch", "commit", "dirty", "as_of"}: the current
    branch, the short commit, and the count of uncommitted
    files (porcelain lines, so untracked files count too),
    stamped with `now` or the current time. This is only the
    repo quarter of the environment record: a caller merges it
    with the bus, jobs, and budget parts from their own
    sources, and a record with only this part still renders
    the other three lines as not reported — a repo line alone
    never claims a bus, a queue, or a budget. Returns {}
    instead of raising when the path is not a git checkout,
    git is missing, a command fails, the HEAD is detached
    (no branch to name), or any output is unusable, so a
    repo the record does not describe renders as not
    reported by environment_lines, never guessed. `repo_path`
    defaults to this repo's root (the parent of intel/).
    """
    path = repo_path or os.path.dirname(os.path.dirname(
        os.path.abspath(__file__)))
    try:
        branch_proc = subprocess.run(
            ["git", "-C", path, "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True, text=True, timeout=10)
        commit_proc = subprocess.run(
            ["git", "-C", path, "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=10)
        status_proc = subprocess.run(
            ["git", "-C", path, "status", "--porcelain"],
            capture_output=True, text=True, timeout=10)
    except (OSError, ValueError, subprocess.TimeoutExpired):
        return {}
    if (branch_proc.returncode != 0 or commit_proc.returncode != 0
            or status_proc.returncode != 0):
        return {}
    branch = branch_proc.stdout.strip()
    commit = commit_proc.stdout.strip()
    if not branch or branch == "HEAD" or not commit:
        return {}
    dirty = len([line for line in status_proc.stdout.splitlines()
                 if line.strip()])
    return {"branch": branch, "commit": commit, "dirty": dirty,
            "as_of": int(time.time() if now is None else now)}


def environment_jobs_record(jobs):
    """OS-103 follow-up: the "jobs" part of an environment record,
    read from a stated jobs list at generation time.

    The caller passes the snapshot's own jobs list — the same
    list the brief composer already sees — and gets back the
    list to store as the environment record's "jobs" value, in
    job order. Only claimed jobs count as work in progress,
    exactly as environment_lines renders them: an entry counts
    only when its status is "claimed" and it carries a
    non-empty string claim nick and a non-empty string title;
    open, blocked, done, claim-less, title-less, and non-dict
    entries are skipped, never guessed into a name. The id is
    carried only when it is a non-empty string or an int, and
    is otherwise left out rather than invented. Returns None
    when `jobs` is not a list or tuple, so the caller leaves
    "jobs" out of the record and the Working now line reads
    not reported instead of falsely reading nobody holds a
    job; an empty list, or a list with no claimed usable job,
    returns [] and renders as nobody holds a claimed job.
    The list carries no time of its own: the Working now
    line's age label comes from the record's as_of, which
    the caller stamps when it merges this part in, at the
    same instant the jobs list was read. This is only the
    jobs quarter: a record carrying only this part still
    renders repo, bus, and budget as not reported. Never
    raises.
    """
    if not isinstance(jobs, (list, tuple)):
        return None
    claimed = []
    for job in jobs:
        try:
            if not isinstance(job, dict):
                continue
            if job.get("status") != "claimed":
                continue
            nick = job.get("claim")
            title = job.get("title")
            if not (isinstance(nick, str) and nick
                    and isinstance(title, str) and title):
                continue
            entry = {"title": title, "status": "claimed",
                     "claim": nick}
            job_id = job.get("id")
            if ((isinstance(job_id, str) and job_id)
                    or (isinstance(job_id, int)
                        and not isinstance(job_id, bool))):
                entry["id"] = job_id
            claimed.append(entry)
        except Exception:
            continue
    return claimed


def environment_bus_record(messages, rooms=None, now=None):
    """OS-103 follow-up: the "bus" part of an environment record,
    read from the snapshot's own messages list at generation
    time.

    The caller passes the snapshot's messages list — the
    same list the brief composer already sees — and the
    room or rooms that list covers, and gets back the dict
    to store as the environment record's "bus" value:
    "rooms" (non-empty strings, in caller order, duplicates
    dropped), "messages" (the count of usable entries),
    and "as_of" (the stamp passed as `now`, or the current
    time). Only dict and string entries count toward the
    total; other entries are skipped, never guessed into a
    message. The documented snapshot message shape carries
    no room field, so rooms come from the caller, never
    from the messages: a caller that states no room gets
    "rooms" as [], and the Bus line still carries the
    count, without a room claim. The count is the count of
    messages in the passed list — the snapshot window —
    never a claim about bus history beyond that window.
    Returns None when `messages` is not a list or tuple,
    so the caller leaves "bus" out of the record and the
    Bus line reads not reported instead of falsely reading
    zero messages; an empty list returns a record with
    "messages" 0, which renders as an empty window. This
    is only the bus quarter: a record carrying only this
    part still renders repo, jobs, and budget as not
    reported. Never raises.
    """
    if not isinstance(messages, (list, tuple)):
        return None
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    if isinstance(rooms, str):
        room_list = [rooms] if rooms else []
    elif isinstance(rooms, (list, tuple)):
        room_list = []
        for room in rooms:
            if isinstance(room, str) and room and room not in room_list:
                room_list.append(room)
    else:
        room_list = []
    count = 0
    for message in messages:
        try:
            if isinstance(message, (dict, str)):
                count += 1
        except Exception:
            continue
    return {"rooms": room_list, "messages": count, "as_of": stamp}


def environment_budget_record(budgets, lane=None, now=None):
    """OS-103 follow-up: the "budget" part of an environment record,
    read from a stated budgets list at generation time.

    The caller passes the snapshot's own budgets list — the
    same OS-079-shaped entries (lane, spent, cap, or
    remaining) the brief's spend-vs-budget lines already
    read — and gets back the dict to store as the
    environment record's "budget" value: "lane", the usable
    figures exactly as stated ("spent" and "cap" when both
    are usable, "remaining" when it is stated usable), and
    "as_of" (the stamp passed as `now`, or the current
    time). This reads stated figures, never a live ledger:
    there is still no spend ledger in this repo for a
    filler to read spent from, so a snapshot that carries
    no budgets list yields nothing here, and the Budget
    line reads not reported rather than a guessed figure.
    An entry counts only when it carries a non-empty
    string lane and usable figures: a usable "remaining"
    (an integer, never a bool), or a usable spent/cap
    pair (integers, never bools, cap positive, spent not
    negative, matching intel/budgets.py's malformed-entry
    rule — a lane with no usable cap is unbudgeted, not a
    zero budget, and a spent figure past cap is kept, an
    honest overspend, not a zero). When `lane` names a
    lane, only that lane's entries count, and the first
    usable one in list order wins; without a lane the
    first usable entry in list order wins, so a caller
    with several lanes states the lane it reports rather
    than taking whichever entry happens to come first.
    Returns None when `budgets` is not a list or tuple, or
    when no entry is usable, so the caller leaves
    "budget" out of the record and the Budget line reads
    not reported instead of falsely reading a zero
    remaining. This is only the budget quarter: a record
    carrying only this part still renders repo, bus, and
    Working now as not reported. Never raises.
    """
    if not isinstance(budgets, (list, tuple)):
        return None
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    wanted = lane if isinstance(lane, str) and lane else None
    for entry in budgets:
        try:
            if not isinstance(entry, dict):
                continue
            entry_lane = entry.get("lane")
            if not (isinstance(entry_lane, str) and entry_lane):
                continue
            if wanted is not None and entry_lane != wanted:
                continue
            spent = entry.get("spent")
            cap = entry.get("cap")
            remaining = entry.get("remaining")
            usable_int = (lambda value: isinstance(value, int)
                          and not isinstance(value, bool))
            record = {"lane": entry_lane, "as_of": stamp}
            if usable_int(spent) and spent >= 0 \
                    and usable_int(cap) and cap > 0:
                record["spent"] = spent
                record["cap"] = cap
            if usable_int(remaining):
                record["remaining"] = remaining
            if "spent" in record or "remaining" in record:
                return record
        except Exception:
            continue
    return None


def build_environment_record(snapshot=None, repo_path=None, now=None,
                             room=None, lane=None):
    """OS-103 follow-up: the caller that merges the built
    environment parts into one launch record.

    Before this change the repo and jobs builders existed
    but no caller in the repo combined them: a launch
    snapshot still had to hand-state its environment record.
    Now a caller passes the snapshot it already holds (or
    nothing, when it only wants the repo part) and gets
    back the record to store as the snapshot's
    "environment" value: "repo" from
    environment_repo_record over `repo_path` (this repo's
    checkout by default), "jobs" from
    environment_jobs_record over the snapshot's own jobs
    list, "bus" from environment_bus_record over the
    snapshot's own messages list and the `room` the
    snapshot covers (a string, or a list for a multi-room
    snapshot; omitted when the caller states no room, in
    which case the Bus line carries the count without a
    room claim), and "budget" from
    environment_budget_record over the snapshot's own
    budgets list and the `lane` the snapshot reports (a
    string naming the lane, or omitted to take the first
    usable entry), and one "as_of" stamp for the whole
    record, taken once so the repo, bus, and Working now
    lines' ages agree instead of drifting across reads.
    A part that yields nothing usable is left out, never
    padded: a non-checkout repo path leaves "repo" out, a
    snapshot with no usable jobs list leaves "jobs" out,
    a snapshot with no usable messages list leaves "bus"
    out, and a snapshot with no usable budgets entry
    leaves "budget" out, and environment_lines then renders that line as
    not reported instead of falsely reading nobody, zero
    messages, or a clean tree. An empty claimed-jobs list
    is kept as [], so it still renders as nobody holds a
    claimed job, and an empty messages list is kept as a
    bus record with 0 messages, so it still renders as an
    empty window. The budget part reads the snapshot's
    stated figures, never a live ledger: no spend ledger
    exists in this repo yet, so a snapshot carrying no
    budgets list still renders the Budget line as not
    reported. Never raises: a
    non-dict snapshot is treated as no snapshot, and the
    builders already never raise.
    """
    stamp = int(time.time() if now is None else now)
    record = {"as_of": stamp}
    repo = environment_repo_record(repo_path, now=stamp)
    if repo:
        record["repo"] = repo
    jobs = None
    messages = None
    budgets = None
    if isinstance(snapshot, dict):
        jobs = snapshot.get("jobs")
        messages = snapshot.get("messages")
        budgets = snapshot.get("budgets")
    jobs_part = environment_jobs_record(jobs)
    if jobs_part is not None:
        record["jobs"] = jobs_part
    bus_part = environment_bus_record(messages, rooms=room, now=stamp)
    if bus_part is not None:
        record["bus"] = bus_part
    budget_part = environment_budget_record(budgets, lane=lane,
                                            now=stamp)
    if budget_part is not None:
        record["budget"] = budget_part
    return record


def with_boot_environment(snapshot, room=None, repo_path=None,
                          now=None):
    """OS-103 follow-up: the launch-path caller that fills a
    boot snapshot's environment record.

    Before this change build_environment_record existed but
    no caller in the launch path used it: `intel.py brief
    --boot` — the path relay-brief.service runs — passed its
    snapshot straight to generate_brief, so a boot brief
    carried environment lines only when the snapshot
    hand-stated an "environment" record, and a bare launch
    snapshot carried none at all. Now the boot path calls
    this first: a snapshot that carries no "environment"
    key gets a copy with one built from itself — repo from
    the checkout at `repo_path` (this repo by default),
    jobs, bus, and budget from the snapshot's own lists,
    one as_of stamp — so the boot template brief carries
    all four lines, with any part that yields nothing
    usable rendered as not reported, never padded. A
    snapshot that already carries "environment" is
    returned as an unchanged copy: a hand-stated record
    wins over a built one, so a caller that knows its
    surroundings better than the builders is never
    overwritten. The caller's snapshot is never mutated,
    and this never raises: a builder failure leaves the
    copy without an environment record, so the boot path
    still produces a brief, just without environment
    lines, instead of failing the launch brief outright.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "environment" in filled:
        return filled
    try:
        filled["environment"] = build_environment_record(
            snapshot if isinstance(snapshot, dict) else None,
            repo_path=repo_path, now=now, room=room)
    except Exception:
        pass
    return filled


def with_memory_budget(snapshot, now=None):
    """OS-079 follow-up: the brief-path caller that fills a
    snapshot's memory_budget record.

    Before this change no caller in the repo filled
    `memory_budget`: a brief carried its settled-decisions
    and spend-vs-budget lines only when the snapshot
    hand-stated a "memory_budget" record, and a snapshot
    that only carried the raw lists carried none of the
    lines at all. Now the brief path calls this first: a
    snapshot that carries no "memory_budget" key gets a
    copy with one built from itself — "budgets" from the
    snapshot's own budgets list (every usable lane, in
    list order, not just one lane the way the OS-103
    environment budget part reads), "settled_decisions"
    from the snapshot's own settled_decisions list when
    the caller states one, and "memory_down" when the
    snapshot states the memory service did not answer —
    with one as_of stamp for the whole record, so the
    lines' ages agree instead of drifting across reads.
    A snapshot that already carries "memory_budget" is
    returned as an unchanged copy: a hand-stated record
    wins over a built one, so a caller that knows its
    memory and budgets better than these lists is never
    overwritten. This still reads stated figures, never
    a live service: there is no memory service in this
    repo for a filler to read settled decisions from,
    and no spend ledger for it to read spent from, so a
    snapshot that states no settled decisions leaves
    that key out and the line reads not reported rather
    than a guessed decision, and a snapshot that states
    no usable budget entry leaves "budgets" out. Unlike
    with_boot_environment, a snapshot that yields
    nothing usable at all gets no record added: the
    OS-079 rule is that a snapshot with no memory_budget
    record carries none of the lines, so older briefs
    keep their exact shape instead of gaining
    not-reported lines. A budget entry counts only
    when it carries a non-empty string lane and usable
    figures — spent and cap (integers, never bools,
    cap positive, spent not negative, overspend kept
    honest), remaining and cap, or remaining alone —
    matching the environment budget record's rule; a
    held flag on a stated entry passes through, so an
    at-cap lane still shows its hold in the spend line.
    The caller's snapshot is never mutated, and this
    never raises: a builder failure leaves the copy
    without a memory_budget record, so the brief path
    still produces a brief, just without these lines,
    instead of failing outright.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "memory_budget" in filled:
        return filled
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    record = {"as_of": stamp}
    added = False
    try:
        if isinstance(snapshot, dict):
            if snapshot.get("memory_down") is True:
                record["memory_down"] = True
                added = True
            decisions = snapshot.get("settled_decisions")
            if isinstance(decisions, list):
                record["settled_decisions"] = [
                    decision for decision in decisions
                    if isinstance(decision, str) and decision]
                added = True
            budgets = snapshot.get("budgets")
            if isinstance(budgets, (list, tuple)):
                usable = []
                for entry in budgets:
                    if not isinstance(entry, dict):
                        continue
                    lane = entry.get("lane")
                    if not (isinstance(lane, str) and lane):
                        continue
                    spent = entry.get("spent")
                    cap = entry.get("cap")
                    remaining = entry.get("remaining")
                    usable_int = (lambda value: isinstance(value, int)
                                  and not isinstance(value, bool))
                    built = None
                    if (usable_int(spent) and spent >= 0
                            and usable_int(cap) and cap > 0):
                        built = {"lane": lane, "spent": spent,
                                 "cap": cap}
                    elif (usable_int(remaining) and remaining >= 0
                            and usable_int(cap) and cap > 0):
                        built = {"lane": lane, "remaining": remaining,
                                 "cap": cap}
                    elif usable_int(remaining) and remaining >= 0:
                        built = {"lane": lane,
                                 "remaining": remaining}
                    if built is None:
                        continue
                    if entry.get("held") is True:
                        built["held"] = True
                    usable.append(built)
                if usable:
                    record["budgets"] = usable
                    added = True
    except Exception:
        return filled
    if added:
        filled["memory_budget"] = record
    return filled


def with_daily(snapshot, now=None):
    """OS-075 follow-up: the morning-path caller that fills a
    snapshot's daily record.

    Before this change no caller in the repo filled
    `daily`: a morning brief carried its Daily brief
    section only when the snapshot hand-stated a "daily"
    record, and a snapshot that only carried the raw
    lists carried no section at all. Now the morning
    path calls this first: a snapshot that carries no
    "daily" key gets a copy with one built from itself
    — "overnight_results" from the snapshot's own
    stated overnight_results list (verbatim non-empty
    strings, in list order), "todays_queue" from the
    snapshot's own jobs list (open or claimed jobs
    with both an id and a title, in job order, each
    job listed once — a job named twice is one queue
    item, not two), and "needs_word" from the
    snapshot's own stated needs_word list (verbatim
    questions, strings or question-plus-job dicts) —
    with one as_of stamp for the whole record, so the
    section's ages agree instead of drifting across
    reads. A snapshot that already carries "daily" is
    returned as an unchanged copy: a hand-stated record
    wins over a built one, so a caller that knows
    Dale's day better than these lists is never
    overwritten. The two stated lists are passed
    through, never re-derived: overnight results are
    NOT pulled out of DONE markers and needs-word
    questions are NOT invented from blocked reasons —
    a blocked job's reason is a reason, not a
    question waiting on Dale's word, so a snapshot
    that states no needs_word list leaves that key
    out and the line reads none reported rather than
    a guessed question. A category with no usable
    entry leaves its key out, and daily_lines then
    renders that category as none reported, so a
    built record always reads as a checked section,
    never a padded one. Unlike with_boot_environment,
    a snapshot that yields nothing usable at all gets
    no record added: the OS-075 rule is that a
    snapshot with no daily record carries no section,
    so older briefs keep their exact shape instead of
    gaining none-reported lines. The caller's snapshot
    is never mutated, and this never raises: a builder
    failure leaves the copy without a daily record, so
    the brief path still produces a brief, just without
    this section, instead of failing outright.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "daily" in filled:
        return filled
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    record = {"as_of": stamp}
    added = False
    try:
        if isinstance(snapshot, dict):
            results = snapshot.get("overnight_results")
            if isinstance(results, list):
                usable_results = [item for item in results
                                  if isinstance(item, str) and item]
                if usable_results:
                    record["overnight_results"] = usable_results
                    added = True
            jobs = snapshot.get("jobs")
            if isinstance(jobs, list):
                usable_queue = []
                seen_ids = set()
                for job in jobs:
                    if not isinstance(job, dict):
                        continue
                    if job.get("status") not in ("open", "claimed"):
                        continue
                    job_id = job.get("id")
                    title = job.get("title")
                    if not (isinstance(job_id, str) and job_id):
                        continue
                    if not (isinstance(title, str) and title):
                        continue
                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)
                    usable_queue.append({"id": job_id,
                                         "title": title})
                if usable_queue:
                    record["todays_queue"] = usable_queue
                    added = True
            needs = snapshot.get("needs_word")
            if isinstance(needs, list):
                usable_needs = []
                for entry in needs:
                    if isinstance(entry, str) and entry:
                        usable_needs.append(entry)
                    elif isinstance(entry, dict):
                        question = entry.get("question")
                        if not (isinstance(question, str)
                                and question):
                            continue
                        built = {"question": question}
                        job_id = entry.get("job")
                        if isinstance(job_id, str) and job_id:
                            built["job"] = job_id
                        usable_needs.append(built)
                if usable_needs:
                    record["needs_word"] = usable_needs
                    added = True
    except Exception:
        return filled
    if added:
        filled["daily"] = record
    return filled


def with_memory_depth(snapshot, now=None):
    """OS-092 follow-up: the morning-path caller that fills a
    snapshot's memory_depth record.

    Before this change no caller in the repo filled
    `memory_depth`: a morning brief carried its
    Long-term memory section only when the snapshot
    hand-stated a "memory_depth" record, and a snapshot
    that only carried the raw lists carried no section
    at all. Now the morning path calls this first: a
    snapshot that carries no "memory_depth" key gets a
    copy with one built from itself — "aged_decisions"
    from the snapshot's own stated aged_decisions list
    (each a dict with a non-empty decision string, its
    original_date kept only when it is a non-empty
    string, so a dateless decision renders original
    date not reported instead of a guessed date),
    "due_commitments" from the snapshot's own stated
    due_commitments list (each a dict with a non-empty
    commitment string, its due date kept only when it
    is a non-empty string), and "fresh_context" from
    the snapshot's own stated fresh_context list
    (verbatim non-empty strings, in list order) — with
    one as_of stamp for the whole record, so the
    section's ages agree instead of drifting across
    reads. A snapshot that already carries
    "memory_depth" is returned as an unchanged copy: a
    hand-stated record wins over a built one, so a
    caller that knows its memory better than these
    lists is never overwritten. This still reads
    stated lists, never a live service: there is no
    memory service in this repo for a filler to read
    aged decisions or due commitments from, so a
    snapshot that states no usable entry leaves that
    key out. When the snapshot states the memory
    service did not answer ("memory_down" True), the
    record carries that flag alone: the renderer shows
    no item beside the down line under the OS-050
    honesty rule, so stated lists are not carried
    into a record whose lines would never show them.
    Unlike a hand-stated empty record, a snapshot that
    yields nothing usable at all gets no record added:
    the OS-092 rule is that a snapshot with no
    memory_depth record carries no section, so older
    briefs keep their exact shape instead of gaining
    none-reported lines. The caller's snapshot is never
    mutated, and this never raises: a builder failure
    leaves the copy without a memory_depth record, so
    the brief path still produces a brief, just without
    this section, instead of failing outright.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "memory_depth" in filled:
        return filled
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    record = {"as_of": stamp}
    added = False
    try:
        if isinstance(snapshot, dict):
            if snapshot.get("memory_down") is True:
                record["memory_down"] = True
                added = True
            else:
                aged = snapshot.get("aged_decisions")
                if isinstance(aged, list):
                    usable_aged = []
                    for entry in aged:
                        if not isinstance(entry, dict):
                            continue
                        decision = entry.get("decision")
                        if not (isinstance(decision, str)
                                and decision):
                            continue
                        built = {"decision": decision}
                        date = entry.get("original_date")
                        if isinstance(date, str) and date:
                            built["original_date"] = date
                        usable_aged.append(built)
                    if usable_aged:
                        record["aged_decisions"] = usable_aged
                        added = True
                due = snapshot.get("due_commitments")
                if isinstance(due, list):
                    usable_due = []
                    for entry in due:
                        if not isinstance(entry, dict):
                            continue
                        commitment = entry.get("commitment")
                        if not (isinstance(commitment, str)
                                and commitment):
                            continue
                        built = {"commitment": commitment}
                        due_date = entry.get("due")
                        if isinstance(due_date, str) and due_date:
                            built["due"] = due_date
                        usable_due.append(built)
                    if usable_due:
                        record["due_commitments"] = usable_due
                        added = True
                context = snapshot.get("fresh_context")
                if isinstance(context, list):
                    usable_context = [item for item in context
                                      if isinstance(item, str)
                                      and item]
                    if usable_context:
                        record["fresh_context"] = usable_context
                        added = True
    except Exception:
        return filled
    if added:
        filled["memory_depth"] = record
    return filled


def with_previous_session(snapshot):
    """OS-051 follow-up: the boot-path caller that fills a
    boot snapshot's previous_session record.

    Before this change no caller in the repo filled
    `previous_session`: a boot brief carried its digest
    line only when the snapshot hand-stated a
    "previous_session" record, and a bare boot snapshot
    carried no digest at all even when the caller knew
    the previous session. Now the boot path calls this
    first: a snapshot that carries no "previous_session"
    key gets a copy with one built by
    build_previous_session from the snapshot's own stated
    inputs — "last_brief", the stored brief record (its
    generated_at, ts, or last_brief_at time becomes the
    last-brief time), and "shutdown_jobs", the job list
    as it stood at shutdown (done jobs are the jobs
    completed, open or claimed jobs are the open
    threads, blocked jobs are neither). A snapshot that
    already carries "previous_session" is returned as
    an unchanged copy: a hand-stated record wins over a
    built one, so a caller that knows its previous
    session better than these inputs is never
    overwritten. Two inputs are deliberately NOT used
    here, and a reader must not confuse them with the
    filler's inputs: the snapshot's current "jobs" list
    is the window's jobs at boot, not the shutdown
    list, so it is never read as the previous session;
    and the snapshot's "previous_brief" record is the
    BRF-019 diff record (job ids with their previous
    statuses), not a stored brief, so it carries no
    last-brief time for the builder to use. A
    shutdown_jobs list that is explicitly empty states
    a clean shutdown and yields a 0-jobs-completed,
    0-open-threads record; a missing or non-list
    shutdown_jobs states nothing about shutdown and
    yields no record at all, so a brief never claims a
    clean shutdown on silence. Likewise a last_brief
    that yields no usable time yields no record, by
    build_previous_session's own rule: the digest is
    never built on a guessed time. The record carries
    no as_of stamp of its own — its time is the
    last-brief time itself — so unlike the other
    with_* callers this one takes no now argument.
    The caller's snapshot is never mutated, and this
    never raises: a builder failure leaves the copy
    without a previous_session record, so the boot
    path still produces a brief, just without the
    digest line, instead of failing the launch brief
    outright. This still reads stated inputs, never a
    live store: the brief store is not consulted for
    the last brief here, so a caller that states no
    last_brief gets no digest even when an earlier
    brief sits in the store.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "previous_session" in filled:
        return filled
    try:
        if not isinstance(snapshot, dict):
            return filled
        shutdown_jobs = snapshot.get("shutdown_jobs")
        if not isinstance(shutdown_jobs, list):
            return filled
        record = build_previous_session(
            snapshot.get("last_brief"), shutdown_jobs)
    except Exception:
        return filled
    if record is not None:
        filled["previous_session"] = record
    return filled


def with_federation(snapshot, now=None):
    """OS-117 follow-up: the morning-path caller that fills a
    snapshot's federation record.

    Before this change no caller in the repo filled
    `federation`: a morning brief carried its Federation
    section only when the snapshot hand-stated a
    "federation" record, and a snapshot that only
    carried the joined machines carried no section at
    all. Now the morning path calls this first: a
    snapshot that carries no "federation" key gets a
    copy with one built from itself — "machines" from
    the snapshot's own stated joined_machines list
    (each machine's name, its crew's completions
    verbatim, and its cross-machine jobs with id,
    title, and status when stated), and "trust_events"
    from the snapshot's own stated trust_events list
    (joins and refusals with their machine and detail)
    — with one as_of stamp for the whole record, so
    the section's ages agree instead of drifting
    across reads. A snapshot that already carries
    "federation" is returned as an unchanged copy: a
    hand-stated record wins over a built one, so a
    caller that knows its federation better than
    these lists is never overwritten. The section
    exists only for a real crew of crews, so a
    snapshot yielding fewer than two usable machines
    gets no record at all: a single-machine record
    would render no section anyway, and trust events
    without two machines are not a federation
    section, so older briefs keep their exact shape
    instead of gaining a silent record. A machine
    named twice is one machine, not two: the first
    entry wins. A machine without a name, a
    cross-machine job without an id and a title, a
    trust event without a machine name, and a trust
    event of any kind but join or refusal are
    skipped, never guessed — a machine with no
    completions still counts, and reads "no
    completions reported" from the renderer, never a
    padded title. The caller's snapshot is never
    mutated, and this never raises: a builder failure
    leaves the copy without a federation record, so
    the morning path still produces a brief, just
    without this section, instead of failing
    outright. This still reads stated inputs, never
    a live federation: the join flow, trust
    enforcement, two-machine drill, and policy
    ruling have not landed, so a caller that states
    no joined machines gets no section even when
    other machines exist somewhere else.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "federation" in filled:
        return filled
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    record = {"as_of": stamp}
    try:
        if not isinstance(snapshot, dict):
            return filled
        machines = snapshot.get("joined_machines")
        usable_machines = []
        if isinstance(machines, list):
            seen_names = set()
            for machine in machines:
                if not isinstance(machine, dict):
                    continue
                name = machine.get("name")
                if not (isinstance(name, str) and name):
                    continue
                if name in seen_names:
                    continue
                seen_names.add(name)
                built = {"name": name}
                completions = machine.get("completions")
                if isinstance(completions, list):
                    usable_titles = [
                        title for title in completions
                        if isinstance(title, str) and title]
                    if usable_titles:
                        built["completions"] = usable_titles
                cross = machine.get("cross_machine_jobs")
                if isinstance(cross, list):
                    usable_cross = []
                    for job in cross:
                        if not isinstance(job, dict):
                            continue
                        job_id = job.get("id")
                        title = job.get("title")
                        if not (isinstance(job_id, str)
                                and job_id):
                            continue
                        if not (isinstance(title, str)
                                and title):
                            continue
                        built_job = {"id": job_id,
                                     "title": title}
                        status = job.get("status")
                        if isinstance(status, str) and status:
                            built_job["status"] = status
                        usable_cross.append(built_job)
                    if usable_cross:
                        built["cross_machine_jobs"] = usable_cross
                usable_machines.append(built)
        if len(usable_machines) < 2:
            return filled
        record["machines"] = usable_machines
        events = snapshot.get("trust_events")
        if isinstance(events, list):
            usable_events = []
            for event in events:
                if not isinstance(event, dict):
                    continue
                kind = event.get("kind")
                if kind not in ("join", "refusal"):
                    continue
                machine = event.get("machine")
                if not (isinstance(machine, str) and machine):
                    continue
                built_event = {"kind": kind,
                               "machine": machine}
                detail = event.get("detail")
                if isinstance(detail, str) and detail:
                    built_event["detail"] = detail
                usable_events.append(built_event)
            if usable_events:
                record["trust_events"] = usable_events
    except Exception:
        return filled
    filled["federation"] = record
    return filled


def with_priority_order(snapshot, now=None):
    """INT-027 follow-up: the morning-path caller that fills a
    snapshot's priority_order record.

    Before this change no caller in the repo filled
    `priority_order`: a morning brief carried its Priority
    order section only when the snapshot hand-stated a
    "priority_order" record, and a snapshot that only
    carried the order as a plain list of job ids carried
    no section at all. Now the morning path calls this
    first: a snapshot that carries no "priority_order"
    key gets a copy with one built from itself — "order"
    from the snapshot's own stated priority_ids list, in
    stated order — with one as_of stamp for the whole
    record, so the section's age agrees with the other
    sections instead of drifting across reads. A snapshot
    that already carries "priority_order" is returned as
    an unchanged copy: a hand-stated record wins over a
    built one, so a caller that knows its order better
    than this list is never overwritten. The record
    exists only when the snapshot states at least one
    usable id, so a snapshot that states nothing usable
    gets no record at all, and older briefs keep their
    exact shape instead of gaining a padded section. A
    job id named twice is one entry, not two: the first
    listing wins, in stated order. An id that is not a
    non-empty string is skipped, never guessed — and a
    list of only skipped ids counts as nothing stated,
    so junk alone never builds a record. The caller
    does not filter ids against the snapshot's jobs
    list: the renderer already skips an id with no
    matching job, and a caller that dropped such ids
    would silently rewrite the stated order instead of
    letting the section read none reported for it. The
    caller's snapshot is never mutated, and this never
    raises: a builder failure leaves the copy without a
    priority_order record, so the brief path still
    produces a brief, just without this section,
    instead of failing outright. This still reads a
    stated order, never a guessed one: there is no
    priority field on a job in this repo for a filler
    to derive an order from, so a snapshot that states
    no priority_ids gets no section even when its jobs
    list has an obvious order to a reader.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "priority_order" in filled:
        return filled
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    record = {"as_of": stamp}
    try:
        if not isinstance(snapshot, dict):
            return filled
        stated = snapshot.get("priority_ids")
        if not isinstance(stated, list):
            return filled
        seen = set()
        usable = []
        for job_id in stated:
            if not (isinstance(job_id, str) and job_id):
                continue
            if job_id in seen:
                continue
            seen.add(job_id)
            usable.append(job_id)
        if not usable:
            return filled
        record["order"] = usable
    except Exception:
        return filled
    filled["priority_order"] = record
    return filled


def with_blocked_contacts(snapshot, now=None):
    """INT-027 follow-up: the morning-path caller that fills a
    snapshot's blocked_contacts record.

    Before this change no caller in the repo filled
    `blocked_contacts`: a morning brief carried its Blocked
    contacts section only when the snapshot hand-stated a
    "blocked_contacts" record, and a snapshot that only
    carried the ask nicks as a plain stated list carried
    no section at all. Now the morning path calls this
    first: a snapshot that carries no "blocked_contacts"
    key gets a copy with one built from itself —
    "contacts" from the snapshot's own stated
    blocked_contact_entries list, each entry a job_id
    with an optional ask nick — with one as_of stamp
    for the whole record, so the section's age agrees
    with the other sections instead of drifting across
    reads. A snapshot that already carries
    "blocked_contacts" is returned as an unchanged
    copy: a hand-stated record wins over a built one,
    so a caller that knows its contacts better than
    this list is never overwritten. The record exists
    only when the snapshot states at least one usable
    job_id, so a snapshot that states nothing usable
    gets no record at all, and older briefs keep their
    exact shape instead of gaining a padded section.
    This filler reads no nick from the jobs list, and
    that is the whole point: a blocked job carries no
    owner field to read one from — jobs.py cmd_blocked
    deletes the claim, claim host, claimed_at, and
    lease when it marks a job blocked, so the jobs
    list cannot name anyone to ask, and a filler that
    derived a nick from a title, a note, or a stale
    claim would be guessing. The ask nick comes only
    from the caller's stated entries, never from the
    job. A job_id named twice is one entry, not two:
    the first listing wins, in stated order. An entry
    with no usable job_id is skipped, never guessed,
    and a list of only skipped entries counts as
    nothing stated, so junk alone never builds a
    record. An entry that states a job_id but no
    usable ask nick is still a usable entry: the
    renderer reads that job as owner not reported in
    this window, which is the stated absence, not a
    guessed nick. The caller does not filter entries
    against the snapshot's jobs list: the renderer
    already ignores a contact for a job that is not
    blocked in this snapshot, and a caller that
    dropped such entries would silently rewrite the
    stated contacts instead of letting the section
    read what the window actually holds. The caller's
    snapshot is never mutated, and this never raises:
    a builder failure leaves the copy without a
    blocked_contacts record, so the brief path still
    produces a brief, just without this section,
    instead of failing outright. This closes gap 5
    for the template brief only, and it does so
    additively: the Blocked and why lines it leaves
    alone keep their verbatim pinned shape.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "blocked_contacts" in filled:
        return filled
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    record = {"as_of": stamp}
    try:
        if not isinstance(snapshot, dict):
            return filled
        stated = snapshot.get("blocked_contact_entries")
        if not isinstance(stated, list):
            return filled
        seen = set()
        usable = []
        for entry in stated:
            if not isinstance(entry, dict):
                continue
            job_id = entry.get("job_id")
            if not (isinstance(job_id, str) and job_id):
                continue
            if job_id in seen:
                continue
            seen.add(job_id)
            ask = entry.get("ask")
            if isinstance(ask, str) and ask:
                usable.append({"job_id": job_id, "ask": ask})
            else:
                usable.append({"job_id": job_id})
        if not usable:
            return filled
        record["contacts"] = usable
    except Exception:
        return filled
    filled["blocked_contacts"] = record
    return filled


def with_held_decisions(snapshot, now=None):
    """INT-027 follow-up: the morning-path caller that fills a
    snapshot's held_decisions record.

    Before this change no caller in the repo filled
    `held_decisions`: a morning brief carried its Held
    decisions section only when the snapshot hand-stated a
    "held_decisions" record, and a snapshot that only
    carried the waiting questions as a plain stated list
    carried no section at all. Now the morning path calls
    this first: a snapshot that carries no "held_decisions"
    key gets a copy with one built from itself —
    "decisions" from the snapshot's own stated
    held_decision_entries list, each entry a question
    string with an optional decider nick — with one as_of
    stamp for the whole record, so the section's age
    agrees with the other sections instead of drifting
    across reads. A snapshot that already carries
    "held_decisions" is returned as an unchanged copy: a
    hand-stated record wins over a built one, so a caller
    that knows its held list better than this list is
    never overwritten. The record exists only when the
    snapshot states at least one usable question, so a
    snapshot that states nothing usable gets no record at
    all, and older briefs keep their exact shape instead
    of gaining a padded section. This filler reads no
    question from the jobs list, and that is the whole
    point: a blocked reason or a job title is not a
    question waiting on Dale's word, and a filler that
    derived a held question from either would be
    guessing. The question comes only from the caller's
    stated entries, never from the job. A question named
    twice is one decision, not two: the first listing
    wins, in stated order. An entry with no usable
    question is skipped, never guessed, and a list of
    only skipped entries counts as nothing stated, so
    junk alone never builds a record. An entry that
    states a question but no usable decider nick is
    still a usable entry: the renderer reads that
    decision as decider not reported, which is the
    stated absence, not a guessed nick. The caller's
    snapshot is never mutated, and this never raises:
    a builder failure leaves the copy without a
    held_decisions record, so the brief path still
    produces a brief, just without this section,
    instead of failing outright. This closes gap 3
    for the template brief only, and it does so
    additively: the Watch items and Federation lines it
    leaves alone keep their pinned shape, and the
    Sources section needs no filler of its own — the
    renderer already reads the snapshot's plain
    source_pointers list directly, so a snapshot that
    states pointers already carries that section.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "held_decisions" in filled:
        return filled
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    record = {"as_of": stamp}
    try:
        if not isinstance(snapshot, dict):
            return filled
        stated = snapshot.get("held_decision_entries")
        if not isinstance(stated, list):
            return filled
        seen = set()
        usable = []
        for entry in stated:
            if not isinstance(entry, dict):
                continue
            question = entry.get("question")
            if not (isinstance(question, str) and question):
                continue
            if question in seen:
                continue
            seen.add(question)
            decider = entry.get("decider")
            if isinstance(decider, str) and decider:
                usable.append({"question": question,
                               "decider": decider})
            else:
                usable.append({"question": question})
        if not usable:
            return filled
        record["decisions"] = usable
    except Exception:
        return filled
    filled["held_decisions"] = record
    return filled


def with_previous_brief(snapshot, now=None):
    """BRF-019 follow-up: the morning-path caller that fills a
    snapshot's previous_brief record.

    Before this change no caller in the repo filled
    `previous_brief`: a morning brief carried its Since
    your last brief section only when the snapshot
    hand-stated a "previous_brief" record, and a snapshot
    that only carried the previous brief's job statuses
    as a plain stated list carried no section at all.
    Now the morning path calls this first: a snapshot
    that carries no "previous_brief" key gets a copy
    with one built from itself — "jobs" from the
    snapshot's own stated previous_brief_entries list,
    each entry a job id with the status that job carried
    in the previous brief — with one as_of stamp for the
    whole record, so the section's age agrees with the
    other sections instead of drifting across reads. A
    snapshot that already carries "previous_brief" is
    returned as an unchanged copy: a hand-stated record
    wins over a built one, so a caller that knows its
    previous brief better than this list is never
    overwritten. The record exists only when the snapshot
    states at least one usable job id, so a snapshot that
    states nothing usable gets no record at all, and older
    briefs keep their exact shape instead of gaining a
    padded section. This filler reads no previous status
    from the current jobs list, and that is the whole
    point: comparing the current window against itself
    would report nothing changed, always, and a current
    status is not a previous status. The previous statuses
    come only from the caller's stated entries, never
    from the job. A job id named twice is one previous
    entry, not two: the first listing wins, in stated
    order. An entry with no usable id is skipped, never
    guessed, and a list of only skipped entries counts
    as nothing stated, so junk alone never builds a
    record. An entry that states an id but no usable
    status is still a usable entry: the renderer reads
    that previous status as empty, which is the stated
    absence, not a guessed status. The caller's snapshot
    is never mutated, and this never raises: a builder
    failure leaves the copy without a previous_brief
    record, so the brief path still produces a brief,
    just without this section, instead of failing
    outright. This closes gap 2 for the template brief
    only, and it does so additively: the sections it
    leaves alone keep their pinned shape, and a brief
    without the record still says nothing about
    newness rather than claiming it.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "previous_brief" in filled:
        return filled
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    record = {"as_of": stamp}
    try:
        if not isinstance(snapshot, dict):
            return filled
        stated = snapshot.get("previous_brief_entries")
        if not isinstance(stated, list):
            return filled
        seen = set()
        usable = []
        for entry in stated:
            if not isinstance(entry, dict):
                continue
            job_id = entry.get("id")
            if not (isinstance(job_id, str) and job_id):
                continue
            if job_id in seen:
                continue
            seen.add(job_id)
            status = entry.get("status")
            if isinstance(status, str) and status:
                usable.append({"id": job_id, "status": status})
            else:
                usable.append({"id": job_id})
        if not usable:
            return filled
        record["jobs"] = usable
    except Exception:
        return filled
    filled["previous_brief"] = record
    return filled


def with_recovery(snapshot, now=None):
    """OS-127 follow-up: the boot-path caller that fills a
    snapshot's recovery record.

    Before this change no caller in the repo filled
    `recovery`: a boot brief carried its one
    in-flight-jobs-recovered line only when the
    snapshot hand-stated a "recovery" record, and a
    boot snapshot that only carried the lease sweep's
    own stated outcome carried no line at all. Now
    the boot path calls this first: a snapshot that
    carries no "recovery" key gets a copy with one
    built from itself — "recovered" from the
    snapshot's own stated sweep_recovered list (each
    job's id, title, and baton step when stated),
    "sweep_count" from the snapshot's own stated
    sweep_count, and "corrupted" from the snapshot's
    own stated sweep_corrupted list — with one as_of
    stamp for the whole record, so the line's age
    agrees with the other boot lines instead of
    drifting across reads. A snapshot that already
    carries "recovery" is returned as an unchanged
    copy: a hand-stated record wins over a built one,
    so a caller that knows its recovery better than
    these lists is never overwritten. The record
    exists only for a sweep that actually reported
    something, so a snapshot that states no usable
    sweep outcome — no recovered jobs, no sweep
    count, no corrupted jobs — gets no record at
    all, and older briefs keep their exact shape
    instead of gaining a silent line. A clean
    shutdown is a stated sweep count of zero with no
    recovered jobs: that builds a record, and it
    reads "0 recovered" plainly, because the sweep
    itself said so — a snapshot with no sweep count
    at all never reads zero. A job listed twice is
    one recovery, not two: the first entry wins, in
    sweep order. A recovered job without an id and a
    title, and a sweep count that is not a
    non-negative int, are skipped, never guessed —
    and a skipped recovered entry never turns into a
    clean count, because the record then carries no
    sweep count to reconcile against. A recovered job
    with no baton step is named with no step, never
    with an invented step: the renderer reads "step
    not reported" for it. The caller's snapshot is
    never mutated, and this never raises: a builder
    failure leaves the copy without a recovery
    record, so the boot path still produces a brief,
    just without this line, instead of failing
    outright. This still reads stated inputs, never
    a live lease sweep: the OS-126 plug-pull drill
    and the sweep verification have not landed, so
    a caller that states no sweep outcome gets no
    line even when a sweep ran somewhere else.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "recovery" in filled:
        return filled
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    record = {"as_of": stamp}
    try:
        if not isinstance(snapshot, dict):
            return filled
        usable = False
        skipped = False
        recovered = snapshot.get("sweep_recovered")
        if isinstance(recovered, list) and recovered:
            seen_ids = set()
            usable_jobs = []
            for job in recovered:
                if not isinstance(job, dict):
                    skipped = True
                    continue
                job_id = job.get("id")
                title = job.get("title")
                if not (isinstance(job_id, str) and job_id):
                    skipped = True
                    continue
                if not (isinstance(title, str) and title):
                    skipped = True
                    continue
                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)
                built_job = {"id": job_id, "title": title}
                step = job.get("baton_step")
                if isinstance(step, int) and not isinstance(step, bool):
                    built_job["baton_step"] = step
                elif isinstance(step, str) and step:
                    built_job["baton_step"] = step
                usable_jobs.append(built_job)
            if usable_jobs:
                record["recovered"] = usable_jobs
                usable = True
            elif skipped:
                # A stated job that could not be read is
                # still a sweep outcome, but it must never
                # reconcile into a clean count: the record
                # carries the jobs it could read and no
                # sweep count, so the renderer says the
                # recovery is incomplete instead of
                # printing a tidy number over a gap.
                record["recovered"] = []
                usable = True
        sweep = snapshot.get("sweep_count")
        if (isinstance(sweep, int) and not isinstance(sweep, bool)
                and sweep >= 0):
            if "recovered" not in record:
                record["recovered"] = []
            # A skipped recovered entry voids the count:
            # without it the renderer cannot print a
            # clean count, only an incomplete line. A
            # job listed twice is not a skip: dedupe
            # never voids a count on its own.
            if not skipped:
                record["sweep_count"] = sweep
            usable = True
        corrupted = snapshot.get("sweep_corrupted")
        if isinstance(corrupted, list) and corrupted:
            usable_corrupted = []
            for job in corrupted:
                if isinstance(job, dict):
                    job_id = job.get("id")
                    title = job.get("title")
                    if isinstance(job_id, str) and job_id:
                        if isinstance(title, str) and title:
                            usable_corrupted.append(
                                {"id": job_id, "title": title})
                        else:
                            usable_corrupted.append(
                                {"id": job_id})
                    elif isinstance(title, str) and title:
                        usable_corrupted.append({"title": title})
                elif isinstance(job, str) and job:
                    usable_corrupted.append(job)
            if usable_corrupted:
                record["corrupted"] = usable_corrupted
                usable = True
        if not usable:
            return filled
    except Exception:
        return filled
    filled["recovery"] = record
    return filled


def with_system_state(snapshot, now=None):
    """OS-062 follow-up: the boot-path caller that fills a
    snapshot's system_state record.

    Before this change no caller in the repo filled
    `system_state`: a boot brief carried its three
    drivers + tools + apps lines with values only when
    the snapshot hand-stated a "system_state" record,
    and a boot snapshot that only carried the machine's
    own stated state carried the not-reported lines
    instead. Now the boot path calls this first: a
    snapshot that carries no "system_state" key gets a
    copy with one built from itself — "drivers" from
    the snapshot's own stated drivers list, in order,
    "gateway_healthy" from its own stated gateway
    health, and "skill_apps" from its own stated skill
    apps list, in order — with one as_of stamp for the
    whole record, so the lines' age agrees with the
    other boot lines instead of drifting across reads.
    A snapshot that already carries "system_state" is
    returned as an unchanged copy: a hand-stated record
    wins over a built one, so a caller that knows its
    machine state better than these flat lists is never
    overwritten. The record exists only when the
    snapshot states something usable, so a snapshot
    that states nothing usable gets no record at all,
    and older briefs keep their exact shape instead of
    gaining a silent record: a boot brief over such a
    snapshot still renders the three not-reported
    lines, as before. A driver or skill app named
    twice is one entry, not two: the first listing
    wins, in stated order. A name that is not a
    non-empty string is skipped, never guessed — and a
    list of only skipped names counts as nothing
    stated, so junk alone never builds a record. A
    stated empty list does count: it is the caller
    saying none, and it reads "no drivers reported"
    or "no skill apps mounted", never "not reported".
    Gateway health counts only as a real bool: True
    reads healthy, False reads down, and anything else
    — a string, a number, a missing key — is skipped,
    never guessed, so a caller that does not know its
    gateway health never gets a healthy or down line
    it did not state. The caller's snapshot is never
    mutated, and this never raises: a builder failure
    leaves the copy without a system_state record, so
    the boot path still produces a brief, just with the
    not-reported lines, instead of failing outright.
    This still reads stated inputs, never live machine
    state: the driver contract (OS-053), the gateway
    daemon (OS-058), and the skills loader (OS-065)
    have not landed, so a caller that states no
    drivers, gateway health, or skill apps gets the
    not-reported lines even when drivers are running
    somewhere else.
    """
    if isinstance(snapshot, dict):
        filled = dict(snapshot)
    else:
        filled = {}
    if "system_state" in filled:
        return filled
    try:
        stamp = int(time.time() if now is None else now)
    except Exception:
        stamp = int(time.time())
    record = {"as_of": stamp}
    try:
        if not isinstance(snapshot, dict):
            return filled
        usable = False
        for key in ("drivers", "skill_apps"):
            stated = snapshot.get(key)
            if not isinstance(stated, list):
                continue
            usable_names = []
            seen_names = set()
            for name in stated:
                if not (isinstance(name, str) and name):
                    continue
                if name in seen_names:
                    continue
                seen_names.add(name)
                usable_names.append(name)
            if stated == [] or usable_names:
                record[key] = usable_names
                usable = True
        gateway = snapshot.get("gateway_healthy")
        if isinstance(gateway, bool):
            record["gateway_healthy"] = gateway
            usable = True
        if not usable:
            return filled
    except Exception:
        return filled
    filled["system_state"] = record
    return filled


def environment_lines(env):
    """OS-103: the four launch-environment lines for a boot
    brief, in that order, one line each: Repo, Bus, Working
    now, Budget.

    `env` is the snapshot's "environment" record: "repo"
    (branch, short commit, dirty count of uncommitted
    files), "bus" (rooms, message count), "jobs" (job
    dicts, claimed jobs only count as work in progress),
    "budget" (lane, spent and cap, or remaining directly).
    Every line that states a value carries its age label:
    the record's as_of time, or the time-not-reported label
    when the record gives no time — a stale field is never
    silently presented as current. A missing record or a
    missing field is reported as not reported, never
    guessed; an empty jobs list means nobody holds a
    claimed job, never a padded name. The lines are
    redacted by the composer, not here, and they are not
    bullet lines, so the BRF-007 budget trim never drops
    them ahead of a watch item.
    """
    if not isinstance(env, dict):
        env = {}
    repo = env.get("repo")
    if (isinstance(repo, dict)
            and isinstance(repo.get("branch"), str)
            and repo.get("branch")
            and isinstance(repo.get("commit"), str)
            and repo.get("commit")):
        dirty = repo.get("dirty")
        if dirty == 0:
            tree = ", clean"
        elif isinstance(dirty, int) and not isinstance(dirty, bool) \
                and dirty > 0:
            tree = (f", {dirty} uncommitted "
                    f"file{'s' if dirty != 1 else ''}")
        else:
            tree = ""
        repo_line = (f"Repo: {repo['branch']} at {repo['commit']}"
                     f"{tree}"
                     f"{_environment_age_label(repo.get('as_of'))}")
    else:
        repo_line = "Repo state: not reported in this snapshot"
    bus = env.get("bus")
    if isinstance(bus, dict):
        rooms = [room for room in (bus.get("rooms") or [])
                 if isinstance(room, str) and room]
        messages = bus.get("messages")
        parts = []
        if isinstance(messages, int) and not isinstance(messages, bool):
            parts.append(f"{messages} messages")
        if rooms:
            parts.append("in room" + ("s" if len(rooms) != 1 else "")
                         + " " + ", ".join(rooms))
        if parts:
            bus_line = ("Bus: " + " ".join(parts)
                        + _environment_age_label(bus.get("as_of")))
        else:
            bus_line = "Bus state: not reported in this snapshot"
    else:
        bus_line = "Bus state: not reported in this snapshot"
    if "jobs" not in env:
        working_line = "Working now: not reported in this snapshot"
    else:
        claimed = []
        for job in (env.get("jobs") or []):
            if not isinstance(job, dict):
                continue
            if job.get("status") != "claimed":
                continue
            nick = job.get("claim")
            title = job.get("title")
            if isinstance(nick, str) and nick \
                    and isinstance(title, str) and title:
                claimed.append(f"{nick}: {title}")
        if claimed:
            working_line = ("Working now: " + "; ".join(claimed)
                            + _environment_age_label(env.get("as_of")))
        else:
            working_line = ("Working now: nobody holds a claimed "
                            "job in this snapshot"
                            + _environment_age_label(env.get("as_of")))
    budget = env.get("budget")
    if isinstance(budget, dict):
        lane = budget.get("lane")
        cap = budget.get("cap")
        remaining = budget.get("remaining")
        if not (isinstance(remaining, int)
                and not isinstance(remaining, bool)):
            spent = budget.get("spent")
            if (isinstance(cap, int) and not isinstance(cap, bool)
                    and isinstance(spent, int)
                    and not isinstance(spent, bool)):
                remaining = cap - spent
            else:
                remaining = None
        if (isinstance(lane, str) and lane
                and isinstance(remaining, int)
                and not isinstance(remaining, bool)):
            cap_part = ""
            if isinstance(cap, int) and not isinstance(cap, bool):
                cap_part = f" of {cap} cap"
            budget_line = (f"Budget: {lane} lane: {remaining} "
                           f"remaining{cap_part}"
                           + _environment_age_label(
                               budget.get("as_of")))
        else:
            budget_line = "Budget: not reported in this snapshot"
    else:
        budget_line = "Budget: not reported in this snapshot"
    return [repo_line, bus_line, working_line, budget_line]


def recovery_line(recovery):
    """OS-127: the one in-flight-jobs-recovered line for
    a boot brief.

    `recovery` is the snapshot's "recovery" record: the
    jobs the lease sweep recovered at this boot, each
    with its id, its title, and the baton step it
    resumed from, plus the sweep's own recovered count
    to reconcile against, plus any job records the
    sweep found corrupted. The line is reconciled, not
    merely counted: a clean count is rendered only when
    the sweep count equals the number of recovered job
    records, and only then are the titles and baton
    steps named. Any other shape says recovery is
    incomplete instead of a false all-clear: a sweep
    count that disagrees with the record count, a
    record with no sweep count to reconcile against, a
    corrupted job (named, so the reader knows which
    job did not recover cleanly), or an unreadable
    recovered record. A clean shutdown is a reconciled
    record with zero recovered jobs, and it reads zero
    recovered plainly. The line is not a bullet line,
    so the BRF-007 budget trim never drops it ahead
    of a watch item, and it is redacted by the
    composer, not here.
    """
    if not isinstance(recovery, dict):
        return ("In-flight jobs recovered at this boot: "
                "not reported in this snapshot")
    corrupted = recovery.get("corrupted")
    if isinstance(corrupted, list) and corrupted:
        names = []
        for job in corrupted:
            if isinstance(job, dict):
                job_id = job.get("id")
                title = job.get("title")
                if (isinstance(job_id, str) and job_id
                        and isinstance(title, str) and title):
                    names.append(f"job {job_id} {title}")
                elif isinstance(job_id, str) and job_id:
                    names.append(f"job {job_id}")
                elif isinstance(title, str) and title:
                    names.append(title)
            elif isinstance(job, str) and job:
                names.append(job)
        if names:
            return ("In-flight jobs recovered at this boot: "
                    "recovery incomplete, "
                    + "; ".join(f"{name} has a corrupted record"
                                for name in names))
        return ("In-flight jobs recovered at this boot: "
                "recovery incomplete, a corrupted job record "
                "could not be named")
    recovered = recovery.get("recovered")
    if not isinstance(recovered, list):
        recovered = []
    usable = []
    unreadable = False
    for job in recovered:
        if (isinstance(job, dict)
                and isinstance(job.get("id"), str) and job.get("id")
                and isinstance(job.get("title"), str)
                and job.get("title")):
            usable.append(job)
        else:
            unreadable = True
    if unreadable:
        return ("In-flight jobs recovered at this boot: "
                "recovery incomplete, a recovered job record "
                "is unreadable")
    sweep = recovery.get("sweep_count")
    if not (isinstance(sweep, int) and not isinstance(sweep, bool)):
        return ("In-flight jobs recovered at this boot: "
                "recovery incomplete, no lease sweep count "
                "to reconcile against")
    if sweep != len(usable):
        return ("In-flight jobs recovered at this boot: "
                f"recovery incomplete, the lease sweep reports "
                f"{sweep} recovered but {len(usable)} job "
                f"records were recovered")
    if not usable:
        return ("In-flight jobs recovered at this boot: "
                "0 recovered")
    parts = []
    for job in usable:
        step = job.get("baton_step")
        if isinstance(step, int) and not isinstance(step, bool):
            step_text = f"baton step {step}"
        elif isinstance(step, str) and step:
            step_text = step
        else:
            step_text = "step not reported"
        parts.append(f"job {job['id']} {job['title']} "
                     f"(resumed at {step_text})")
    return ("In-flight jobs recovered at this boot: "
            f"{len(usable)} recovered: " + "; ".join(parts))


def federation_lines(federation):
    """OS-117: the crew-of-crews section lines for a
    morning brief, one line per joined machine plus
    one line per trust event.

    `federation` is the snapshot's "federation" record:
    "machines" (each with a name, the titles its crew
    completed, and its cross-machine jobs with id, title,
    and status) and "trust_events" (each a join or a
    refusal, with the machine name and a detail). The
    section exists only for a real crew of crews: a
    record naming fewer than two usable machines
    returns no lines at all, so a single-machine brief
    renders the section absent, never empty-padded,
    and a record with no machines returns none either.
    A machine with no completions says nothing
    reported, never a padded title; a cross-machine
    job without an id and a title is skipped, never
    guessed; a trust event without a machine name is
    skipped, and a refusal without a detail says the
    reason is not reported, never an invented reason.
    Completions and job titles are named verbatim from
    the record, never re-derived from raw history.
    The lines are bullet lines in the section the
    composer adds, so they are redacted by the
    composer, not here, and the BRF-007 budget trim
    may drop them like any other section bullet when
    a brief runs over budget.
    """
    if not isinstance(federation, dict):
        return []
    machines = federation.get("machines")
    if not isinstance(machines, list):
        return []
    usable = [machine for machine in machines
              if isinstance(machine, dict)
              and isinstance(machine.get("name"), str)
              and machine.get("name")]
    if len(usable) < 2:
        return []
    lines = []
    for machine in usable:
        completions = [title
                       for title in
                       (machine.get("completions") or [])
                       if isinstance(title, str) and title]
        if completions:
            line = (f"- {machine['name']}: completed "
                    + ", ".join(completions))
        else:
            line = (f"- {machine['name']}: no completions "
                    "reported")
        cross = machine.get("cross_machine_jobs")
        if isinstance(cross, list):
            usable_cross = []
            for job in cross:
                if (isinstance(job, dict)
                        and isinstance(job.get("id"), str)
                        and job.get("id")
                        and isinstance(job.get("title"), str)
                        and job.get("title")):
                    status = job.get("status")
                    status_text = (f" ({status})"
                                   if isinstance(status, str)
                                   and status else "")
                    usable_cross.append(
                        f"job {job['id']} {job['title']}"
                        f"{status_text}")
            if usable_cross:
                line += ("; cross-machine jobs: "
                         + "; ".join(usable_cross))
        lines.append(line)
    events = federation.get("trust_events")
    if isinstance(events, list):
        for event in events:
            if not isinstance(event, dict):
                continue
            machine = event.get("machine")
            if not (isinstance(machine, str) and machine):
                continue
            detail = event.get("detail")
            detail_text = (f": {detail}"
                           if isinstance(detail, str)
                           and detail else "")
            if event.get("kind") == "join":
                lines.append(f"- Trust: {machine} joined "
                             f"the federation{detail_text}")
            elif event.get("kind") == "refusal":
                if detail_text:
                    lines.append(f"- Trust: {machine} was "
                                 f"refused{detail_text}")
                else:
                    lines.append(f"- Trust: {machine} was "
                                 "refused (reason not "
                                 "reported)")
    return lines


def memory_budget_lines(record):
    """OS-079: the settled-decisions line plus one
    spend-vs-budget line per lane, opening a brief.

    `record` is the snapshot's "memory_budget" record:
    "settled_decisions" (decision strings pulled from the
    memory service, named verbatim, never re-derived from
    raw history), "memory_down" (True when the memory
    service did not answer), and "budgets" (one entry per
    lane: lane name, spent and cap, or remaining
    directly). The lines open the brief, right after the
    window line and before the digest and the sections:
    a reader meets what is already settled before what
    is new. A down memory service is said, never hidden
    behind an absent line (OS-050 honesty rule): with
    the service down, no settled decision is shown and
    none is invented. A missing record field is reported
    as not reported, never guessed; an empty decision
    list reads none reported, never padded with a
    decision. A budget entry needs a lane name and a
    usable figure (spent plus cap, or remaining); an
    entry without one is skipped, and a record with no
    usable budget entry renders the not-reported line
    instead of a made-up figure. Every line carries its
    age label from the record's as_of time, or the
    snapshot-time-not-reported label when the record
    gives no time, so a stale figure is never silently
    presented as current. The lines are rendered
    whenever the snapshot carries a memory_budget
    record, in a boot brief and in a morning brief alike
    (OS-079 covers both); a snapshot without the record
    carries none, so older briefs keep their exact
    shape. They are not bullet lines, so the BRF-007
    budget trim never drops them ahead of a watch item,
    and they are redacted by the composer, not here.
    """
    if not isinstance(record, dict):
        record = {}

    def _usable_int(value):
        return isinstance(value, int) and not isinstance(value, bool)

    if record.get("memory_down") is True:
        settled = ("Settled decisions from memory: memory "
                   "service down, so no settled decisions "
                   "are shown")
    elif "settled_decisions" not in record:
        settled = ("Settled decisions from memory: not "
                   "reported in this snapshot")
    else:
        decisions = [decision
                     for decision in
                     (record.get("settled_decisions") or [])
                     if isinstance(decision, str) and decision]
        if decisions:
            settled = ("Settled decisions from memory: "
                       + "; ".join(decisions))
        else:
            settled = ("Settled decisions from memory: none "
                       "reported")
    lines = [settled + _environment_age_label(record.get("as_of"))]
    budget_lines = []
    budgets = record.get("budgets")
    if isinstance(budgets, list):
        for entry in budgets:
            if not isinstance(entry, dict):
                continue
            lane = entry.get("lane")
            if not (isinstance(lane, str) and lane):
                continue
            cap = entry.get("cap")
            spent = entry.get("spent")
            remaining = entry.get("remaining")
            if _usable_int(spent) and _usable_int(cap):
                remaining = cap - spent
                text = (f"Spend: {lane} lane: {spent} of "
                        f"{cap} budget ({remaining} "
                        f"remaining)")
            elif _usable_int(remaining) and _usable_int(cap):
                text = (f"Spend: {lane} lane: {remaining} "
                        f"remaining of {cap} cap")
            elif _usable_int(remaining):
                text = (f"Spend: {lane} lane: {remaining} "
                        f"remaining")
            else:
                continue
            age = entry.get("as_of", record.get("as_of"))
            if entry.get("held") is True:
                # OS-085: a lane at cap holds new claims, and
                # the hold is visible in the budget line
                # itself — the reader meets the hold where
                # they meet the spend, not in a section they
                # might skip. Entries without the flag render
                # exactly as before.
                text += " — new claims held"
            budget_lines.append(text + _environment_age_label(age))
    if budget_lines:
        lines.extend(budget_lines)
    else:
        lines.append("Spend vs budget: not reported in this snapshot")
    return lines


def memory_depth_lines(record):
    """OS-092: the long-term-memory lines for a daily
    brief, in the brief's plain-English standard.

    `record` is the snapshot's "memory_depth" record:
    "aged_decisions" (decisions aging out, each a
    decision string plus its original date), "due_
    commitments" (commitments made weeks ago that are
    due, each a commitment string plus its due date),
    and "fresh_context" (context a fresh agent would
    miss, each a plain string), all drawn from the
    memory service, never re-derived from raw history.
    "memory_down" (True when the memory service did
    not answer) says so in one line and shows no item
    at all, under the OS-050 honesty rule: a down
    service must never hide behind an absent section.
    An aged decision or a due commitment is named
    verbatim from the record; a missing original date
    reads original date not reported, and a missing
    due date reads due date not reported, never a
    guessed date. An entry without its text is skipped,
    never padded. A category with no usable entries
    reads none reported, never a padded item, and a
    record with no usable entry at all still renders
    its three none-reported lines, so a reader can tell
    the memory was checked and held nothing, rather
    than guessing whether it was checked. Every line
    carries its age label from the record's as_of time,
    or the snapshot-time-not-reported label when the
    record gives no time, so a stale item is never
    silently presented as current. The lines are plain
    lines, not bullets, so the BRF-007 budget trim
    never drops an aged commitment ahead of a watch
    item, and they are redacted by the composer, not
    here. They render whenever the snapshot carries a
    memory_depth record, in a morning-format brief;
    a snapshot without the record carries none, so
    older briefs keep their exact shape.
    """
    if not isinstance(record, dict):
        record = {}
    if record.get("memory_down") is True:
        return ["Long-term memory: memory service down, "
                "so no aged decisions, due commitments, "
                "or fresh-agent context are shown"]
    age = _environment_age_label(record.get("as_of"))
    lines = []
    aged = record.get("aged_decisions")
    usable_aged = []
    if isinstance(aged, list):
        for entry in aged:
            if not isinstance(entry, dict):
                continue
            decision = entry.get("decision")
            if not (isinstance(decision, str) and decision):
                continue
            date = entry.get("original_date")
            if isinstance(date, str) and date:
                usable_aged.append(f"Aged decision: {decision} "
                                   f"(from {date})")
            else:
                usable_aged.append(f"Aged decision: {decision} "
                                   "(original date not "
                                   "reported)")
    if usable_aged:
        lines.extend(line + age for line in usable_aged)
    else:
        lines.append("Aged decisions: none reported" + age)
    due = record.get("due_commitments")
    usable_due = []
    if isinstance(due, list):
        for entry in due:
            if not isinstance(entry, dict):
                continue
            commitment = entry.get("commitment")
            if not (isinstance(commitment, str) and commitment):
                continue
            due_date = entry.get("due")
            if isinstance(due_date, str) and due_date:
                usable_due.append(f"Due commitment: {commitment} "
                                  f"(due {due_date})")
            else:
                usable_due.append(f"Due commitment: {commitment} "
                                  "(due date not reported)")
    if usable_due:
        lines.extend(line + age for line in usable_due)
    else:
        lines.append("Due commitments: none reported" + age)
    context = record.get("fresh_context")
    usable_context = []
    if isinstance(context, list):
        usable_context = [item for item in context
                          if isinstance(item, str) and item]
    if usable_context:
        lines.extend(f"Fresh-agent context: {item}" + age
                     for item in usable_context)
    else:
        lines.append("Fresh-agent context: none reported" + age)
    return lines


def daily_lines(record):
    """OS-075: Dale's daily brief section, in the brief's
    plain-English standard.

    `record` is the snapshot's "daily" record:
    "overnight_results" (what the crew finished
    overnight, each a plain string), "todays_queue"
    (today's queue, each a job with an id and a
    title), and "needs_word" (what needs Dale's
    word, each a question string, or a dict with a
    question plus the job id it waits on), all
    stated by the caller that builds the brief
    snapshot, never re-derived from raw history.
    A result or a question is named verbatim from
    the record; a queue job without both an id and
    a title is skipped, and a needs-word entry
    without a question is skipped, never padded.
    A category with no usable entries reads none
    reported, never a padded item, and a record
    with no usable entry at all still renders its
    three none-reported lines, so a reader can tell
    the daily section was checked and held nothing,
    rather than guessing whether it was checked.
    Every line carries its age label from the
    record's as_of time, or the snapshot-time-not-
    reported label when the record gives no time,
    so a stale daily section is never silently
    presented as current. The lines are plain
    lines, not bullets, so the BRF-007 budget trim
    never drops a question waiting on Dale's word
    ahead of a watch item, and they are redacted
    by the composer, not here. They render
    whenever the snapshot carries a daily record,
    in a morning-format brief; a snapshot without
    the record carries none, so older briefs keep
    their exact shape. This is the daily brief's
    section only, not the daily brief itself: the
    desktop session it is read on (Rowan OS-071)
    has not landed, and two weeks of daily briefs
    on the daily machine have not run, so no
    prompt-history change from Dale's feedback is
    recorded here yet — format changes from his
    feedback belong in the prompt history when
    real daily use produces them, never invented
    ahead of use.
    """
    if not isinstance(record, dict):
        record = {}
    age = _environment_age_label(record.get("as_of"))
    lines = []
    results = record.get("overnight_results")
    usable_results = []
    if isinstance(results, list):
        usable_results = [item for item in results
                          if isinstance(item, str) and item]
    if usable_results:
        lines.extend(f"Overnight result: {item}" + age
                     for item in usable_results)
    else:
        lines.append("Overnight results: none reported" + age)
    queue = record.get("todays_queue")
    usable_queue = []
    if isinstance(queue, list):
        for job in queue:
            if (isinstance(job, dict)
                    and isinstance(job.get("id"), str)
                    and job.get("id")
                    and isinstance(job.get("title"), str)
                    and job.get("title")):
                usable_queue.append(job)
    if usable_queue:
        lines.extend(f"Today's queue: job {job['id']} "
                     f"{job['title']}" + age
                     for job in usable_queue)
    else:
        lines.append("Today's queue: none reported" + age)
    needs = record.get("needs_word")
    usable_needs = []
    if isinstance(needs, list):
        for entry in needs:
            if isinstance(entry, str) and entry:
                usable_needs.append(entry)
            elif (isinstance(entry, dict)
                    and isinstance(entry.get("question"), str)
                    and entry.get("question")):
                question = entry["question"]
                job_id = entry.get("job")
                if isinstance(job_id, str) and job_id:
                    question += f" (job {job_id})"
                usable_needs.append(question)
    if usable_needs:
        lines.extend(f"Needs your word: {item}" + age
                     for item in usable_needs)
    else:
        lines.append("Needs your word: none reported" + age)
    return lines


def held_decisions_lines(record):
    """INT-027 follow-up: the held-decisions lines for a
    morning brief, closing cold-start gap 3 (no held
    decisions) from a stated record.

    `record` is the snapshot's "held_decisions" record:
    "decisions" (each a dict with a question string plus
    an optional decider nick), stated by the caller that
    builds the brief snapshot, never re-derived from raw
    history — the INT-027 verdict documented this gap as
    a limit precisely because no such source existed in
    the FND-033 source map, and the record is that
    source, supplied by the caller the same way the
    daily, memory, and federation records are. A
    question is named verbatim from the record; an
    entry without a question is skipped, never padded;
    a decision without a decider reads decider not
    reported, never a guessed nick. A record with no
    usable entries reads none reported, never a padded
    decision, so a reader can tell the held list was
    checked and held nothing. Every line carries its
    age label from the record's as_of time, or the
    snapshot-time-not-reported label when the record
    gives no time, so a stale held list is never
    silently presented as current. The lines are plain
    lines, not bullets, so the BRF-007 budget trim
    never drops a decision waiting on Dale's word
    ahead of a watch item, and they are redacted by
    the composer, not here. They render whenever the
    snapshot carries a held_decisions record, in a
    morning-format brief; a snapshot without the
    record carries none, so older briefs keep their
    exact shape. This closes gap 3 for the template
    brief only: a Spark-composed brief carrying these
    lines, and an independent lane member's cold-start
    re-run, are still owed, the same caveats INT-027
    carries.
    """
    if not isinstance(record, dict):
        record = {}
    age = _environment_age_label(record.get("as_of"))
    usable = []
    decisions = record.get("decisions")
    if isinstance(decisions, list):
        for entry in decisions:
            if (isinstance(entry, dict)
                    and isinstance(entry.get("question"), str)
                    and entry.get("question")):
                question = entry["question"]
                decider = entry.get("decider")
                if isinstance(decider, str) and decider:
                    usable.append(f"Held decision: {question} "
                                  f"(waiting on {decider})")
                else:
                    usable.append(f"Held decision: {question} "
                                  "(decider not reported)")
    if usable:
        return [line + age for line in usable]
    return ["Held decisions: none reported" + age]


def source_pointer_lines(pointers):
    """INT-027 follow-up: the sources lines for a
    morning brief, closing cold-start gap 4 (no source
    pointers) from a stated list.

    `pointers` is the snapshot's "source_pointers" list:
    plain strings naming where the brief's details live
    (a lane file, an eval log, a fixture manifest),
    stated by the caller that builds the brief snapshot,
    never guessed from a job title — the INT-027 verdict
    documented this gap as a limit because no such
    source existed in the FND-033 source map, and the
    list is that source, supplied by the caller the same
    way the other section records are. A pointer is
    named verbatim from the list; a non-string or empty
    entry is skipped, never padded. An absent or empty
    list returns no lines at all, so a brief without
    pointers renders no Sources section rather than a
    padded one, and older briefs keep their exact
    shape. The lines are plain lines, not bullets, so
    the BRF-007 budget trim never drops a source
    pointer ahead of a watch item, and they are
    redacted by the composer, not here. Pointers name
    locations, not dated facts, so they carry no age
    label: a path does not go stale the way a figure
    does, and a not-reported label on one would read
    as a missing fact rather than a location. This
    closes gap 4 for the template brief only, under
    the same still-owed caveats as held_decisions_lines.
    """
    if not isinstance(pointers, list):
        return []
    usable = [item for item in pointers
              if isinstance(item, str) and item]
    if not usable:
        return []
    return [f"Source: {item}" for item in usable]


def since_last_brief_lines(previous_brief, jobs):
    """BRF-019 follow-up: the since-last-brief lines for a
    morning brief, closing cold-start gap 2 (no diff: old
    news and new news look identical) for the template
    brief from a stated record.

    `previous_brief` is the snapshot's "previous_brief"
    record: "jobs" (each a dict with an id and the status
    that job carried in the previous brief), stated by the
    caller that builds the brief snapshot, never guessed
    from a job title — the INT-027 verdict documented
    this gap as a limit precisely because no previous
    brief was in the window to compare against, and the
    record is that comparison source, supplied by the
    caller the same way the daily, memory, and
    federation records are. A job in the current window
    whose status differs from its previous-brief status
    reads as changed, with the old status and the new
    status both named; a job in the current window with
    no previous-brief entry reads as new; a job whose
    status is unchanged is not listed at all, so old
    news and new news never look identical. A current
    job with no id cannot be compared and is skipped,
    never padded with an invented id; a previous-brief
    entry with no id is skipped the same way. A record
    that is not a dict, or whose jobs are not a list,
    cannot be compared and yields no lines at all, so
    a malformed record never produces a false diff.
    When the comparison finds nothing changed, the
    single line reads nothing changed, never a padded
    change, so a reader can tell the diff was checked
    and the window held nothing new. Every line carries
    its age label from the record's as_of time, or the
    snapshot-time-not-reported label when the record
    gives no time, so a stale diff is never silently
    presented as current. The lines are plain lines,
    not bullets, so the BRF-007 budget trim never drops
    a change ahead of a watch item, and they are
    redacted by the composer, not here. They render
    whenever the snapshot carries a previous_brief
    record, in a morning-format brief; a snapshot
    without the record carries none, so older briefs
    keep their exact shape, and no line here ever
    marks a job as new without a previous-brief record
    to compare against. This closes gap 2 for the
    template brief only: a Spark-composed brief carrying
    these lines, and an independent lane member's
    cold-start re-run, are still owed, the same caveats
    INT-027 carries, and the v2 rule 10 sentence for
    a window with no previous brief at all ("nothing
    here is marked as new") is a prompt rule, not a
    template line — a template brief without the record
    says nothing about newness rather than claiming it.
    """
    if not isinstance(previous_brief, dict):
        return []
    prev_jobs = previous_brief.get("jobs")
    if not isinstance(prev_jobs, list):
        return []
    prev = {}
    for job in prev_jobs:
        if (isinstance(job, dict) and job.get("id")
                and job["id"] not in prev):
            prev[job["id"]] = job.get("status") or ""
    age = _environment_age_label(previous_brief.get("as_of"))
    lines = []
    current = jobs if isinstance(jobs, list) else []
    for job in current:
        if not isinstance(job, dict):
            continue
        job_id = job.get("id")
        if not job_id:
            continue
        title = job.get("title", "")
        status = job.get("status") or ""
        if job_id not in prev:
            lines.append(f"New since your last brief: {job_id} "
                         f"{title} ({status})")
        elif prev[job_id] != status:
            lines.append(f"Changed since your last brief: {job_id} "
                         f"{title}: {prev[job_id]} -> {status}")
    if lines:
        return [line + age for line in lines]
    return ["Nothing changed since your last brief" + age]


def priority_order_lines(record, jobs):
    """INT-027 follow-up: the priority-order lines for a
    morning brief, closing cold-start gap 1 (no priority
    order: the brief lists jobs by section, never by
    lane task id or dependency order) for the template
    brief from a stated record.

    `record` is the snapshot's "priority_order" record:
    "order" (a list of job ids in priority order, first
    first), stated by the caller that builds the brief
    snapshot, never guessed from a job title or a
    section order — the INT-027 verdict documented this
    gap as a limit precisely because no priority field
    existed in the window, and the record is that
    field, supplied by the caller the same way the
    daily, memory, and federation records are. A job
    id in the order is named with its title from the
    snapshot's jobs list, in record order, numbered
    from 1; an id with no matching job is skipped,
    never padded with an invented title, and a job
    the record does not list is not listed here at
    all, never guessed into an order. A duplicate id
    in the order is listed once, at its first place.
    A record that is not a dict, or whose order is
    not a list, yields no lines at all, so a malformed
    record never produces a false order; an order
    list with no usable entry reads none reported,
    never a padded order. Every line carries its age
    label from the record's as_of time, or the
    snapshot-time-not-reported label when the record
    gives no time, so a stale order is never silently
    presented as current. The lines are plain lines,
    not bullets, so the BRF-007 budget trim never
    drops the order ahead of a watch item, and they
    are redacted by the composer, not here. They
    render whenever the snapshot carries a
    priority_order record, in a morning-format brief;
    a snapshot without the record carries none, so
    older briefs keep their exact shape. This closes
    gap 1 for the template brief only, and it does so
    additively: the In flight lines it leaves alone
    keep their pinned shape, because rewriting them
    in place was what the BRF-019 follow-up could not
    do without breaking those pins. A Spark-composed
    brief carrying these lines, and an independent
    lane member's cold-start re-run, are still owed,
    the same caveats INT-027 carries.
    """
    if not isinstance(record, dict):
        return []
    order = record.get("order")
    if not isinstance(order, list):
        return []
    age = _environment_age_label(record.get("as_of"))
    titles = {}
    current = jobs if isinstance(jobs, list) else []
    for job in current:
        if (isinstance(job, dict) and job.get("id")
                and job["id"] not in titles):
            titles[job["id"]] = job.get("title", "") or ""
    seen = set()
    lines = []
    for job_id in order:
        if (not isinstance(job_id, str) or not job_id
                or job_id in seen or job_id not in titles):
            continue
        seen.add(job_id)
        title = titles[job_id]
        if title:
            lines.append(f"Priority {len(lines) + 1}: "
                         f"{job_id} {title}")
        else:
            lines.append(f"Priority {len(lines) + 1}: {job_id}")
    if lines:
        return [line + age for line in lines]
    return ["Priority order: none reported" + age]


def blocked_contact_lines(record, jobs):
    """INT-027 follow-up: the blocked-contacts lines for a
    morning brief, closing cold-start gap 5 (no ask-nick
    on the blocked job: the blocked line names the job
    and its reason, but no owner to ask about it) for
    the template brief from a stated record.

    `record` is the snapshot's "blocked_contacts"
    record: "contacts" (each a dict with a job_id and
    an optional ask nick), stated by the caller that
    builds the brief snapshot, never guessed from a
    job title — the INT-027 verdict documented this
    gap as a limit precisely because a blocked job
    carries no owner field, and the record is that
    field, supplied by the caller the same way the
    daily, memory, and federation records are. The
    lines cover every blocked job in the snapshot, in
    snapshot order, not only the jobs the record
    names: a blocked job with a contact entry reads
    "Ask <nick> about <id> <title>", and a blocked
    job with no usable entry reads "<id> <title>:
    owner not reported in this window", the v2 rule 8
    wording, never a guessed nick. A contact entry
    for a job that is not blocked in this snapshot is
    ignored, never a contact for a job that is not
    blocked; a blocked job with no id cannot be
    named here and is skipped, though its blocked
    line still names it in the Blocked section. A
    record that is not a dict, or whose contacts are
    not a list, yields no lines at all, so a malformed
    record never produces a false contact; a record
    over a window with no blocked jobs reads none
    reported, never a padded contact. Every line
    carries its age label from the record's as_of
    time, or the snapshot-time-not-reported label
    when the record gives no time, so a stale contact
    is never silently presented as current. The lines
    are plain lines, not bullets, so the BRF-007
    budget trim never drops a contact ahead of a
    watch item, and they are redacted by the
    composer, not here. They render whenever the
    snapshot carries a blocked_contacts record, in a
    morning-format brief; a snapshot without the
    record carries none, so older briefs keep their
    exact shape. This closes gap 5 for the template
    brief only, and it does so additively: the
    Blocked and why lines it leaves alone keep their
    verbatim pinned shape, because rewriting them in
    place was what the BRF-019 follow-up could not do
    without breaking those pins. A Spark-composed
    brief carrying these lines, and an independent
    lane member's cold-start re-run, are still owed,
    the same caveats INT-027 carries.
    """
    if not isinstance(record, dict):
        return []
    contacts = record.get("contacts")
    if not isinstance(contacts, list):
        return []
    age = _environment_age_label(record.get("as_of"))
    ask_by_job = {}
    for entry in contacts:
        if (isinstance(entry, dict) and entry.get("job_id")
                and entry["job_id"] not in ask_by_job):
            ask = entry.get("ask")
            ask_by_job[entry["job_id"]] = (
                ask if isinstance(ask, str) and ask else "")
    lines = []
    current = jobs if isinstance(jobs, list) else []
    for job in current:
        if (not isinstance(job, dict)
                or job.get("status") != "blocked"
                or not job.get("id")):
            continue
        job_id = job["id"]
        title = job.get("title", "") or ""
        if title:
            label = f"{job_id} {title}"
        else:
            label = job_id
        ask = ask_by_job.get(job_id, "")
        if ask:
            lines.append(f"Ask {ask} about {label}")
        else:
            lines.append(f"{label}: owner not reported "
                         "in this window")
    if lines:
        return [line + age for line in lines]
    return ["Blocked contacts: none reported" + age]


def onjoin_template_lines(snapshot):
    """BRF-018 follow-up: the four BRF-002 on-join sections for a
    template brief, in prompt order: What this crew is building,
    Your likely lane, What is blocked, Who to ask.

    Before this change the template composer rendered the
    morning sections for every kind, so an on-join template
    brief carried no project sentence, no likely-lane line,
    and no ask-for-a-first-job line — the composer gap the
    BRF-018 cold-read verdict pinned. Now a kind="onjoin"
    template brief renders these four sections instead, from
    the snapshot alone, never guessing: the crew-building
    sentence is the snapshot's stated "crew_building" string
    when the caller states one, else the prompt's own
    not-stated sentence; the likely-lane line names an open
    job's "lane" field in the v2 rule 9 form when the record
    carries one, and names a newcomer's capability record
    verbatim when one is stated for a newcomer, and when neither
    is stated it says so and points to the first owner to
    ask for a first job (or says plainly that no owner is
    recorded); blocked lines quote reasons verbatim, or
    read "Nothing blocked in this window"; Who to ask names
    the claimed-job owners, marking one "not online in this
    window" only when the snapshot carries a presence list
    that does not name them, plus the blocked-contact ask
    nick when the snapshot carries a blocked_contacts
    record. The four section lines are plain lines, not
    bullets, so the BRF-007 budget trim cannot drop a
    blocked job or an ask-nick ahead of any other line;
    the additive INT-004 sections below use the morning
    bullet form, so under trim they drop first, the same
    order the morning brief trims in. This never raises:
    a non-dict snapshot reads as an empty one.
    """
    snapshot = snapshot if isinstance(snapshot, dict) else {}
    lines = []
    lines.append("What this crew is building")
    crew = snapshot.get("crew_building")
    if isinstance(crew, str) and crew.strip():
        lines.append(crew.strip())
    else:
        lines.append("The room's current work is not stated "
                     "in this window")
    lines.append("")
    lines.append("Your likely lane")
    jobs = snapshot.get("jobs")
    if not isinstance(jobs, list):
        jobs = []
    open_job = None
    for job in jobs:
        if isinstance(job, dict) and job.get("status") == "open":
            open_job = job
            break
    lane_lines = []
    has_lane_or_caps = False
    if open_job is not None:
        title = open_job.get("title", "") or ""
        lane = open_job.get("lane")
        if isinstance(lane, str) and lane:
            lane_lines.append(f"The open job {title} belongs "
                              f"to the {lane} lane")
            has_lane_or_caps = True
        elif title:
            job_id = open_job.get("id", "") or ""
            label = f"{job_id} {title}".strip()
            lane_lines.append(f"Open job: {label}")
    newcomers = detect_new_nicks(snapshot)
    caps = snapshot.get("caps")
    if isinstance(caps, dict):
        for newcomer in newcomers:
            record = caps.get(newcomer)
            if not isinstance(record, dict):
                continue
            caps_text = record.get("caps")
            roles_text = record.get("roles")
            if isinstance(caps_text, str) and caps_text:
                caps_line = (f"{newcomer}'s capability record "
                             f"lists {caps_text}")
                if isinstance(roles_text, str) and roles_text:
                    caps_line += f"; roles: {roles_text}"
                lane_lines.append(caps_line)
                has_lane_or_caps = True
    owners = extract_owners(snapshot)
    ask_nick = owners[0]["nick"] if owners else ""
    lines.extend(lane_lines)
    if not has_lane_or_caps:
        lines.append("No capability record and no open job "
                     "lane are stated in this window.")
        if ask_nick:
            lines.append(f"Ask {ask_nick} for a first job")
        else:
            lines.append("No owner is recorded in this window")
    lines.append("")
    lines.append("What is blocked")
    blocked = extract_blocked(snapshot)
    if blocked:
        for job in blocked:
            lines.append(f"{job['id']} {job['title']}: "
                         f"{job['reason']}")
    else:
        lines.append("Nothing blocked in this window")
    lines.append("")
    lines.append("Who to ask")
    presence = snapshot.get("presence")
    presence_nicks = None
    if isinstance(presence, dict):
        presence_nicks = {nick for nick in presence
                          if isinstance(nick, str)}
    elif isinstance(presence, list):
        presence_nicks = {nick for nick in presence
                          if isinstance(nick, str)}
    ask_lines = []
    for owner in owners:
        nick = owner["nick"]
        titles = ", ".join(job["title"] for job in owner["jobs"])
        line = f"{nick}: {titles}"
        if (presence_nicks is not None
                and nick not in presence_nicks):
            line += " (not online in this window)"
        ask_lines.append(line)
    contacts = None
    record = snapshot.get("blocked_contacts")
    if isinstance(record, dict) and isinstance(
            record.get("contacts"), list):
        contacts = {}
        for entry in record["contacts"]:
            if (isinstance(entry, dict) and entry.get("job_id")
                    and entry["job_id"] not in contacts):
                ask = entry.get("ask")
                contacts[entry["job_id"]] = (
                    ask if isinstance(ask, str) and ask else "")
    if contacts is not None:
        for job in blocked:
            ask = contacts.get(job["id"], "")
            label = f"{job['id']} {job['title']}"
            if ask:
                ask_lines.append(f"Ask {ask} about {label}")
            else:
                ask_lines.append(f"{label}: owner not reported "
                                 "in this window")
    if ask_lines:
        lines.extend(ask_lines)
    else:
        lines.append("No owner is recorded in this window")
    # INT-004 additive sections, after the four on-join
    # sections and only when they have content: the e2e3
    # loop's on-join stage reads the blocked job from a
    # "Blocked and why" section and the stall alert from a
    # "Watch items" section, so an on-join template brief
    # must still carry both, in the morning bullet form,
    # even though the four sections above already name
    # the blocked job in plain form. A brief with no
    # blocked job carries no additive Blocked section,
    # and one with no alerts carries no additive Watch
    # section, so the four sections stand alone then.
    if blocked:
        lines.append("")
        lines.append("Blocked and why")
        for job in blocked:
            lines.append(f"- {job['id']} {job['title']}: "
                         f"{job['reason']}")
    watch_items = extract_watch_items(snapshot)
    if watch_items:
        lines.append("")
        lines.append("Watch items")
        for item in watch_items:
            lines.append(f"- {item['id']}: {item['summary']}")
    return lines


def compose_template_brief(snapshot, boot=False, kind="morning"):
    """BRF-008: template brief from extractors alone, no LLM.

    Used when the Spark call fails (or is unavailable). The output
    is marked TEMPLATE in its first line, so no reader mistakes it
    for a Spark-composed brief. Every fact comes from the
    extractors above; nothing is invented, nothing is paraphrased
    away (blocked reasons stay verbatim). This function never
    calls Spark and never touches the network.

    BRF-018 follow-up: kind="onjoin" renders the four BRF-002
    sections via onjoin_template_lines instead of the morning
    sections, so a template on-join brief finally reads as an
    on-join brief. Any other kind, and a boot brief (boot
    briefs are morning kind by construction), keeps the
    morning shape exactly, and the default kind="morning"
    keeps every existing caller unchanged. The empty-room
    branch still wins for every kind: an on-join brief over
    an empty room says no activity yet, not four empty
    sections.
    """
    snapshot = snapshot or {}
    if kind not in BRIEF_BUDGETS:
        kind = "morning"
    # BRF-012: an empty room is not an error and never invents
    # content. A snapshot with no messages, no jobs, and no alerts
    # yields a short "nothing yet" brief, with no job names at all.
    # OS-050: cold-start honesty. An empty history is said to be
    # empty, never dressed up as a window with content. When the
    # snapshot states no window at all, the window line itself
    # says the window is empty; when a capped window kept
    # nothing, the line says so too. A stated string window with
    # no content keeps its stated line plus "no activity yet"
    # (BRF-012) — that case is a quiet room, not a cold start,
    # and the brief does not claim otherwise.
    if (not snapshot.get("messages") and not snapshot.get("jobs")
            and not snapshot.get("alerts")):
        window_line = _window_line(snapshot)
        if (not snapshot.get("source_window")
                and not snapshot.get("window_start")):
            window_line = ("Window: empty (no history is available "
                           "for this boot)")
        elif (isinstance(snapshot.get("source_window"), dict)
                and snapshot["source_window"].get("messages_kept") == 0):
            window_line += " The window is empty."
        # OS-051: a boot brief with a previous-session record
        # still opens with its digest even when this boot's
        # window is empty — the digest is about the previous
        # session, not this window, so it does not contradict
        # the empty window line. Without a record, nothing is
        # said about a previous session (OS-050 rule 3).
        digest = (previous_session_digest(snapshot.get("previous_session"))
                  if boot else None)
        body = "TEMPLATE\n\n" + window_line + "\n"
        # OS-079: a brief with a memory_budget record
        # opens with its settled-decisions line and its
        # spend-vs-budget lines, even over an empty
        # window — settled decisions and budgets are not
        # activity in the window, and a down memory
        # service must never hide behind an empty room.
        if "memory_budget" in snapshot:
            body += ("\n" + "\n".join(memory_budget_lines(
                snapshot.get("memory_budget"))) + "\n")
        if digest:
            body += "\n" + digest + "\n"
        # OS-062: a boot brief always carries its three system
        # lines, even over an empty window — the machine state
        # is not activity in the window, and a down gateway
        # must never hide behind an empty room.
        if boot:
            body += ("\n" + "\n".join(system_state_lines(
                snapshot.get("system_state"))) + "\n")
        # OS-103: a boot brief with an environment record
        # carries its four environment lines too, before "no
        # activity yet" — the surroundings are not activity
        # in the window, and a budget line must never hide
        # behind an empty room.
        if boot and "environment" in snapshot:
            body += ("\n" + "\n".join(environment_lines(
                snapshot.get("environment"))) + "\n")
        # OS-127: a boot brief with a recovery record
        # carries its one recovery line too, before "no
        # activity yet" — the recovered jobs are not
        # activity in the window, and a recovery that
        # came back incomplete must never hide behind
        # an empty room.
        if boot and "recovery" in snapshot:
            body += ("\n" + recovery_line(
                snapshot.get("recovery")) + "\n")
        # OS-075: a brief with a daily record
        # carries its daily section too, before "no
        # activity yet" -- overnight results, today's
        # queue, and what needs Dale's word are not
        # activity in this window, and a daily record
        # with nothing usable still reads none
        # reported per category, never padded.
        if "daily" in snapshot:
            body += ("\nDaily brief\n"
                     + "\n".join(daily_lines(
                         snapshot.get("daily"))) + "\n")
        # OS-092: a brief with a memory_depth record
        # carries its long-term-memory section too,
        # before "no activity yet" — aged decisions,
        # due commitments, and fresh-agent context are
        # not activity in this window, and a down
        # memory service must never hide behind an
        # empty room.
        if "memory_depth" in snapshot:
            body += ("\nLong-term memory\n"
                     + "\n".join(memory_depth_lines(
                         snapshot.get("memory_depth"))) + "\n")
        # OS-117: a brief with a federation record
        # naming at least two machines carries its
        # federation section too, before "no activity
        # yet" — what other machines' crews did is not
        # activity in this window, and a single-machine
        # record renders no section at all.
        if "federation" in snapshot:
            fed_lines = federation_lines(
                snapshot.get("federation"))
            if fed_lines:
                body += ("\nFederation\n"
                         + "\n".join(fed_lines) + "\n")
        # INT-027 follow-up: a brief with a
        # held_decisions record carries its held list
        # too, before "no activity yet" -- decisions
        # waiting on Dale's word are not activity in
        # this window, and a returner over an empty
        # window needs them most. A brief with source
        # pointers carries them too, so the returner
        # knows where the details live.
        if "held_decisions" in snapshot:
            body += ("\nHeld decisions\n"
                     + "\n".join(held_decisions_lines(
                         snapshot.get("held_decisions"))) + "\n")
        pointers = source_pointer_lines(
            snapshot.get("source_pointers"))
        if pointers:
            body += ("\nSources\n"
                     + "\n".join(pointers) + "\n")
        return redact_secrets(body + "\n"
                              + "no activity yet\n\n"
                              "This room has no activity yet in this window.\n")
    if kind == "onjoin" and not boot:
        lines = ["TEMPLATE", _window_line(snapshot), ""]
        lines.extend(onjoin_template_lines(snapshot))
        return redact_secrets("\n".join(lines) + "\n")
    lines = ["TEMPLATE"]
    lines.append(_window_line(snapshot))
    # BRF-019 follow-up: v2 rule 10 opens the brief with
    # its diff against the previous brief, before the
    # sections — but only when the snapshot carries a
    # previous_brief record, so a brief without one keeps
    # its exact older shape and never marks a job as new
    # without a record to compare against. A malformed
    # record yields no lines and no section, never a
    # false diff. The lines are plain lines, not bullets,
    # so the BRF-007 trim keeps them.
    if "previous_brief" in snapshot:
        since_lines = since_last_brief_lines(
            snapshot.get("previous_brief"), snapshot.get("jobs"))
        if since_lines:
            lines.append("")
            lines.append("Since your last brief")
            lines.extend(since_lines)
    # OS-079: a brief with a memory_budget record opens
    # with its settled-decisions line and its
    # spend-vs-budget lines, right after the window line
    # and before the digest and the sections — in a boot
    # brief and in a morning brief alike. A snapshot
    # without the record carries none, so older briefs
    # keep their exact shape.
    if "memory_budget" in snapshot:
        lines.extend(memory_budget_lines(
            snapshot.get("memory_budget")))
    # OS-051: a boot brief opens with its previous-session
    # digest line, right after the window line and before the
    # sections. A non-boot brief never carries it, even when
    # the snapshot happens to hold a previous-session record:
    # the digest belongs to the boot brief only.
    if boot:
        digest = previous_session_digest(
            snapshot.get("previous_session"))
        if digest:
            lines.append(digest)
        # OS-062: the three system lines follow the digest and
        # precede Decisions, in every boot brief — with values,
        # with none, or with health not reported, never omitted.
        lines.extend(system_state_lines(
            snapshot.get("system_state")))
        # OS-103: the four environment lines follow the
        # system lines and precede Decisions, but only when
        # the snapshot carries an environment record — a
        # snapshot without one keeps its older exact shape,
        # and a non-boot brief never carries them.
        if "environment" in snapshot:
            lines.extend(environment_lines(
                snapshot.get("environment")))
        # OS-127: the one recovery line follows the
        # environment lines and precedes Decisions,
        # but only when the snapshot carries a recovery
        # record — a snapshot without one keeps its
        # older exact shape, and a non-boot brief never
        # carries it.
        if "recovery" in snapshot:
            lines.append(recovery_line(
                snapshot.get("recovery")))
    lines.append("")
    lines.append("Decisions")
    decisions = extract_decisions(snapshot)
    if decisions:
        for decision in decisions:
            lines.append(f"- {decision['kind']}: {decision['text']}")
    else:
        lines.append("Nothing reported in this window")
    lines.append("")
    lines.append("In flight")
    in_flight = [job for job in (snapshot.get("jobs") or [])
                 if isinstance(job, dict)
                 and job.get("status") in ("open", "claimed")]
    if in_flight:
        for job in in_flight:
            lines.append(f"- {job.get('id', '')} "
                         f"{job.get('title', '')} "
                         f"({job.get('status', '')})")
    else:
        lines.append("Nothing reported in this window")
    lines.append("")
    lines.append("Owners")
    owners = extract_owners(snapshot)
    if owners:
        for owner in owners:
            titles = ", ".join(job["title"] for job in owner["jobs"])
            lines.append(f"- {owner['nick']}: {titles}")
    else:
        lines.append("Nothing reported in this window")
    lines.append("")
    lines.append("Blocked and why")
    blocked = extract_blocked(snapshot)
    if blocked:
        for job in blocked:
            lines.append(f"- {job['id']} {job['title']}: {job['reason']}")
    else:
        lines.append("Nothing blocked in this window")
    lines.append("")
    lines.append("Watch items")
    # WDG-028: the watchdog status line heads the Watch items
    # section, but only when the snapshot's alerts actually
    # carry severities — the stored alert records do, the
    # {id, summary} alert summaries of older snapshots do not,
    # and a severity-less snapshot keeps its exact older shape
    # rather than gaining a line of invented zeros. The line is
    # built from the same alert list the section renders, so
    # its counts and the items below it cannot disagree.
    alerts = snapshot.get("alerts") or []
    if any(isinstance(alert, dict)
           and alert.get("severity") in _store.ALERT_SEVERITIES
           for alert in alerts):
        lines.append(_store.build_watchdog_status(alerts)["line"])
    watch_items = extract_watch_items(snapshot)
    if watch_items:
        for item in watch_items:
            lines.append(f"- {item['id']}: {item['summary']}")
    else:
        lines.append("Nothing to watch in this window")
    # OS-075: the daily section follows Watch items,
    # but only when the snapshot carries a daily
    # record, so a brief without the record keeps
    # its exact older shape and a brief with an
    # empty record reads none reported, never
    # padded. It precedes Long-term memory: the
    # daily brief is the frame, the depth lines
    # are its detail.
    if "daily" in snapshot:
        lines.append("")
        lines.append("Daily brief")
        lines.extend(daily_lines(snapshot.get("daily")))
    # OS-092: the long-term-memory section follows Watch
    # items, but only when the snapshot carries a
    # memory_depth record, so a brief without the record
    # keeps its exact older shape and a brief with an
    # empty record reads none reported, never padded.
    if "memory_depth" in snapshot:
        lines.append("")
        lines.append("Long-term memory")
        lines.extend(memory_depth_lines(
            snapshot.get("memory_depth")))
    # OS-117: the federation section follows Watch items,
    # but only when the snapshot's federation record
    # names at least two machines, so a single-machine
    # brief renders the section absent, never
    # empty-padded, and a brief without the record keeps
    # its exact older shape.
    fed_lines = federation_lines(snapshot.get("federation"))
    if fed_lines:
        lines.append("")
        lines.append("Federation")
        lines.extend(fed_lines)
    # INT-027 follow-up: the Held decisions section
    # follows Watch items (and Federation, when one
    # renders), but only when the snapshot carries a
    # held_decisions record, so a brief without the
    # record keeps its exact older shape and a brief
    # with an empty record reads none reported, never
    # padded. The Sources section follows it, but
    # only when the window actually carries source
    # pointers, so a brief without pointers renders
    # no section at all.
    if "held_decisions" in snapshot:
        lines.append("")
        lines.append("Held decisions")
        lines.extend(held_decisions_lines(
            snapshot.get("held_decisions")))
    pointers = source_pointer_lines(
        snapshot.get("source_pointers"))
    if pointers:
        lines.append("")
        lines.append("Sources")
        lines.extend(pointers)
    # INT-027 follow-up: the Priority order section
    # follows Sources, but only when the snapshot
    # carries a priority_order record, so a brief
    # without the record keeps its exact older shape
    # and a malformed record yields no section, never
    # a false order. The Blocked contacts section
    # follows it, but only when the snapshot carries
    # a blocked_contacts record, so a brief without
    # the record keeps its exact older shape. Both
    # sections are additive: the In flight and
    # Blocked and why lines above keep their pinned
    # shape, and these sections supply the order and
    # the ask-nick those lines cannot carry in place.
    if "priority_order" in snapshot:
        prio_lines = priority_order_lines(
            snapshot.get("priority_order"), snapshot.get("jobs"))
        if prio_lines:
            lines.append("")
            lines.append("Priority order")
            lines.extend(prio_lines)
    if "blocked_contacts" in snapshot:
        contact_lines = blocked_contact_lines(
            snapshot.get("blocked_contacts"), snapshot.get("jobs"))
        if contact_lines:
            lines.append("")
            lines.append("Blocked contacts")
            lines.extend(contact_lines)
    # STR-002: the screenshot digest follows Watch items
    # (and the federation section, when one renders), but
    # only when the window actually carries image pointers, so a
    # brief without screenshots keeps its exact older shape.
    screenshot_refs = extract_screenshot_refs(snapshot)
    if screenshot_refs:
        lines.append("")
        lines.append("Screenshots")
        lines.extend(screenshot_digest_lines(screenshot_refs))
    # BRF-014: redact before the brief is stored or posted. This
    # is the one exception to verbatim blocked reasons.
    return redact_secrets("\n".join(lines) + "\n")


def extract_owners(snapshot):
    """BRF-006: claimed jobs mapped claim nick -> title -> age.

    Returns a list of dicts, one per owner nick, in first-claim
    order: {"nick", "jobs": [{"id", "title", "last_progress_age"}]}.
    "last_progress_age" is the job record's "last_progress_at"
    when present, else its "claimed_at" when present, else None.
    Honest limit: the current jobs.py tree has no
    last_progress_at field yet (that is Pax FND-011), so until it
    lands the age falls back to claimed_at, and a brief must say
    the age is "since claim" rather than "since last progress".
    Unclaimed jobs are never assigned to an owner here.
    """
    owners = []
    by_nick = {}
    jobs = (snapshot or {}).get("jobs") or []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        nick = job.get("claim") or ""
        if not nick:
            continue
        # Only claimed jobs count as owned. A done job must not
        # appear under an owner even if a stale claim field lingers
        # in a fixture dump — jobs.py deletes the claim on done.
        if job.get("status") != "claimed":
            continue
        if nick not in by_nick:
            by_nick[nick] = {"nick": nick, "jobs": []}
            owners.append(by_nick[nick])
        age = job.get("last_progress_at")
        if age is None:
            age = job.get("claimed_at")
        by_nick[nick]["jobs"].append({
            "id": job.get("id", ""),
            "title": job.get("title", ""),
            "last_progress_age": age,
        })
    return owners


def extract_blocked(snapshot):
    """BRF-005: every blocked job, with its reason verbatim.

    Returns a list of dicts, in jobs-dump order: {"id", "title",
    "reason"} where reason is the job record's "note" field
    character-for-character — never paraphrased, never trimmed,
    never summarised. A blocked job with no note gets reason "".
    Only jobs whose status is exactly "blocked" are returned.
    """
    blocked = []
    jobs = (snapshot or {}).get("jobs") or []
    for job in jobs:
        if not isinstance(job, dict):
            continue
        if job.get("status") != "blocked":
            continue
        blocked.append({
            "id": job.get("id", ""),
            "title": job.get("title", ""),
            "reason": job.get("note", "") or "",
        })
    return blocked


def extract_watch_items(snapshot):
    """BRF-022: open watchdog alerts, by reference.

    Returns a list of dicts, in snapshot order: {\"id\", \"summary\"}
    where id is the alert id Milo's watchdog produced and summary
    is its one-line summary, verbatim. Alerts with no id are
    skipped — a brief must never invent an alert id. This is
    the extractor the template brief's Watch items section
    already renders; it now has its own function and test.
    INT-004: a stored WDG-010 alert record carries no summary
    field — it carries explanation instead — so an alert with
    no summary falls back to the first line of its
    explanation, and only an alert with neither renders an
    empty summary. Without this, a brief built from stored
    alert records named each alert id with nothing after it.
    """
    items = []
    alerts = (snapshot or {}).get("alerts") or []
    for alert in alerts:
        if not isinstance(alert, dict):
            continue
        alert_id = alert.get("id", "")
        if not alert_id:
            continue
        summary = alert.get("summary", "") or ""
        if not isinstance(summary, str) or not summary.strip():
            explanation = alert.get("explanation", "") or ""
            if isinstance(explanation, str) and explanation.strip():
                summary = explanation.splitlines()[0].strip()
            else:
                summary = ""
        items.append({"id": alert_id, "summary": summary})
    return items


# STR-002: image blob pointers posted with send.py --img (and any
# --blob post whose file is an image). send.py posts the text plus
# "BLOB:<16 hex hash>:<name>:<chunk count>"; img_put validates the
# file by magic bytes, but a snapshot message carries only the
# pointer text, so this extractor can only prove the pointer names
# an image file, not that it arrived via --img rather than --blob.
_IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg", ".gif", ".webp")
_BLOB_POINTER_RE = re.compile(
    r"BLOB:([0-9a-fA-F]{16}):([A-Za-z0-9._-]+):(\d+)")


def extract_screenshot_refs(snapshot):
    """STR-002: screenshot digest for a brief record.

    Scans snapshot messages (dict entries or "nick: text" bus
    strings) for BLOB pointers naming an image file, in snapshot
    order. Returns a list of dicts, one per distinct image:
    {"nick", "file", "hash", "chunks", "ts", "caption"} where
    "ts" is the message dict's numeric ts or None for a bus
    string (a bus string carries no time, so no time is claimed
    for it), and "caption" is the message text with every BLOB
    pointer removed, whitespace-collapsed, possibly empty for a
    pointer-only post. A non-image pointer (a .txt, .pdf, or any
    other extension) is skipped: it is a file share, not a
    screenshot. A pointer whose filename has no image extension
    is skipped for the same reason, even if its bytes were an
    image: the digest lists what the pointer itself names.

    "Latest" rule: the same image posted twice (same hash and
    file) yields one ref, at its latest occurrence, so the SAM
    pass (STR-004/STR-005) is handed each screenshot once, not
    once per repost. This digest produces no verdict: whether a
    screenshot shows a working or broken build is the SAM
    pass's call, not this extractor's, and no verdict field is
    invented here. Returns [] for an empty or missing snapshot,
    never an error.
    """
    refs = []
    positions = {}
    position = 0
    for message in (snapshot or {}).get("messages") or []:
        nick, text = _message_parts(message)
        ts = None
        if isinstance(message, dict):
            raw_ts = message.get("ts")
            if isinstance(raw_ts, (int, float)) and not isinstance(
                    raw_ts, bool):
                ts = raw_ts
        for match in _BLOB_POINTER_RE.finditer(text or ""):
            position += 1
            file_name = match.group(2)
            lower = file_name.lower()
            if not any(lower.endswith(ext)
                       for ext in _IMAGE_EXTENSIONS):
                continue
            caption = " ".join(
                _BLOB_POINTER_RE.sub("", text or "").split())
            key = (match.group(1).lower(), file_name)
            ref = {"nick": nick, "file": file_name,
                   "hash": match.group(1).lower(),
                   "chunks": int(match.group(3)),
                   "ts": ts, "caption": caption}
            if key in positions:
                refs[positions[key]] = (position, ref)
            else:
                positions[key] = len(refs)
                refs.append((position, ref))
    refs.sort(key=lambda item: item[0])
    return [ref for _position, ref in refs]


def screenshot_digest_lines(refs):
    """STR-002: one plain line per screenshot ref, in ref order.

    Each line names the sender, the file, and the time in ET
    when the message carried one, else "time not reported" --
    never a guessed time -- plus the post's caption when it has
    one. The lines are not bullets, so the BRF-007 budget trim
    drops section bullets before it ever touches these lines,
    the same protection the OS-062/079/103/127 lines carry.
    Returns [] for no refs, so a brief without screenshots
    keeps its exact older shape.
    """
    lines = []
    for ref in refs or []:
        when = _format_brief_time(ref.get("ts"))
        line = (f"{ref.get('nick', '')} shared {ref.get('file', '')} "
                f"at {when if when else 'time not reported'}")
        caption = ref.get("caption", "")
        if isinstance(caption, str) and caption:
            line += f": {caption}"
        lines.append(line)
    return lines


def detect_new_nicks(snapshot):
    """BRF-029: nicks present in the room with no prior message.

    A nick counts as new when it appears in the snapshot's
    presence list but has authored none of the snapshot's
    messages (dict entries or "nick: text" bus strings). Presence
    order is kept, duplicates dropped, empty nicks ignored. A
    nick that only holds a job claim or a caps entry is still
    new — only a prior message counts as prior presence in the
    room, per the task wording. Returns [] for an empty or
    missing snapshot, never an error.
    """
    snapshot = snapshot or {}
    authors = set()
    for message in snapshot.get("messages") or []:
        nick, _text = _message_parts(message)
        if nick:
            authors.add(nick)
    presence = snapshot.get("presence") or []
    if isinstance(presence, dict):
        presence = list(presence.keys())
    new_nicks = []
    for nick in presence:
        if not isinstance(nick, str) or not nick:
            continue
        if nick in authors or nick in new_nicks:
            continue
        new_nicks.append(nick)
    return new_nicks


def offer_onjoin_brief(snapshot, room, now=None):
    """BRF-029: offer (never auto-generate) an on-join brief.

    For every nick from detect_new_nicks, returns one offer
    record: {"room", "nick", "kind": "onjoin", "status":
    "offered", "offered_at", "brief_generated": False,
    "brief_id": None}. The offer is the whole effect: this
    function composes no brief text, stores nothing, and posts
    nothing to the bus. A brief comes into being only when
    someone invokes generate_brief(kind="onjoin") for that nick
    afterwards — until then the offer record is the only trace,
    and no brief id exists to confuse with a generated brief.
    """
    import time as _time
    offered_at = int(_time.time() if now is None else now)
    clean_room = room or "main"
    return [{"room": clean_room,
             "nick": nick,
             "kind": "onjoin",
             "status": "offered",
             "offered_at": offered_at,
             "brief_generated": False,
             "brief_id": None}
            for nick in detect_new_nicks(snapshot)]


def extract_decisions(snapshot):
    """BRF-004: decisions from message markers, in snapshot order.

    Returns a list of dicts: {"kind", "text", "nick", "index"} where
    kind is "done", "blocked", or "decision", text is the marker
    remainder verbatim, nick is the sender ("" when unknown), and
    index is the message position in the snapshot. Messages with
    no marker are skipped, never reinterpreted. No Spark pass runs
    here (see module docstring); a future Spark pass may add
    records, but must never remove or rewrite a marker record.
    """
    decisions = []
    messages = (snapshot or {}).get("messages") or []
    for index, message in enumerate(messages):
        nick, text = _message_parts(message)
        match = _DECISION_RE.match(text or "")
        if not match:
            continue
        decisions.append({
            "kind": match.group(1).lower(),
            "text": match.group(2),
            "nick": nick,
            "index": index,
        })
    return decisions
