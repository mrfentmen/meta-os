"""intel/ingest.py — read-only snapshot of the relay for intel engines.

snapshot(room) returns one dict — {room, messages, jobs, presence,
caps} — assembled from four real sources and nothing else:

  messages  the bus list for the room, read with LRANGE paging
            exactly like digest.py (PAGE=1000), oldest first;
  jobs      the jobs.py queue index + job hashes, in the same field
            shape jobs.py list --json prints (FND-013);
  presence  relay_common.presence_list(): nicks with a live
            heartbeat key;
  caps      the mos capability registry (mos/capabilities.agents()).

Every engine (brief, watchdog, dashboard) reads through this one
function so there is exactly one place where raw relay state becomes
an intel-shaped snapshot. Read-only: snapshot never writes Redis,
never posts to the bus, and never invents a message, job, nick, or
capability that is not already there.

Absolute cursor reading (FND-015) lives here too, beside snapshot:
messages_from_cursor(room, after_id) reads the local store.py JSONL
for the room, whose entries carry stable ids ("<room>-<seq>") that
survive restarts — unlike bus-list offsets, which shift as the list
is trimmed. The cursor does NOT replace snapshot's bus-list read:
the JSONL store records only messages this participant sent
(store.py), so it can never stand in for the room's full history.
Engines that need the whole room read snapshot(); engines that need
to resume where they left off read the cursor.
"""

import json

import jobs
import relay_common as rc
import store
from mos import capabilities

PAGE = 1000  # LRANGE chunk size, same as digest.py

__all__ = ["snapshot", "PAGE", "store_messages", "messages_from_cursor"]


def _as_int(value):
    try:
        return int(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def _messages(room):
    """All messages on the room's bus list, oldest first, paged."""
    key = rc.bus_key(room)
    out = []
    start = 0
    while True:
        chunk = rc.bus_get(start, start + PAGE - 1, key=key)
        out.extend(chunk)
        if len(chunk) < PAGE:
            break
        start += PAGE
    return out


def _store_entries(room):
    """Raw JSONL entries for the room, oldest first, or [].

    A missing or unreadable store file is an empty store, not an
    error: rooms this participant never sent in have no file.
    """
    try:
        return store.open_store(room).entries()
    except Exception:  # noqa: BLE001 - an unreadable store is no store
        return []


def _render(entries):
    """Store entries as bus-shaped "nick: text" strings, in order."""
    out = []
    for e in entries:
        nick = e.get("nick")
        text = e.get("text")
        if nick and isinstance(text, str):
            out.append(f"{nick}: {text}")
    return out


def store_messages(room):
    """This participant's sent messages for the room, oldest first.

    NOT the room's full history (see module docstring): the JSONL
    store records sent messages only. [] when there is no store file
    or it holds no entries.
    """
    return _render(_store_entries(room))


def messages_from_cursor(room, after_id=None):
    """(messages, cursor) reading the room's JSONL store from a cursor.

    Absolute cursor reading (FND-015): entries carry stable store
    ids ("<room>-<seq>"), so a caller that keeps the returned cursor
    and passes it back later gets exactly the entries appended since
    — no re-reads, no duplicates — even across restarts. after_id
    None reads from the start. The returned cursor is the last entry
    id read, or the input cursor when nothing new arrived. An
    unknown after_id reads from the start rather than failing: the
    store file is append-only, so an unknown id means the file was
    replaced out from under the reader, and losing the whole history
    would be worse than re-reading it.
    """
    entries = _store_entries(room)
    if after_id is not None:
        idx = next((i for i, e in enumerate(entries)
                    if e.get("id") == after_id), None)
        if idx is not None:
            entries = entries[idx + 1:]
    if not entries:
        return [], after_id
    return _render(entries), entries[-1].get("id")


def _jobs():
    """Queue rows in the jobs.py list --json field shape (FND-013)."""
    try:
        ids = json.loads(rc.api_get(
            f"zrange/{jobs._index_key()}/0/-1"))["result"] or []
    except Exception:  # noqa: BLE001 - an unreadable index is no jobs
        return []
    rows = []
    for jid in ids:
        h = jobs._hgetall(jobs._job_key(jid))
        if not h:
            continue
        rows.append({
            "id": jid,
            "title": h.get("title", ""),
            "status": h.get("status", "?"),
            "claim": h.get("claim") or None,
            "files": h.get("files", ""),
            "deps": h.get("deps", ""),
            "attempts": _as_int(h.get("attempts", 0)),
            "lease_until": _as_int(h.get("lease_until")),
            "last_progress_at": _as_int(h.get("last_progress_at")),
        })
    return rows


def snapshot(room):
    """Return {room, messages, jobs, presence, caps} for `room`.

    `room` is cleaned exactly like every other module cleans it; the
    empty room is "main". Presence and caps are global (they are not
    per-room in the relay), jobs are global too — the queue is one
    index — while messages are the room's own bus list.
    """
    clean = rc.clean_room(room) or "main"
    return {
        "room": clean,
        "messages": _messages(room),
        "jobs": _jobs(),
        "presence": rc.presence_list(),
        "caps": capabilities.agents(),
    }
