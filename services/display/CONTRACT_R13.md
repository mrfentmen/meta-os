# Contract note — R13-012, display output schema

Status: **AUDITED — 2 gaps filed**.
Facet: what `display` emits to its consumer, in what shape, and what it guarantees about a failed write.

## Evidence

Commands:

```sh
grep -nE '^fn disp_|^fn text_' services/display/*.goose
nl -ba services/display/display.goose | sed -n '248,272p'
```

Relevant output:

```text
255  fn disp_paint(v: i64) -> i64 {
256      if !disp_valid(v) { return E_INVAL; }
259      while row < vcons[v].rows {
262          while end > 0 && (... == 0x20 || ... == 0) { end = end - 1; }
265          if end > 0 {
266              sys_write_console(vcons[v].screen[row * cols .. row * cols + end]);
267              sys_write_console("\n");
268          }
269          row = row + 1;
270      }
271      return CODE_OK;
272  }
```

The public surface is `disp_init`, `disp_new`, `disp_valid`, `disp_scroll`, `disp_hist_lines`,
`disp_putc`, `disp_puts`, `disp_active`, `disp_switch`, `disp_paint`, `disp_switch_key`, plus
`text_wrap`, `text_line_count` and `text_clip`.

## Corrected contract

There is no data schema. `disp_paint` is a byte sink: for each row it trims trailing spaces and
NULs, writes the remaining row through `sys_write_console`, then writes `"\n"`. Empty rows emit
nothing at all, including no newline. The only structured output is the return code: `E_INVAL`
for a bad console index, `CODE_OK` otherwise. `disp_switch` returns `(previous, CODE_OK)`.

No console id, row number, width or cursor position is emitted. A consumer cannot reconstruct
which console a row belongs to from the bytes alone.

## Mismatches

- **R13-012-G1** — the output is not a schema and cannot be consumed as one; `disp_paint`
  returns `CODE_OK` without reporting how many rows were written.
- **R13-012-G2** — the return value of `sys_write_console` is discarded, so a failed write still
  returns `CODE_OK`. See `services/display/GAPS_R13.md`.
