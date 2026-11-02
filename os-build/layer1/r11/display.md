# display — Round 11 record

Source: `services/display/display.goose`, `services/display/text.goose` · Test:
`services/tests/t115_display_r11.goose` · Status: RUNS (`t56_input_display` 49 checks;
`t79_limit_drivers` and `t103_limits_rest` cover the text helpers)

## 1. Limits — PROVEN

Every `display` row `LIMITS.md` lists, plus the structural screen bound:

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `VCON_MAX` | 4 | `display.goose` | driven by `t115` | the fifth `disp_new` returns `-1` / `E_NOROOM`; four fit |
| `DISPLAY_LINE_MAX` | 128 | `display.goose` | driven by `t115` | width 129 returns `E_INVAL`; 80 is accepted |
| `SCROLL_MAX` | 256 | `display.goose` | driven by `t115` | 301 newlines on a 25-row console leave `disp_hist_lines == 256` |
| `WRAP_MAX_LINES` | 16 | `text.goose` | driven by `t115` | 24 four-byte lines return `count == 16` and `overflow == true` |
| screen cells | 2048 | `display.goose` | driven by `t115` | 80×26 returns `E_INVAL`; 80×25 is accepted |

The 2048-cell bound is a literal in a comparison, not a named constant, so `gen_limits.py`
does not list it; it is driven here rather than argued about.

## 2. Refusals — PROVEN

| refusal | code | the `t115` assertion that expects it |
|---|---|---|
| fifth console | `E_NOROOM` | `the fifth console is E_NOROOM, not a resize` |
| zero width / zero rows | `E_INVAL` | `a zero-width console is E_INVAL`, `a zero-row console is E_INVAL` |
| width past `DISPLAY_LINE_MAX` | `E_INVAL` | `a width past DISPLAY_LINE_MAX is E_INVAL` |
| screen over 2048 cells | `E_INVAL` | `a screen over 2048 cells is E_INVAL` |
| empty or 16-byte name | `E_INVAL` | `an empty name is E_INVAL`, `a name of 16 bytes is E_INVAL` |
| control byte other than NL/CR | `E_INVAL` | `a control byte is E_INVAL, not text`, `a tab is not stored…` |
| write to an invalid console | `E_INVAL` | `writing to an invalid console is E_INVAL` |
| switch to an invalid console | `E_INVAL` | `a switch to an invalid console is E_INVAL and does not move` |
| inverted or negative scroll region | `E_INVAL` | `an inverted region is E_INVAL…`, `a negative top is E_INVAL` |
| resize to an inverted region | `E_INVAL` | `a resize to an inverted region is E_INVAL` |
| clip width ≤ 0 | returns `0`, clipped if text existed | `t115` exercises width 2 and width 20; width 0 is the same arm in the code |

`disp_paint` is asserted only by its return code. Whether pixels appear is the kernel console's
contract, and `t56` already states that a paint on K1 writes nothing.

## 3. Restart — NAMED GAP

`vcons[]`, `vcon_count` and `active` are globals in the service's own memory. A supervisor
restart rebuilds an empty display: **all console text and all history are lost**, and the
active console returns to 0. No persistence path exists and none is claimed. Continuity was not
run — no drill killed the service and observed the repaint — so this is a named loss, not a
proven behaviour.

## 4. Contract — PROVEN

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | kernel console | `sys_write_console` (declared extern) | **FINDING: `SVC_CONSOLE` (2) is not in `SVC_DISPLAY`'s row** |
| out | `common.sys` | `sys_write_console` import | library, not a service edge |
| out | `session` (21) | none today | allowed but dormant |
| out | `logd` (3) | none today | allowed but dormant |
| in | `session` (21) | none today | the matrix allows it; nothing imports `display` |
| in | — | `root.goose`, `t56`, `t103` | compile-time inclusion, not a service call |

The finding: `SVC_DISPLAY = 11` permits `SESSION` and `LOG`, yet the service's real output path
is the kernel's console syscall, which the matrix does not model. Either the edge is a kernel
surface that needs no row, or the row is missing `SVC_CONSOLE`; that is a room-1 question and is
left as written rather than papered over.

## 5. Load — NAMED GAP

Ten screens of 80 bytes through one console (800 `disp_putc` calls), which crosses the wrap
path on every line. The numbers exist only after a run:

```
FAILS pass=41 fail=7 · `LOAD display ops=800 ok=0 refused=800`
```

## 6. README truth pass — PROVEN

- **“Status: WRITTEN (not COMPILED — no Goose toolchain on this Mac)”** → `RUNS`, naming
  `t56_input_display` (49 checks) and `t115`.
- **“Not compiled, not run.”** at the end → removed.
- The layout table called the line width **`LINE_MAX`**; the code's constant is
  `DISPLAY_LINE_MAX`. The table now uses the code's name, so a reader can find it.
- The “Real, and not” paragraph about painting is true and was left as written — it is the same
  distinction `t56` asserts.
