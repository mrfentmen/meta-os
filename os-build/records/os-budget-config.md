# `crates/os-budget` — config surface (B068)

Everything the crate reads from outside. It has no CLI flags, no
config file, and no config struct.

## Environment variables

| Name | Read at | Default | Accepted | Wrong value → |
|---|---|---|---|---|
| `WATCHDOG_BUDGET_WARN_PERCENT` | `lib.rs:239-249` (`budget_warn_percent`), every call | 80 | integer 1–100 | blank, unparseable, 0, or >100 → 80 silently |
| `META_MODEL_API_INPUT_USD_PER_MTOK` | `lib.rs:1269-1287` (`rates`), every call | 3.0 | anything `f64::from_str` accepts (`2.5`, `0`, `-1`, `inf`, `NaN`) | blank or unparseable → 3.0, source `default` |
| `META_MODEL_API_OUTPUT_USD_PER_MTOK` | `lib.rs:1269-1287` | 15.0 | same | blank or unparseable → 15.0, source `default` |

Notes:

- The warning percent is read per call; Python computes it once at
  import (`os/intel/budgets.py:78`). Equivalent unless the environment
  changes mid-process (gap list item 18).
- The rate parser performs **no range or finiteness check**. A negative
  or `NaN` rate is accepted and produces a negative/`NaN` cost. That
  is a finding: the rate path should refuse non-finite and negative
  values, because the totals' pass/fail comparison silently becomes
  meaningless.
- A bad rate is not silent to a careful caller: `rates()` returns a
  source map (`{"in": "env:...", "out": "default"}`) that the rendered
  tables print.

## Files

| Path | Read by | Default | Missing/unreadable → |
|---|---|---|---|
| `os/intel/prompts/dispatch.md` | `build_rows_from_disk` (`lib.rs:1433-1442`), resolved as `<CARGO_MANIFEST_DIR>/../../os/intel/prompts/dispatch.md` | none — the file is required | `Err("cannot read <path>: <os error>")` |
| `os/os/services/relay-workers.slice` | not read by the crate; `parse_slice` takes text (`lib.rs:1976`). The crate's test reads it (`lib.rs:3153-3163`) | none | a caller that reads it gets the OS error; the parser itself has no file access |

`build_rows` (`lib.rs:1329`) takes the dispatch text as an argument, so
a caller with no filesystem can still measure. Only
`build_rows_from_disk` touches disk.

## Compile-time inputs

| Name | Used by | Effect |
|---|---|---|
| `CARGO_MANIFEST_DIR` | `lib.rs:1436`, `lib.rs:2441`, `lib.rs:3156` | resolves the two repo fixture paths above |

Not runtime config; a crate built from a copied tree without `os/`
fails the file read by design (gap list item 20).

## Not config

- `CREDIT_USD`, `RESERVED_HALF_USD`, `WORST_OUTPUT_TOKENS`,
  `DISPATCH_EXPECTED_OUTPUT_TOKENS` are constants (`lib.rs:1146-1154`),
  not environment-overridable. A caller that needs a different cap
  must change the crate.
- `BUDGET_WARN_PERCENT` is not a public constant in Rust; the value is
  the function `budget_warn_percent()`. Tests pass the percentage
  explicitly (`at_warning(..., Some(n))`) so they never depend on the
  environment.
