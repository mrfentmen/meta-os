# settings — the desktop's typed store, validated at the write

Status: **RUNS** — `tests/t86_settings` passes in the native host corpus
(`run_native.sh t86_settings`, measured 2026-11-02: `RUNS=1 FAILS=0`), and the
program typechecks under `os-build/layer1/check_services.sh`. Layer 5, face
service 1.

## What it holds

A closed table of typed settings: colour, mode, animation, wallpaper index and
hostname. Each id has a kind and a range, and both are checked when the value is
written.

## The three properties, and why a key/value map does not give them

1. **Validation at the write, not the read.** A mode of 9 or a colour of
   `0x1ffffff` is refused at `st_put_int`, so no consumer downstream has to
   defend against a value that could never have been written.
2. **A dirty count that means something.** Writing the value that is already
   there is not a change and does not dirty the entry (`st_text_eq` is the text
   half of this). `st_dirty_count` is therefore accurate, and a save does not run
   for nothing.
3. **An atomic import.** `st_import` parses into a staging copy of the table and
   replaces the live one only after every line validates. A corrupt file in the
   middle applies nothing — the live settings are exactly what they were.

## What it is not

Not a general key/value store. The key set is closed: `st_import` refuses an
unknown id rather than adding it, because a store that accepts any key at
runtime cannot validate anything — it does not know what a key means.

## Surface

| Function | Answers |
|---|---|
| `st_put_int` / `st_get_int` | write and read a numeric setting, range-checked |
| `st_put_text` / `st_get_text` | write and read a text setting, length- and character-checked |
| `st_dirty_count` / `st_clear_dirty` | how many entries differ from what was saved |
| `st_export` / `st_import` | the file form; import is all-or-nothing |
| `st_kind`, `st_name`, `st_in_range`, `st_count` | the table itself, readable |

Capacity is `SET_MAX` (24) entries and `SET_TEXT_MAX` bytes of text per entry;
both are static, and `st_import` returns `E_NO_SPACE` rather than growing.

## Where the proof is

`services/tests/t86_settings.goose` — the driver that exercises the write-time
refusals, the dirty count and the atomic-import path.
