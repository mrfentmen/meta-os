# Record — crate `os-misc`, from the code

Scope: `crates/os-misc` on `main` @ `6d8d54e` (2026-11-02). Every claim
cites a file and line range in the crate. This crate is a shared port
home for batches B24–B30; each batch keeps its own subtree.

Status words: **LIVE** = code exists and a test exercises it.
**UNWIRED** = code exists but no production caller in this repository.

## What it is

| Subtree | What it is | State |
|---|---|---|
| `b24` | Bus messaging core: poll, send parsing, presence, local store, watch, nick watch | LIVE in tests; UNWIRED from a binary |
| `b25` | Bus messaging extras: announce, clipboard, edits, forward, paste, saved | LIVE in tests; UNWIRED |
| `b26` | Bus bridges, digest, admin rules, health text, time capsule, webhook shapes | LIVE in tests; UNWIRED |
| `b27` | World-pack validator + FDNY PAR clock pure core | LIVE; called by `parity-tests` |
| `b28` | OS docs/roles/root docs — CARRIED (inventory only) | CARRIED |
| `b29` | Crew dirs + demo/submission assets — CARRIED | CARRIED |
| `b30` | Lane plans — CARRIED | CARRIED |

`src/lib.rs:1-11` declares the seven subtrees. There is no `main.rs`,
no `[[bin]]`, and no production caller of any module outside the crate
and `parity-tests` (`Cargo.toml:1-8`).

## b24 — bus messaging core

### Transport seam

- `MAX_TEXT = 2000` (`b24/transport.rs:11`), the Python
  `relay_common.MAX_TEXT` value.
- `BusTransport` (`b24/transport.rs:14-31`) has one required method
  `bus_get` and three best-effort defaults: `presence_beat`, `mark_seen`,
  `own_prefixes`. There is **no write/post method**; sending is not
  carried (see gaps G1).
- `room_for_key` / `bus_key` (`b24/transport.rs:35-52`) map
  `muse-bus:room:<name>` both ways.

### Store

- `MessageStore` (`b24/store.rs:86-158`) is an append-only JSONL log.
- `store_path` (`:46-51`): `messages.jsonl` for the default room,
  `messages-<room>.jsonl` otherwise.
- `append` (`:105-127`) refuses an empty nick (`"nick is empty"`) and
  empty text (`"message text is empty"`); ids are `<counter>` or
  `<room>-<counter>` and continue from the highest on disk
  (`next_seq`, `:69-83`).
- `edit` (`:129-158`) refuses empty text, an unknown id, and a nick that
  is not the original author; it appends the displaced text to
  `edit_history` and sets `edited`.
- `load` (`:160-184`) skips blank and unparseable lines; entries with an
  empty id are dropped. `save` (`:186-199`) writes a temp file and
  renames.

### Poll and watch

- `poll_one` (`b24/poll.rs:32-91`) reads the seen offset (missing or
  garbage = 0, `:24-29`), calls `bus_get`, heartbeats, filters the
  caller's own prefixes, records incoming lines, advances and persists
  seen, and writes a read receipt. A transport error becomes
  `"poll failed: <e>"`; heartbeat, store, seen-write and receipt
  failures become warnings and never abort the poll (`:45-80`).
- `watch_once` (`b24/watch.rs:32-89`) repeats that per target, but only
  once; the interval loop and sleep are not carried. A nonpositive
  interval is refused by `validate_interval` (`:24-30`).

### Presence and nick watch

- `render_presence` (`b24/presence.rs:10-35`): `NO_ONE_ONLINE` when
  empty, otherwise one line per nick with `[holder]` then `(status)`.
- `nick_joined` (`b24/watch_nick.rs:8-24`) matches the watched nick or a
  display name, case-insensitively. `flag_name` (`:27-35`) and
  `render_outcome` (`:37-45`) produce the `.NAME_reported[_room]` file
  name and `NAME_JOINED` / `NAME_NOT_JOINED` line.

## b25 — messaging extras

- `announce`: key (`b25/announce.rs:7-9`), filter with skipped count
  (`:13-26`), the mod/claim gate with two exact refusal messages
  (`:29-46`), and the client-side-only warning (`:48`). The Redis
  get/set is not carried.
- `clipboard`: ordered read/write command tables
  (`b25/clipboard.rs:7-25`), `ClipboardError`, and `no_tool_msg`
  (`:37-45`). No command is executed here.
- `edits`: `parse_edit_text` (`b25/edits.rs:9-25`) accepts
  `EDIT <id> <text>` with the Python id character class;
  `validate_edit_text` (`:27-40`) refuses empty and over-2000-byte text;
  `render_kind` (`:42-51`) classifies a line as edit or plain.
- `forward`: `parse_fwd_text` (`b25/forward.rs:4-33`) parses
  `FWD <id> <#room>`; `via_parts` (`:35-45`) parses
  `"<orig> (via <fwd>): <body>"`; `forward_text` (`:47-57`) collapses a
  single hop when the entry's nick is its own forwarder.
- `paste`: `verify_clip` (`b25/paste.rs:8-18`) compares the first 16 hex
  chars of SHA-256; `short_sha256_hex` (`:20-98`) is a dependency-free
  FIPS 180-4 implementation. Chunk reassembly is not carried.
- `saved`: `SAVE_CAP = 200` (`b25/saved.rs:7`), key, room label,
  `SavedEntry`, render and room filter (`:10-46`). Save/unsave I/O is not
  carried.

