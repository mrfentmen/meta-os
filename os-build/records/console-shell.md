# Record — the console task and its shell, from the code

Scope: `kernel/src/sched.rs`, the `console_task` and `run_command` functions. Function names
exact; line ranges approximate. Evidence: typed `status` in `K3-boot.txt`, full command set in
`K7-boot.txt`.

## The loop

`console_task` is an ordinary kernel task, spawned with the demo tasks. Each pass:

1. drains the keyboard ring (`interrupts::keyboard_read`) until empty;
2. takes press codes only (`scancode & 0x80 == 0`) for the idle clock, but matches every code;
3. handles shift (`0x2A`/`0x36` press, `0xAA`/`0xB6` release), backspace (`0x0E`), and decodes
   the rest through `decode_scancode(scancode, shift)`;
4. builds a line in an 80-byte buffer; an overlong line sets a `truncated` flag and prints
   `line too long, truncated to 80` when Enter is pressed;
5. on Enter, runs the command and resets the buffer;
6. yields (`yield_task`) so the other tasks run.

## Commands

| command | output |
|---|---|
| `status` | `tasks N ticks N heap_free NK`, then `STATUS tasks=N ticks=N heap_free_kb=N` (also drawn cyan on VGA) |
| `help` | `commands: status help uptime mem ps` |
| `uptime` | `uptime Ns ticks N` (seconds = ticks / 100) |
| `mem` | `mem frames_free N frames_total N heap_free NK heap_total NK` |
| `ps` | one line per spawned slot: `ps id N state <State> ticks_used N prio N` |
| unknown | `unknown command`, then the help listing |

There is **no prompt string**, by ruling: the shell prints none rather than inventing one.
An empty line prints nothing.

## Attract screen

After `BOOT_IDLE_TICKS` (~2 s) with no key, and again after `IDLE_TICKS` (~30 s) idle, the shell
snapshots the screen and draws the logo frames, one per `FRAME_TICKS`. Any key press restores
the snapshot and is then processed normally — the key that exits the attract is not swallowed.
Drawing is VGA-only, so the serial log stays a clean shell log.

## Findings

1. **`ps` reports `ticks_used 0` for every task.** The quantum counter exists in the scheduler
   but nothing accumulates into it, so the column is structurally true and informationally
   empty (`K7-boot.txt` shows seven zeros). Either accumulate or drop the column.
2. **The shell has no exit/reboot/shutdown command**, and the line buffer is 80 bytes with
   truncation rather than editing.
3. **`clear` is named in the code's comment but absent from the help listing**; if it exists,
   help is wrong, and if it does not, the comment is. Recorded rather than guessed.
