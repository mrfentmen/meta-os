# `crates/os-budget` — failure drill (B069)

What breaks first when each input stops arriving, read from the code.
Run the commands from the repo root, one at a time, with `-j1` (8GB
lane rule). Every expected line below is a real assertion in this
lane's tests or an existing crate test; no step needs a network or a
Spark call.

## Input map

| Input | First consumer | Failure mode |
|---|---|---|
| snapshot `budgets` key | `budgets_from_snapshot` (`lib.rs:313-329`) | missing/non-list → empty list; gate allows every claim, detector silent |
| a budget entry's `spent`/`cap` | `spend_ratio` (`lib.rs:251-261`) | non-int, cap ≤ 0, spent < 0 → `None`; entry is unbudgeted |
| snapshot `jobs`/`messages`/`alerts` | brief extractors (`lib.rs:623-754`) | missing/non-list → empty sections, no panic |
| dispatch prompt file | `build_rows_from_disk` (`lib.rs:1433-1442`) | unreadable → `Err("cannot read ...")`; no zero rows |
| model rate env | `rates` (`lib.rs:1269-1287`) | blank/bad → 3.0/15.0 and source `default` |
| memory journal | `audit` (`lib.rs:2190-2377`) | unreadable → `memory-journal` leak, once per agent |
| artifact store | `audit` (`lib.rs:2190-2377`) | unreadable entry/bytes → one `artifacts` leak per reference |
| slice file | `parse_slice` (`lib.rs:1976-1993`) | caller's file read fails; parser sees only text |
| cgroup controllers | `cgroup_gate_missing` (`lib.rs:2011-2025`) | `None` → both `cpu` and `memory` reported missing |

## Drill 1 — the budget disappears (fail-open)

Why this is first: a budget is optional by design. The gate treats a
missing cap as unbudgeted, so work keeps flowing. That is correct per
OS-085 (an absent budget is not a zero budget), but it means a lost
`budgets` key looks like a healthy system.

```
cargo test -p os-budget -j1 --test error_paths empty_snapshot_is_unbudgeted_not_zero
```

Expected: PASS. The test proves `budgets_from_snapshot` returns empty,
`claim_allowed(Null, Null)` is true, and `budget_state` is
`unbudgeted`. The observable symptom in a live system is “no warning
fired”, not an error.

## Drill 2 — the figures become strings

```
cargo test -p os-budget -j1 --test error_paths budget_gate_never_warns_or_holds_malformed_figures
```

Expected: PASS. `spent: "80"` / `cap: "100"` yields no ratio, no
warning, no hold. A lane whose ledger switched from int to string
silently stops warning; nothing crashes.

## Drill 3 — the snapshot loses its lists

```
cargo test -p os-budget -j1 --test error_paths empty_snapshot_yields_empty_sections
```

Expected: PASS. `message_parts(Null)`, `extract_decisions`,
`extract_owners`, `extract_blocked`, `extract_watch_items` all return
empty; the template brief still composes with “Nothing reported in
this window” wording.

## Drill 4 — the dispatch file is gone

This is the first hard failure. In a throwaway copy so the working
tree is untouched:

```
tmp=$(mktemp -d)
git clone --quiet --no-hardlinks . "$tmp/meta-os"
rm "$tmp/meta-os/os/intel/prompts/dispatch.md"
cd "$tmp/meta-os"
cargo test -p os-budget -j1 missing_dispatch_is_an_error
```

Expected: PASS, proving `build_rows_from_disk()` is `Err` whose text
starts `cannot read` and names the path. `build_rows(text)` with
caller-supplied text still succeeds — the failure is the file read,
not the maths.

## Drill 5 — the rates go bad

```
cargo test -p os-budget -j1 --test error_paths bad_rate_falls_back_to_default
```

Expected: PASS for `rate_value(Some("junk"), 3.0, "X")` → `(3.0,
"default")`. The tables print the source per rate, so a silent fallback
is visible in the header line. A negative rate parses successfully and
is **not** refused — that is a known finding, see the config record.

## Drill 6 — a store stops answering

```
cargo test -p os-budget -j1 --test error_paths unreadable_artifact_store_is_a_leak
```

Expected: PASS. `audit` returns `passed == false` and one leak with
`layer == "artifacts"`; a second job using the same unreadable store
files its own leak (leaks are per reference), while an unreadable agent
journal files once per agent.

## Drill 7 — the slice drifts

```
cargo test -p os-budget -j1 --test error_paths slice_mismatch_fails_file_phase
```

Expected: PASS. `CPUQuota=50%` or a missing `MemoryMax` makes
`slice_file_passes` false. A duplicate key is the known divergence:
Python keeps the LAST value, Rust `slice_value` returns the FIRST
(gap list item 17).

## Drill 8 — totals cross the cap

```
cargo test -p os-budget -j1 --test error_paths breach_flips_passed_and_headroom
```

Expected: PASS. A constructed `CostSummary` with
`worst_with_boot >= 75` has `passed == false`, a negative headroom,
and `run_cost_check`-shape exit code 1. No live rate is required to
prove the breach branch.

## Stop conditions

- A test fails or does not compile: stop and report the file and the
  compiler line; do not edit the assertion to match.
- `cargo` starts swapping or peaks the machine: stop, report on the
  lane, do not retry with more jobs.
- A drill changes a file outside a `mktemp` copy: stop; nothing here
  should touch the working tree except `target/`.
