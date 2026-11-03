# Contract — `notify`

Status: **RUNS** — `services/tests/t95_notify.goose` (75 checks), on the host shim. Not started
by a supervisor; nothing starts a service yet.

## What it is

The top-bar feed: one place for the sentences the machine has to say to the user — a board
post arrived, an update is available, a receipt landed, a service degraded. It does not draw
anything; it hands lines to whoever draws the bar.

## The four rules

1. **A duplicate is one notification.** Identical `(source, text)` inside `NT_DEDUPE_MS`
   (3000 ms) returns the id that is already on screen and the code `NT_DUPLICATE` (9101, above
   the error range), so a caller can tell "shown" from "already shown". The window is
   **inclusive at 3000 ms and exclusive at 3001**: a retry is the same event, an event a minute
   later is a new one.
2. **A dismissal is a record, not a deletion.** `nt_dismiss` frees the slot by compacting the
   feed (a feed full of closed items must not become a feed that can never show anything
   again) and appends `(id, severity, when)` to an 8-slot ring whose *total* is unbounded. After
   nine dismissals the first is out of the ring and still counted in `nt_dismissal_total`.
3. **Refusal is counted.** At `NT_MAX` (12) a new notification is refused with `E_NO_SPACE`
   and `nt_refusal_total` moves. Nothing is displaced: silently dropping the oldest is how a
   feed loses the one message that mattered.
4. **The dot is derived.** `nt_worst()` is computed from the notes on screen, so it cannot
   disagree with them: dismiss the only error and the dot falls back to the highest remaining
   severity, or to 0 when the feed is empty.

## API

| function | returns | notes |
|---|---|---|
| `nt_init()` | — | empty feed, ids from 1, counters zero |
| `nt_post(source, sev, text, now_ms)` | `(id, code)` | shape → duplicate → capacity, in that order |
| `nt_dismiss(id, now_ms)` | code | `E_NOTFOUND` for an unknown id; frees the slot, logs the record |
| `nt_count()` | count | items on screen |
| `nt_id_at` / `nt_sev_at` / `nt_text_at` / `nt_source_at` / `nt_when_at` | entry fields | array order is age order, oldest first |
| `nt_unread(since_id)` | count | "newer than the id the bar last showed" |
| `nt_worst()` | severity | the dot |
| `nt_fetch(since_id, out)` | `(lines, code)` | `"<id> <sev> <text>\n"` per note, newest last |
| `nt_refusal_total` / `nt_duplicate_total` / `nt_dismissal_total` | counters | one per outcome, so a log can say *why* |
| `nt_dismissal_at` / `nt_dismissal_sev_at` / `nt_dismissal_when_at` | ring entry | 8 slots, oldest overwritten |

Severities are `SEV_INFO` 1, `SEV_WARN` 2, `SEV_ERROR` 3. Anything else is `E_INVAL` — not
clamped, because a severity the bar cannot draw is a caller bug and clamping it to "info" would
hide the message that mattered.

## Validation at the post

`source` 1..15 printable bytes (`NT_SRC_MAX` 16 including the terminator slot), `text` 1..95
printable bytes (`NT_TEXT_MAX` 96). A newline is a control byte and is refused: one note is one
line on the bar, and a producer that sends two lines is writing a paragraph, not a notification.

## What it is not

- **Not a log.** No persistence, no priority policy that lets an error jump the queue. The
  honest answer at capacity is "refused, and here is the count".
- **Not a transport.** It does not write to the screen and does not know the session; the bar
  reads `nt_fetch` (or walks the accessors) and draws.
- **Not an authority.** It cannot call back into the services that post to it (its matrix row is
  `log` and `time` only), so a producer cannot make the bar lie about its own event.

## Failure modes, all driven by the test

- **Retry storm** — same sentence inside the window is `NT_DUPLICATE`, feed unchanged.
- **Full feed** — 13th is `E_NO_SPACE`, counted, nothing displaced.
- **Dismiss an unknown id** — `E_NOTFOUND`, no record written.
- **Dismiss the only error** — the dot falls back to the next severity.
- **Bad severity / empty or overlong text / control byte** — `E_INVAL` or `E_NOROOM`.
- **Restart** — `nt_init` forgets the feed, the ring and the counters; ids start at 1 again.

## Restart semantics

Everything is memory. Dismissals are a record *within the process*: a supervisor restart loses
the log of what the user closed, which is stated here rather than implied. Nothing re-posts the
events either — the feed after a restart is empty until a producer speaks again.

## Limits

`NT_MAX` 12, `NT_TEXT_MAX` 96 (95 usable), `NT_SRC_MAX` 16 (15 usable), `NT_DEDUPE_MS` 3000,
`NT_LOG_MAX` 8 ring slots. Storage is measured by `size_audit.py`; the numbers above are the
bounds `t95` drives to their edges.