## b26 — bridges, digest, admin

- `admin`: `MAX_DISPLAY = 32`; `validate_display` (`b26/admin.rs:9-22`)
  refuses empty, over-32, `:` and newlines; `validate_rekey_digest`
  (`:24-32`) requires 64 hex; `canonical_envelope` (`:34-38`) renders
  the HMAC input shape. Secret handling, HMAC signing and the CLI are not
  carried.
- `digest`: `PAGE = 1000`, `TOP_N = 5`; `talker_stats`
  (`b26/digest.rs:9-23`) counts lines and returns the top five
  deterministic `(count desc, nick asc)`; `validate_hours` refuses
  nonpositive; `fmt_hour` renders `HH:00` or `n/a`.
- `export`: `ExportEntry` (`b26/export.rs:7-12`), `fmt_time`
  (`:14-23`, a `ts:<n>` placeholder, not local time), `write_md`
  (`:25-33`) and `write_json_line` (`:35-50`). Store streaming is not
  carried.
- `health`: `uptime_str` (`b26/health.rs:7-20`) renders
  `{d}d{h}h{m}m` omitting zero high units; `health_text` (`:22-26`)
  renders `HEALTH cpu=..% mem=..% disk=..% up=.. load=..`. Reading the
  stats is not carried.
- `timecapsule`: constants and helpers only —
  `TIMECAPSULE_KEY`, `REQUEUE_DELAY_SECS = 60`, interval validation,
  `is_due` (`score <= now`), `recur_next` (`now + every`)
  (`b26/timecapsule.rs:8-26`). The Redis pop/requeue sweep is not
  carried.
- `webhook`: `MAX_ATTEMPTS = 5`, `BACKOFFS = [1,2,4,8]`;
  `resolve_url` (`b26/webhook.rs:11-27`) accepts a literal http(s) URL or
  reads a named env var and refuses a missing/empty/non-URL value;
  interval validation; `payload_for` (`:37-49`). Delivery and offset
  handling are not carried.

## b27 — world packs

- `validate_pack` (`b27/validate.rs:48-313`) returns a list of error
  strings (empty = valid): required keys, token shapes, status/severity/
  privacy/urgency enums, nonempty watchers/agents/alerts/firstboot/
  urgency, unique watcher ids, agent nicks, alert kinds, firstboot
  fields and urgency ranks, `crosses_bus` requires `privacy:"summary"`,
  unknown `serves` targets, and cross-world send/never-carries rules.
- `pack_dir_matches` (`:315-322`) refuses a pack name that differs from
  its directory.
- `par_clock` (`b27/par_clock.rs`) is the pure FDNY PAR core:
  `validated_crew_id` (`:63-72`) refuses empty/whitespace; `enter_crew`
  refuses a second entry; `complete_par`/`exit_crew` refuse a crew not
  inside; `tick` (`:197-245`) raises `par-check-due` once per due
  timestamp and `crew-unaccounted` once per due+grace, both deduped in
  the ledger; `render_alert` (`:249-251`) renders
  `ALERT:<id> <severity> <kind>`.

## b28–b30 — carried, not ported

- `b28` inventories 16 docs/role files (`b28/mod.rs:9-26`).
- `b29` inventories 22 crew/demo/submission assets (`b29/mod.rs:8-30`).
- `b30` inventories 12 lane-plan files (`b30/mod.rs:7-20`).
- Each exposes `is_logic_free() -> true`. No file is opened to verify
  that claim (see F6).

## Findings — docs and comments that disagree with the code

1. **"byte-for-byte" is too strong for `parse_when`.** `b24/mod.rs:8-9`
   claims the pure logic matches Python byte-for-byte, but
   `b24/send.rs:105-124` treats a naive ISO timestamp as UTC while the
   Python uses local time (`os/send.py:122-142`). The module comment
   documents the approximation; the subtree claim should be narrowed.
2. **No dedupe in the store.** `b24/poll.rs:58-59` says duplicates
   collapse in the store layer; `b24/store.rs:105-127` appends every
   call unconditionally. Re-polling the same line records it twice.
3. **Documented requeue does not exist.** `b26/timecapsule.rs:1-6`
   describes failed pushes re-queuing at +60s, but the module has only
   `REQUEUE_DELAY_SECS` (`:9`) and no push/requeue code.
4. **Documented webhook delivery does not exist.**
   `b26/webhook.rs:1-6` describes retries and offset behaviour; the
   module contains constants, URL resolution, interval validation and
   payload shaping only.
5. **Dead helper kept alive by an allow.**
   `b27/par_clock.rs:252-255` has `_assert_no_mutation_hint` behind
   `#[allow(dead_code)]`; it asserts nothing and has no caller.
6. **`is_logic_free` cannot answer its own question.**
   `b28/mod.rs:29-32`, `b29/mod.rs:33-36`, `b30/mod.rs:22-25` return a
   constant `true`; the carried-file claim is an inventory fact, not
   something the function checks.
7. **Export time is a placeholder.** `b26/export.rs:1-3` documents
   `## <nick> (<time>)`, but `fmt_time` (`:14-23`) emits `ts:<n>` or
   `unknown time`, not a formatted wall-clock time.

Test inventory at this pass: 23 inline `#[cfg(test)]` modules and
47 inline `#[test]` functions across `src/`, plus the three integration
files added under `crates/os-misc/tests/` (B206, B207, B215).
