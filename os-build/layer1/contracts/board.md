# Contract — `board`

Status: **RUNS** — `services/tests/t91_board.goose` (54 checks), on the host shim. Not started
by a supervisor; nothing starts a service yet.

## What it is

Rooms and an append-only post log, with ids that only go up. This is the client half of the
agent board: the thing a dashboard tile and a task list both read.

## The three choices

1. **Posts are immutable.** No edit, no delete. A board whose history can change is a board
   where a fetch is not a record of what was said.
2. **A full log refuses; it does not drop.** A ring that silently overwrote the oldest post
   would make `fetch since 1` return a different answer at different times. `E_NO_SPACE` is
   the honest answer, and `bd_refused_total()` counts them.
3. **Ids are the cursor.** `fetch(room, since_id)` returns everything newer than the id the
   client already has, so a reader that lost its place catches up without timestamps or a
   server-side mark.

## API

| function | returns | notes |
|---|---|---|
| `bd_init()` | — | four empty room slots, ids from 1 |
| `bd_room_add(name)` | `(id, code)` | ≤ 15 bytes, printable, no comma, unique |
| `bd_post(room, text, now_ms)` | `(id, code)` | ≤ 95 bytes, no comma, no newline |
| `bd_post_count(room)` / `bd_last_id(room)` | count / id | 0 for an unknown room |
| `bd_unread(room, since_id)` | count | what a badge shows |
| `bd_fetch(room, since_id, out)` | `(count, code)` | the posts newer than the cursor, in id order |
| `bd_export(out)` / `bd_import(data)` | bytes / code | `R,<id>,<name>` and `P,<id>,<room>,<created>,<text>` |
| `bd_post_total()` / `bd_refused_total()` | counters | accepted and refused, for the dashboard |

## Commas, and why they are refused at write time

The export format is line-oriented and comma-separated. A comma in a room name or a post
would make that format ambiguous, and the ambiguity would be resolved differently by every
reader. Both are refused at write time instead, so a line is always five fields. Newlines
are refused for the same reason against the line.

## Failure modes, all driven by the test

- **Unknown room** — `E_NOTFOUND` from post, count, fetch and unread.
- **Duplicate room name** — `E_EXISTS`.
- **Fifth room** — `E_NO_SPACE`; the fourth still works.
- **Full log** — `E_NO_SPACE` on post 25 remains refused, the 24 posts are intact, and the
  refusal count moves.
- **Empty or over-long text** — refused whole; nothing is truncated into the log.
- **Bad import** — a line with a missing comma, a non-numeric id, a zero id, a control byte
  or an unknown kind letter fails the import and applies **nothing** (`E_CORRUPT`). The
  staging arrays are the reason: the parse builds a candidate log and commits at the end.
- **Round trip** — export then import reproduces rooms, posts, ids, cursors and the next-id
  counter, so a restarted client cannot reuse an id.

## Restart semantics

The log is memory unless exported. `bd_export`/`bd_import` are the whole persistence story,
and the import is atomic, so a truncated file leaves the previous log rather than half of a
new one. **This is the one face service where the restart path is proven** — the round-trip
test runs it — but nothing calls export on a timer yet.

## Limits

`BD_MAX_ROOMS` 4, `BD_MAX_POSTS` 24 (whole log, not per room), `BD_ROOM_NAME_MAX` 16,
`BD_POST_MAX` 96. Storage is 4 × 32 + 24 × ~128 ≈ 3.2 KiB, measured by `size_audit.py`.
