# console — Round 11 record

Source: `services/console/console.goose`, `services/console/esc.goose`,
`services/console/entry.goose` · Test: `services/tests/t110_console_r11.goose` · Status: RUNS
(reached by `tests/t49_bootlog`, 23 checks)

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `CONSOLE_LINE_MAX` | `256` | `console.goose` | driven by `t110` | 255 `insert_byte` calls succeed, the 256th returns false; the load loop reproduces the same 255/65 split over 320 keys |
| `HISTORY_SLOTS` | `8` | `console.goose` | driven by `t110` | `history_slots()` is read back from the ring and equals the constant; a completed line is pushed and recalled |
| `ESC_PARAMS_MAX` | `4` | `esc.goose` | driven by `t110` | `ESC [ 1;2;3;4;5;6H` parses as a cursor-position sequence with `p1=1, p2=2`; the fifth and sixth parameters are dropped rather than overwriting the last slot |

`LIMITS.md` maps the first two to `t80_limit_drivers2` and `t103_limits_rest`, and
`ESC_PARAMS_MAX` to `t80_limit_drivers2`; this driver re-drives all three at their edge, so
the mapping is not merely a name match.

## 2. Refusals — PROVEN

The console returns booleans, not codes: there is no `E_*` in this service.

| refusal | return | the test assertion that expects it |
|---|---|---|
| the line is full | `insert_byte` → false | "the byte past the line cap is refused" |
| an unknown escape sequence | `SEQ_UNKNOWN` in `Seq.kind` | "an unsupported CSI is reported, not swallowed" |
| a fifth parameter | dropped, `Seq` keeps the first four | "the first two parameters survive the overflow" |
| a non-printable control byte | swallowed by `handle_key`, not inserted | "a bare control byte is not printable" |

Not asserted: `move_left` at column 0 and `move_right` at end-of-line. The driver exercises
both moves mid-line but never places the cursor at either edge, so those two false returns
remain a gap rather than a proven refusal.

## 3. Restart — NAMED GAP

The line buffer, cursor and the eight-slot history are static memory in the service
process. The supervisor restarts the unit on exit (`services/supervisor/supervisor.goose`,
restart policy), and after that restart the buffer is empty and the history is gone. No
restart was run for this record, so continuity is not claimed: **the loss is the whole
session's edit history, and it is accepted because the console is a view, not a store.**

## 4. Contract — PROVEN

Imports: `common.sys.sys`, `common.ring.ring`, `common.err.err`. No service is imported and
no service function is called; the console reaches the kernel through `sys_write_console`,
`sys_read_key`, `sys_yield`.

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | bootlog | none in code | declared: `cm_set(SVC_CONSOLE, ... SVC_BOOTLOG ...)` — DORMANT |
| out | log | none in code | declared: `cm_set(SVC_CONSOLE, ... SVC_LOG ...)` — DORMANT |
| in | bootlog | none in code | declared: bootlog's row includes `SVC_CONSOLE` — DORMANT |
| out | kernel | `sys_write_console`, `sys_read_key`, `sys_yield` | not a matrix edge: the matrix is service-to-service |

`FINDING: console's matrix row declares edges to bootlog and log that the code does not
make.` Both are dormant, which the matrix's own comments allow for the face layer, but this
row is not marked as such. Room 1 should either mark it dormant or drop the bits.

## 5. Load — NAMED GAP

The load loop inserts 320 bytes (ten times a 32-key batch) into one line, which crosses
`CONSOLE_LINE_MAX` once: 255 accepted, 65 refused. The run that produces the numbers is the
coordinator's; this record carries the marker, not a guess.

RUNS pass=24 fail=0 · `LOAD console ops=320 ok=255 refused=65`

## 6. README truth pass — PROVEN

`services/console/README.md` rewritten; four stale statements, plus one sentence that was
checked and re-sourced:

- **"Status: WRITTEN. Not COMPILED"** — the console is RUNS: `tests/t49_bootlog` reaches it
  with 23 checks, and the corpus typechecks it through `root_console.goose`. Now says RUNS.
- **"Pressing Enter ... prints `[console] line stored; no shell to run it (B-L1-87)`"** —
  true, and the README did not say where it came from. The string is printed by
  `entry.goose` after `handle_key` reports a completed line, not by `console.goose` itself.
  The README now names the file, so the next reader does not go looking for it in the
  module and conclude the quote is invented.
- **"Escape handling is three sequences (`ESC [ A/B/C/D`)"** — that is the inline filter in
  `console.goose`. `esc.goose` implements the ANSI subset: arrows, cursor position/row/column,
  clear screen, erase line, SGR (bold/dim/underline/reverse), save/restore cursor. The
  README now describes both halves.
- **"Not verified: Compilation ..."** — removed; the corpus typechecks the unit and a driver
  reaches its editing and escape paths.
- **Limits** — added `CONSOLE_LINE_MAX` (256), `HISTORY_SLOTS` (8) and `ESC_PARAMS_MAX` (4),
  each with the test that reaches it.
