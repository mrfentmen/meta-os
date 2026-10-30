# Hana source map — FND-033

What each existing text source gives a brief, and the exact command or
function that produces it. Checked against the code in this repo on
2026-10-26. A brief never invents a fact: if a source below cannot
supply a section, the brief says so instead of filling it in.

Morning brief sections (BRF-001): Decisions, In flight, Owners,
Blocked and why, Watch items.

## 1. digest.py output — room activity volume

- Exact command: `python3 digest.py --room <room> --hours 24 --json`
- Exact function: `digest_room(room, hours)` in `digest.py`
- What it gives: `bus_messages` (count from the bus list, paged
  LRANGE, PAGE=1000), `top_talkers` (top 5 nicks by count),
  `recent_messages` and `busiest_hour` from the local store.
- Feeds brief section: Watch items (how busy the room was), and it
  helps size the source window.
- Honest limit: bus list items are plain `<nick>: <text>` with no
  timestamps. Anything time-based comes from the local store. A room
  with no local store data reports those fields as null, not as
  invented numbers.

## 2. store.py JSONL — timestamped message text

- Exact function: `store.open_store(room).entries()` in `store.py`
- Files: `messages.jsonl` (main room) and `messages-<room>.jsonl`
  (other rooms), one JSON object per line:
  `id`, `room`, `nick`, `text`, `ts`, `edited`, `edit_history`.
- Feeds brief sections: Decisions (DONE:/BLOCKED:/decision markers
  found in the text), In flight (progress notes in the text), and
  the source window itself (the `ts` values are the only clock the
  brief can trust for bus text).
- Honest limit: the store records messages this participant sent
  (via `send.py`). It is NOT a full transcript of the room. A brief
  built from the store alone must say its window is partial. The
  full room text lives on the bus list, read by `digest.py`, but
  without timestamps.

## 3. jobs list — job state, owners, blocked reasons

- Exact commands today: `python3 jobs.py list --status all` and
  `python3 jobs.py show <id>`
- Exact functions: `cmd_list` / `cmd_show` / `job_get` in `jobs.py`
- What `show` prints per job: `title`, `status`, `room`, `claim`,
  `claim_host`, `claimed_at`, `lease_until`, `result_commit`,
  `note`, `created_by`, `created_at`, plus the spec text.
- Feeds brief sections: In flight (claimed and open jobs), Owners
  (claim nick per job), Blocked and why (`note` holds the blocked
  reason verbatim — `cmd_blocked` stores `args.reason` as `note`,
  and the brief must quote it, never paraphrase it away).
- Honest limit, stated plainly: `jobs.py list --json` does NOT exist
  in this tree yet. That is Pax's FND-013. Until it lands, the brief
  extractor reads `show` output (or calls `job_get` directly) — it
  must not claim a `--json` dump exists. The jobs fields `files`,
  `deps`, and `attempts/max_attempts` also do not exist yet
  (Pax FND-008/009/010); the brief cannot report them until then.

## 4. presence.py — who is online right now

- Exact command: `python3 presence.py`
- Exact functions: `relay_common.presence_list()`,
  `relay_common.status_get_many(nicks)`,
  `relay_common.nick_holders(nicks)`, called from `main()` in
  `presence.py`
- What it gives: one nick per line, with a status in parentheses
  (for example `milo (heads down)`) and a holding instance in
  brackets when a nick is reserved. Prints `NO_ONE_ONLINE` when
  nobody has a live heartbeat.
- Feeds brief section: Owners (who is around to ask, and what
  status they set).
- Honest limit: a heartbeat means activity in the last ~2 minutes.
  Presence is not a promise that someone is free to take work.

## 5. mos capabilities — who can do what, and who is loaded

- Exact functions: `mos/capabilities.py: agents()`,
  `mos/capabilities.py: get(nick)`,
  `mos/capabilities.py: find_for(requirements)`,
  `mos/capabilities.py: active_claims(nick)`
- What it gives: per-nick capability record (`caps`, `roles`,
  `max_jobs`, `info`, `updated`), the list of nicks whose caps
  cover a requirement and who still have capacity, and how many
  claimed jobs a nick currently holds.
- Feeds brief sections: Owners (capability + load per owner),
  In flight (claimed-job counts per owner).
- Honest limit: records go stale after 15 minutes
  (`STALE_AFTER` in `mos/capabilities.py`, pruned by
  `prune_stale()`). A brief must not present a stale capability
  record as current.

## What is still missing (not a source yet)

- `intel/ingest.py` snapshot (Pax FND-014) will unify sources
  1–5 into one `{messages, jobs, presence, caps}` dict. This map
  is the pre-snapshot truth: the brief extractor reads the five
  sources above directly until the snapshot lands.
- No Spark call is needed to build this map, and none was used.
  The Spark transport question (GOV-001, real transport only,
  no FakeTransport) does not block FND-033.

## Status

FND-033: done, code-inspected against the five source files above.
No bus post was made. No secret appears in this file.
