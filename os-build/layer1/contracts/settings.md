# Contract — `settings`

Status: **RUNS** — `services/tests/t86_settings.goose`, on the host shim. Not started by a
supervisor, because nothing starts a service yet.

## What it is

The key/value config store the face layer draws from. Six keys, each with a type, a range
and a default; values live in fixed storage, are staged before they are committed, and can
be exported to and imported from one line of text so an image can carry its config.

## The keys

| id | name | type | range | default |
|---|---|---|---|---|
| 1 | `wallpaper` | int | 0..`SET_WALLPAPER_MAX` (7) | 1 |
| 2 | `bg` | int | 0..`SET_COLOR_MAX` (0xffffff) | `0x10141c` |
| 3 | `bar` | int | 0..`SET_COLOR_MAX` | `0x1c2230` |
| 4 | `mode` | int | 1 = dark, 2 = light | 1 |
| 5 | `anim` | int | 0 or 1 | 1 |
| 6 | `hostname` | text | 1..31 bytes, printable | `meta-os` |

`SET_MAX` is 24 entries, which is six keys plus room for named profiles. `st_count()`
reports how many are occupied, so a caller can see the headroom rather than assume it.

## API

| function | returns | notes |
|---|---|---|
| `st_init()` | — | table to defaults, dirty cleared |
| `st_put_int(id, v)` | `CODE_OK` / `E_RANGE` / `E_NOTFOUND` | range is per key, checked before write |
| `st_get_int(id)` | `(value, code)` | unknown id → `(0, E_NOTFOUND)` |
| `st_put_text(id, s)` | code | rejects control bytes, over-long text, non-text keys |
| `st_get_text(id)` | `(slice, code)` | slice points into the table; caller must not hold it past a write |
| `st_export(out)` | bytes written | `k=v;k=v;...` one line, no terminator |
| `st_import(data)` | `CODE_OK` / `E_CORRUPT` | atomic: a bad line stages nothing |
| `st_dirty_count()` / `st_clear_dirty()` | count | what persistence would need to flush |

## Failure modes, all driven by the test

- **Out of range.** `mode = 3` is `E_RANGE` and the old value survives. The check happens
  before the store is touched, so there is no half-written state to reason about.
- **Unknown key.** `E_NOTFOUND` from both getters and both setters.
- **Bad text.** A control byte, an empty string or 32+ bytes is refused whole.
- **Corrupt import.** A line with a missing `=`, an unknown key, an out-of-range value or a
  bad number fails the import and leaves every value as it was. The staging array is the
  reason: `st_import` builds a candidate table first and commits only at the end.
- **Size.** The 24th entry can be written and the 25th is `E_NO_SPACE`; a profile that
  wants to exist needs one of the six keys removed first.

## Restart semantics

There is no persistence call in this build. `st_init()` resets to defaults and clears
dirty, so **a restart loses every change** unless the caller exported first. That is a fact
about this file, not a bug to discover later: the storage hook is `st_dirty_count` +
`st_export`, and it is not wired.

## Limits

`SET_MAX` 24, `SET_TEXT_MAX` 32 (31 usable), `SET_COLOR_MAX` 0xffffff,
`SET_WALLPAPER_MAX` 7. The six-key table is 2 ints per entry plus 32 bytes of text, so the
whole store is under 1 KiB and is measured by `size_audit.py`.
