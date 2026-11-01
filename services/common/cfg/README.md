# `common/cfg` — key=value config over borrowed text

**Status: WRITTEN.** Not COMPILED (no Goose toolchain).

## Format

```
# comment   (or ; comment)
key = value

[section]
other = 42
enabled = yes
```

Values are trimmed at both ends. A value **may contain spaces** — the split is on
the first `=`, not on whitespace. Section names are identifiers: `[ a b ]` is not
a section, because two names that look alike and differ must not both parse.

## Design: borrow, don't copy

`Config` holds a `u8[:]` slice of text that someone else owns (a service's static
config blob). Every lookup scans it. Configs are tens of lines and lookups happen
at start-up or on reload, not in a hot loop. The payoff: no parsed copy that can
disagree with the bytes, no fixed entry array to overflow, no allocation.

## API

| Function | Does |
|---|---|
| `cfg_init(text)` | wrap borrowed text |
| `cfg_find(cfg, section, key) -> start, end, bool` | the value span |
| `cfg_get(cfg, section, key, out, cap) -> bool` | copy the value into your buffer |
| `cfg_has(cfg, section, key) -> bool` | is the key present |
| `cfg_int(cfg, section, key, default) -> i64, bool` | integer with honest failure |
| `cfg_bool(cfg, section, key, default) -> bool, bool` | `1/0`, `true/false`, `yes/no`, `on/off` |

An empty `section` means the top level. A key after a `[section]` header is **not**
top-level — the header changes which pairs are visible.

## Deliberate refusals

- **No quoting, escapes, multi-line values, includes or env expansion.** Each is a
  place a malformed file gets half-understood.
- **Case-sensitive booleans.** `True` is a typo this parser refuses, not a value
  it guesses at.
- **A non-empty garbage value is not `true`.** `cfg_bool` returns `ok=false` for
  anything unrecognised, including `""`.
- **`cfg_int` does not distinguish absent from malformed.** For a config both mean
  "fix the file"; a caller that needs the difference uses `cfg_get`.

## Verification

| Form | Source |
|---|---|
| `trim`, `split`, `parse_int`, `find`, `compare` | `reference#30` |
| slices, indexing, `text[a..b]` sub-ranges | `spec#40`, `samples/03_strings.goose` |
| trailing bool / code returns | `samples/04_errors.goose` |
| multiple returns incl. a trailing bool | `samples/01_tour.goose` |

## Not verified

Compilation; that `parse_int` takes a `u8[:]` slice and returns `i64, bool` (the
docs list the name, not the signature); and that a struct field of type `u8[:]`
inside a struct literal initialises from a slice parameter — `spec#40` shows
slices as parameters and returns, not as struct fields. B-L1-47 tests the parser
first, before any service trusts a config.
