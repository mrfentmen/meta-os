# board — rooms, and a post log that only goes forward

Status: **RUNS** — `tests/t91_board` passes in the native host corpus
(`run_native.sh t91_board`, measured 2026-11-02: `RUNS=1 FAILS=0`), and the
program typechecks under `os-build/layer1/check_services.sh`. Layer 5, face
service 6.

## What it is

Rooms and an append-only post log, with ids that only go up. Three choices carry
it:

1. **Posts are immutable.** There is no edit and no delete. A board whose history
   can change is a board where a fetch is not a record of what was said.
2. **A full log refuses; it does not drop.** A ring that silently overwrote the
   oldest post would make `bd_fetch(room, since 1)` return a different answer at
   different times. `E_NO_SPACE` is the honest answer, and
   `bd_refused_total` counts it.
3. **Ids are the cursor.** `bd_fetch(room, since_id)` returns everything newer
   than the id the client already has, so a reader that lost its place catches up
   without timestamps and without a server-side mark. `bd_unread` is the same
   comparison as a count.

## Persistence

`bd_export` writes comma-separated lines and `bd_import` parses them atomically: a
bad line applies nothing, the same all-or-nothing rule the settings store uses.
Commas and newlines are refused in room names and post text **at write time**, so
the format cannot be made ambiguous by content — the export never has to quote or
escape, because the service never accepted a value that would need it.

## Surface

| Function | Answers |
|---|---|
| `bd_room_add`, `bd_room_find`, `bd_room_find_name` | rooms |
| `bd_room_count`, `bd_room_name_at`, `bd_room_id_at` | the room list |
| `bd_post` | append a post; returns its id |
| `bd_fetch` | everything after a `since_id`, into a caller buffer |
| `bd_post_count`, `bd_last_id`, `bd_unread` | the log's state per room |
| `bd_export` / `bd_import` | the file form, atomic on import |
| `bd_post_total`, `bd_refused_total` | how much was accepted, how much refused |

## Where the proof is

`services/tests/t91_board.goose` — immutability, the full-log refusal, and a
round trip through export and import.
