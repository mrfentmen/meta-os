# input — scancodes to key events

Status: **WRITTEN** (not COMPILED — no Goose toolchain on this Mac). Layer 4,
service 10.

## The split

The K3 PS/2 driver fills a ring of raw bytes. It does not know what a key is. This
service turns bytes into events — which key, pressed or released, with which
modifiers — and that is where the meaning lives. Scan code set 1 is assumed because
that is what `kernel/src/interrupts.rs` configures; if the kernel ever switches
sets, `input_decode` is the only function that changes.

## Keymap as a function, not a table

A 128-entry table needs initialising at start-up, which is a second table to keep in
step with the first. An if-chain cannot drift: one place says what `0x1E` means. It
costs a handful of compares per keypress, which at a human typing rate is not a
cost.

Unmapped keys return `0` — "no character", not an error. Arrows and modifiers
reaching the character function is expected.

## Caps is a latch, not a second shift

`MOD_CAPS` flips on press only, and applies to letters via `input_letter`. Folding
it into `MOD_SHIFT` would turn `1` into `!`, which is not what caps lock does.

## Repeat is software

The controller can repeat by itself, but then the delay and rate live in a hardware
register a user cannot change and a test cannot drive. Here they are data:
`repeat_delay_ms` (floor 250) and `repeat_rate_ms` (floor 16).

`input_repeat` advances by exactly one rate and never catches up in a burst: a
console blocked for 500 ms emits **one** repeat, not ten. If modifiers changed
while the key was held, the repeat uses the new ones — that is what the user is
looking at.

## Calls

| Call | Purpose |
|---|---|
| `input_init(delay_ms, rate_ms)` | decoder state, clamped |
| `input_decode(scancode, now_ms)` | (KeyEvent, got_event) — modifiers update state and emit `ch == 0` events |
| `input_repeat(now_ms)` | (KeyEvent, got_event) — the held key's next repeat |
| `input_passthrough(byte)` | bytes that are already characters (serial, scripted input) |

Not compiled, not run.
