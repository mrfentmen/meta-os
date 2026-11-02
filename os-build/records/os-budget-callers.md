# `crates/os-budget` — callers (B067)

Search: `os[-_]budget` across the repo, excluding
`crates/os-budget/**`, on 2026-11-02.

## Result: no Rust caller

Nothing in the workspace does `use os_budget` or calls a function from
this crate. It is a workspace member and a batch deliverable, not a
dependency of another crate.

## Every place the crate is named, and what it expects

| Caller | Expectation | Met? |
|---|---|---|
| `Cargo.toml:14` (workspace members) | the crate builds as a member | yes — `cargo test -p os-budget` is the gate |
| `Cargo.lock:411` | a locked package entry named `os-budget` | yes |
| `BATCHES.md:54` (batch map) | B20 owns `crates/os-budget` | yes |
| `BATCHES.md:477` (B20 section) | port inside the crate; `cargo build/test -p os-budget` are the gates | yes for `test`; no `bin` target exists, and none is expected |
| `SUPER_PROMPT.md:227-238` (T107–T116) | ported modules, tests with Python name roots, `cargo doc -p os-budget` | tests exist (60 unit + this lane's integration tests); docs are module comments, no `cargo doc` run here |
| `docs/RUST_REBUILD_PLAN.md:238` | B20 → `os-budget` | yes |
| `TASKS.md:183` | B20 budget & resource policy | yes |
| `OPENCODE_FINISH_REPORT.md:114` | counts `os_budget 60` tests | yes at the time; this lane adds 3 integration files |
| `os-build/aegis/DRILL.json:52` | `crates/os-budget/Cargo.toml` exists | yes |
| `os-build/aegis/SWEEP.md:24` | the crate is excluded from the secret sweep as a first-party crate | yes, by path |
| `os-build/BOND_TASKS.md:86-99` | Section 6 deliverables (this record set) | written in this lane |

## Callers of the Python originals (still the live path)

The crate does not replace them yet. Each original is called by:

- `os/intel/budgets.py` — imported by `intel/watchdog.py`,
  `intel/brief.py`, `os/intel/drills/budget_gate.py`, and the budget
  tests.
- `os/intel/forecast.py` — imported by `drills/budget_forecast.py` and
  the forecast tests.
- `os/intel/cost_check.py` — a script (`python3 intel/cost_check.py`)
  and imported by `brief_cost_check.py` for constants/builders.
- `os/intel/brief_cost_check.py` — a script.
- `os/intel/drills/budget_gate.py`, `budget_forecast.py` — drills,
  run by the eval lanes.
- `os/intel/drills/cgroup_limits.py` — a host drill; exits 2 when the
  cgroup controllers are absent.
- `os/mos/disk_audit.py` — a CLI (`--jobs`, `--memory-root`,
  `--artifact-root`), called by the OS-128 audit runs.

## Expectations the crate does not meet

1. The batch docs say “fresh module mirrors the source layout”; the
   port is one `lib.rs` with sections, not one module per source file.
   This is the B16–B19 single-file shape the crate header cites; the
   batch text is older. Finding, not a code defect.
2. `SUPER_PROMPT.md:238` says `cargo doc -p os-budget` must build.
   That command was not run in this lane (no terminal); nothing in the
   crate prevents it, and every public item carries a doc comment
   except the `Value` variants and a few fields, which rustdoc accepts.
3. No caller expects a CLI or a `main`, so the missing disk-audit CLI
   (gap list item 16) blocks nobody today.
4. The Python drills still drive the live budget/cost behaviour; until
   a caller imports the crate, the crate's parity is proven only by its
   tests, not by a running system.
