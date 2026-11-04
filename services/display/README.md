# display — virtual consoles over one framebuffer

Status: **COMPILED** (Lane B R5, 2026-11-04 — build+run log: services/display/BUILD_LOG.txt; was RUNS on the 2026-11-02 host corpus) — `tests/t56_input_display` (49 checks, exit 0), plus
`tests/t115_display_r11` for the console limits and the text helpers; the text module is
also driven by `t79_limit_drivers` and `t103_limits_rest`. Layer 4, service 11.

## The problem it solves

One display, three users: the person typing, the boot log, and (later) the agent's
structured view. Sharing one cursor means they overwrite each other, and somebody
reads a command prompt in the middle of a kernel log. So: four consoles, each with
its own text model, one visible.

## Real, and not

**Real:** wrapping, newline/CR, scrolling into history, per-console cursor and
history, switching with a defined repaint.

**Not real yet:** painting. `disp_paint` emits the visible console through
`sys_write_console`, and a kernel that appends at a cursor cannot address a row — so
the first paint after a switch starts wherever the kernel is. A true in-place
repaint needs cursor positioning (B-L1-107's escape handling plus a kernel that
honours it). Recorded as requirement A12 rather than faked.

## Layout

| Name | Value | Why |
|---|---|---|
| `VCON_MAX` | 4 | console, boot log, agent view, one spare |
| `DISPLAY_LINE_MAX` | 128 | characters before wrapping; wider than a real terminal so a wrapped boot line stays one line |
| `SCROLL_MAX` | 256 | history lines kept per console |
| screen | `u8[..2048]` per console | `rows × cols`, bytes only |
| history | `u8[..32768]` per console | byte ring; `hist_start`/`hist_used`/`hist_lines` |

History is a byte ring rather than a ring of line records: a console scrolls by the
line, and a ring of bytes would have to rediscover where lines start — the same
bookkeeping in a worse place.

## Switching

`disp_switch_key(scancode, mods)` returns `Ctrl+Alt+F1..F4` as data, the convention
nobody has to be taught. `disp_switch(v)` repaints as part of the switch, so
"switch" and "draw the new one" cannot become two steps somebody forgets.

## Deliberately absent

No direct framebuffer writes (the kernel owns it; two writers means two cursors), no
colours (the K2 console has none, and attributes nothing renders are a promise this
service cannot keep), no scrollback paging (needs the same positioning as the
repaint).

Compiled to C and run as a host process. Not booted on the kernel: the console syscall it
paints through is the host shim's, and a paint on K1 writes nothing.
