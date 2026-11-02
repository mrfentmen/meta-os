# `crates/stack` — config surface (B200)

The crate is a library with no binary, no flags, and no filesystem
access. Its whole configuration is five environment names, read by
`StackConfig::from_entries` (`src/lib.rs:127-137`) or `from_env`
(`src/lib.rs:139-148`).

| Name | Read at | Default | Wrong/empty value | Refusal |
|---|---|---|---|---|
| `RELAY_PORT` | `src/lib.rs:131` (entries), `141` (env) | `8787` | empty → default; any other string (including `abc`, `-1`, spaces) is kept verbatim | none (`src/lib.rs:110-115`) |
| `QUEUE_PORT` | `src/lib.rs:133`, `143` | `8935` | same pass-through rule | none |
| `PORT` | `src/lib.rs:135`, `145` | `8080` | same pass-through rule | none |
| `SPARK_API_KEY` | `src/lib.rs:136`, `146` | unset | non-empty → `ProductionDirect`; empty or unset → `DevHelper` | none (`src/lib.rs:117-121`) |
| `TRIO_JOB_NS` | `src/lib.rs:137`, `147` | none — not defaulted here | absent → `None`; empty → `Some("")`, carried verbatim | none |
| `TRIO_SPARK_VIA_HELPER` | **not read** | — | — | missing: the script's third transport state cannot be represented (G1/G2) |

## Files

None. `grep` for `std::fs`, `File::`, `read_to_string` and `include_str`
in `crates/stack/src` returns nothing; the module has no `use std::fs`.

## Notes

- `from_env` uses `std::env::var(...).ok()`, so a non-UTF-8 value is
  treated as unset and falls back — the same as a missing key.
- `from_entries` takes the **first** match for a duplicated key
  (`entries.iter().find`, `src/lib.rs:128`). The later duplicate is
  ignored; this is pinned by the tests.
- `RELAY_PORT`, `QUEUE_PORT` and `PORT` are not validated anywhere in
  the crate, matching `${VAR:-default}` in `run-stack.sh:31-33`. The
  invalid value surfaces later as an unreachable URL, not as a refusal
  here.
