# `console` — Layer 4, service 2

**Status: RUNS.** Reached by `tests/t49_bootlog` (23 checks, exit 0) and typechecked with the
corpus by `os-build/layer1/check_services.sh`; `tests/t110_console_r11.goose` drives its line
cap and escape parser.

## What it does

The interactive line console: echoes what you type, edits in place, keeps an
8-line history, and hands completed lines on. Built on `sys_write_console` and
`sys_read_key`, with the history ring from `common/ring`.

`console.goose` is the editing half — insert anywhere, backspace, forward delete,
left/right, up-arrow history recall. A redraw is "carriage return, prompt, line,
pad, step back": no terminal state to get out of sync, correct on any console
that prints.

`esc.goose` is the parsing and emitting half — an ANSI subset as data:

| Accepted | Meaning |
|---|---|
| `ESC [ n A/B/C/D` | cursor up / down / right / left |
| `ESC [ r ; c H` and `f` | cursor position |
| `ESC [ n G`, `ESC [ n d` | cursor to column, cursor to row |
| `ESC [ 2 J`, `ESC [ K` / `1K` | clear screen, erase to end of line |
| `ESC [ n m` | bold, dim, underline, reverse (0/1/2/4/7/22/24/27) |
| `ESC [ s` / `u`, `ESC 7` / `8` | save / restore cursor |

Anything else is reported as `SEQ_UNKNOWN` with the bytes it consumed, never
silently swallowed. A fifth CSI parameter is dropped instead of overwriting the
fourth — before that fix, `ESC [ 1;2;3;4;5;6H` could aim the cursor anywhere.

`console.goose` still has a small inline filter for `ESC [ A/B/C/D` so a stray arrow
does not land in the line buffer; the full parser is the service surface.

## No shell is attached

Pressing Enter echoes a newline, stores the line in history, and reports a
completed line to the caller. `entry.goose` then prints
`[console] line stored; no shell to run it (B-L1-87)` and a fresh prompt. Nothing
is executed: the shell is B-L1-87, and a console that pretended to run commands
would be a mock. The line a shell will receive is exactly the buffer this service
finishes.

## Contract

- **Entry:** `export "svc_entry" fn service_main() -> i32` — no `BootInfo`
  argument yet (Q-B-L1-4), same recorded deviation as `bootlog` and `time`.
- **Kernel surface:** `sys_write_console`, `sys_read_key`, `sys_yield`.
- **Needs:** K2 (framebuffer), K3 (keyboard), K5 (`yield`), K6 (calls).
- **Polling, not blocking:** there is no key-wait call (Q-B-L1-1), so the loop
  polls and yields. That costs CPU in the one service a user stares at; fixing it
  is requirement A4 in `BOUNDARIES.md`.

## Storage

All static: a 256-byte line, an 8-slot history ring, and the parser's four
parameter slots. No allocation anywhere, and the sizes are constants at the top
of each file so the size audit (B-L1-136) can total them.

## Limits, and the test that reaches each

| Limit | Value | Reached by |
|---|---|---|
| `CONSOLE_LINE_MAX` | 256 bytes | `t110`: 255 inserts succeed, the 256th is refused |
| `HISTORY_SLOTS` | 8 lines | `t110`: `history_slots()` reads the ring back and equals the constant |
| `ESC_PARAMS_MAX` | 4 parameters | `t110`: a six-parameter CSI keeps the first two and drops the rest |

Printable ASCII only: a control byte the console does not handle is ignored
rather than guessed at. A lone `ESC` does not leave the console — there is
nowhere to leave to yet.

## Verification

| Form | Source |
|---|---|
| `export "svc_entry" fn`, `extern fn` | `spec#41`, `spec#40` |
| builder, `push`, `append`, `.len` | `samples/03_strings.goose` |
| slices and sub-ranges `line[0..len]` | `samples/03_strings.goose` |
| trailing bool | `samples/04_errors.goose` |
| struct field arrays (`Ring`, `MsgRing`) | `stdlib#13` |

## Not verified

- **The key event shape.** `sys_read_key` is assumed to deliver one byte per key
  with control keys as the conventional codes; the kernel may define events
  differently, and then `handle_key` changes, not the console's design. On the
  host shim it returns 0 forever, so no test here proves a real keyboard.
- **Restart continuity.** Line and history are process memory and are lost when
  the supervisor restarts the unit; that is named in
  `os-build/layer1/r11/console.md`, not papered over.
