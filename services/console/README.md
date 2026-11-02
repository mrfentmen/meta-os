# `console` — Layer 4, service 2

**Status: WRITTEN.** Not COMPILED (no Goose toolchain).

## What it does

The interactive line console: echoes what you type, edits in place, keeps an
8-line history, and hands completed lines on. Built on `sys_write_console` and
`sys_read_key`, with the history ring from `common/ring`.

Editing supported: insert anywhere, backspace, forward delete, left/right, up-arrow
history recall. A redraw is "carriage return, prompt, line, pad, step back" — no
terminal state to get out of sync, correct on any console that prints.

## No shell is attached

Pressing Enter echoes the line, stores it in history, and prints
`[console] line stored; no shell to run it (B-L1-87)`. Nothing is executed,
because the shell is B-L1-87 and a console that pretended to run commands would be
a mock. The line a shell will receive is exactly the buffer this service finishes.

## Contract

- **Entry:** `export "svc_entry" fn service_main() -> i32` — no `BootInfo`
  argument yet (Q-B-L1-4), same recorded deviation as `bootlog` and `time`.
- **Kernel surface:** `sys_write_console`, `sys_read_key`, `sys_yield`.
- **Needs:** K2 (framebuffer), K3 (keyboard), K5 (`yield`), K6 (calls).
- **Polling, not blocking:** there is no key-wait call (Q-B-L1-1), so the loop
  polls and yields. That costs CPU in the one service a user stares at, and the
  requirement to fix it is A4 in `BOUNDARIES.md`.

## Storage

All static: a 256-byte line, a 2048-byte history arena, and the ring's indices.
No allocation anywhere, and the sizes are constants at the top of the file so the
size audit (B-L1-136) can total them.

## Limits, stated

- **8 history lines.** A choice, not a law; one constant to change.
- **Printable ASCII only.** A control byte the console does not handle is ignored
  rather than guessed at; B-L1-107 covers the rest.
- **Escape handling is three sequences** (`ESC [ A/B/C/D`). Anything longer is
  dropped until B-L1-107.
- **A lone `ESC` does not leave the console.** There is nowhere to leave to yet.

## Verification

| Form | Source |
|---|---|
| `export "svc_entry" fn`, `extern fn` | `spec#41`, `spec#40` |
| builder, `push`, `append`, `.len` | `samples/03_strings.goose` |
| slices and sub-ranges `line[0..len]` | `samples/03_strings.goose` |
| trailing bool | `samples/04_errors.goose` |
| `while` / `if` / `continue` / `break` | `list_keywords` |
| struct field arrays (`Ring`, `MsgRing`) | `stdlib#13` |

## Not verified

- **The cross-file imports.** `spec#57` describes `import a.b.c;` resolved from
  the importing file's package root; whether that root is `services/` here is not
  stated. This is the largest risk in the file and the first thing the first
  COMPILED pass must settle.
- **Compilation**, and with it the static-array indexing this file leans on
  (`line[i] = v` on a fixed array).
- **The key event shape.** `sys_read_key` is assumed to deliver one byte per key
  with control keys as the conventional codes; the kernel may define events
  differently, and then `handle_key` changes, not the console's design.
