# Failure drill — `crates/os-misc`

B213 deliverable. What breaks first when its inputs stop arriving,
written from the code. A drill another agent can run without a brain
dump.

## Run the drill

```
cargo test -p os-misc -j1
```

The three integration files are the drill's assertions:

- `crates/os-misc/tests/error_paths.rs` — refusals and best-effort paths.
- `crates/os-misc/tests/edge_cases.rs` — empty/max/duplicate/out-of-order.
- `crates/os-misc/tests/gap_close.rs` — the transport seam.

Target one drill by name, e.g.:

```
cargo test -p os-misc -j1 --test error_paths poll_surfaces_transport_failure
```

## D1 — the bus stops answering

Input: `BusTransport::bus_get` starts returning `Err`.

1. `poll_one` (`b24/poll.rs:39-41`) returns
   `Err("poll failed: <e>")`. It does **not** advance the seen offset,
   record anything, or heartbeat.
2. `watch_once` (`b24/watch.rs:39-41`) returns the same error on the
   first target and stops; later targets are not polled that cycle.
3. Nothing is retried inside the crate: there is no loop to back off.
   The caller's loop (not carried, gap G2/G3) is where retry lives.

Observable: the call returns `Err`; the seen file is unchanged.

## D2 — the bus answers but the heartbeat or receipt fails

Input: `bus_get` is OK; `presence_beat` / `mark_seen` return `Err`.

1. `poll_one` continues (`:43-47`, `:74-80`). Each failure is pushed to
   `PollOutcome.warnings` with the exact prefixes
   `presence heartbeat failed:` and `read-receipt write failed:`.
2. Messages are still recorded and the offset still advances. A failed
   heartbeat cannot lose a message.

Observable: `warnings` is non-empty, `new_from_others` is populated.

## D3 — the seen file cannot be written

Input: the seen path's directory disappears.

1. The bus read still happens; messages are still returned and stored.
2. `fs::write` fails; `poll_one` pushes `seen write failed: <e>`
   (`b24/poll.rs:74-77`).
3. Consequence: the next poll re-reads the old offset and repeats the
   same messages. The store has no dedupe (finding F2), so duplicates
   accumulate.

Observable: warning present; re-running the same poll grows the store.

## D4 — the store file cannot be written

Input: the store directory is removed or read-only.

1. `poll_one` and `watch_once` **ignore** the store append result
   (`let _ = store.append(...)`, `poll.rs:57-64`, `watch.rs:55-62`).
   The poll still succeeds; incoming lines are not persisted, so
   `forward`/`saved` by id cannot find them later.
2. A direct `append` or `edit` returns `Err` (`b24/store.rs:105-127`,
   `:129-158`); `edit` wraps a write failure as
   `"store write failed: <e>"`.

Observable: direct append/edit errors; poll keeps returning OK.

## D5 — a stored line is torn or unparseable

Input: a partial JSON line at the end of `messages.jsonl`.

1. `load` skips it (`b24/store.rs:160-184`): blank and invalid lines are
   dropped, entries with an empty id are dropped.
2. No warning is surfaced and no repair is attempted; the good records
   before and after survive.
3. Consequence: a torn line silently loses one record, not the file.

Observable: `entries()` length is the number of whole records.

## D6 — the pack manifest is wrong

Input: a manifest missing keys or carrying a bad enum.

1. `validate_pack` returns early when any required key is missing
   (`b27/validate.rs:54-63`); otherwise it appends every rule failure in
   check order.
2. An empty vec is the only "valid" answer. There is no panic path for
   bad JSON shape: a non-object returns one error string.

Observable: the exact error list; see `os-misc-records.md` §11.

## D7 — the PAR clock stops receiving ticks

Input: `tick` is not called.

1. Nothing happens. The clock is pure: no timer, no thread, no file
   watcher (`b27/par_clock.rs:197-245`).
2. If ticks resume with a large `now`, both the due and unaccounted
   events fire in that one call, each once, because the ledger keys are
   derived from `due_at`.
3. Consequence: a stopped clock is silent; a late clock is loud. The
   operator can miss the window but cannot miss the escalation once the
   clock runs again.

Observable: `tick` at `now >= due + grace` returns two events; a second
tick at the same/later time returns none.

## D8 — webhook / time capsule inputs stop

Input: no URL, no due items, or no sweep loop.

1. `resolve_url` refuses a missing/empty env var or a non-http(s) value
   (`b26/webhook.rs:11-27`); nothing is sent.
2. `is_due` / `recur_next` compute one item's fate
   (`b26/timecapsule.rs:19-26`); no sweep loop exists, so a stopped
   caller means nothing is popped and nothing is requeued (gap G17/G18).

Observable: refusal string from `resolve_url`; pure helpers still
return their computed values.
