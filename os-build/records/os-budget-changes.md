# `crates/os-budget` — changelog (B072)

Compiled on 2026-11-02 from the crate's own headers and the reports
that name it. **Limitation:** this slice had no git access (no
terminal), so this is not produced by `git log`. Every entry names the
file that carries it; the commit SHAs are deliberately absent rather
than guessed.

## 2026-11-02 — B00 skeleton

- `crates/os-budget` added to the workspace member list
  (`Cargo.toml:14`) with a locked package entry (`Cargo.lock:411`).
- `Cargo.toml` created with only `name`, `version`, `edition` — no
  dependencies, no binaries. The file is still 64 bytes.
- `src/lib.rs` created with the B00 header listing the seven source
  modules and six Python test files this batch ports.
- At this point the header said “Skeleton only: no logic yet.”

## 2026-11-02 — B20 port (owner: Milo)

- The batch spec `batches/B20.md` names the sources:
  `os/intel/budgets.py`, `cost_check.py`, `brief_cost_check.py`,
  `drills/budget_forecast.py`, `drills/budget_gate.py`,
  `drills/cgroup_limits.py`, `os/mos/disk_audit.py`, plus six test
  files.
- The port landed as one `lib.rs` in the B16–B19 single-file shape:
  value model, budgets, forecast, brief-measure helpers, cost check,
  brief cost check, budget gate, cgroup portable parts, disk audit,
  tests (`lib.rs:29-43`).
- 60 unit tests were pinned, covering the Python figures:
  `0.021258 / 0.12789 / 0.143982` and breakeven `520`
  (`lib.rs:3003-3026`), the busy-fixture `416/266` and `542/298`
  (`lib.rs:3063-3096`), and the gate/forecast phase tests.
- The workspace verification report counts `os_budget 60` in a
  1,379-passed run (`OPENCODE_FINISH_REPORT.md:114`).
- `B20.md` records gate 1 (local) done and gate 2 (the boss's Mac)
  still pending; the Python originals stay the live fallback until
  PORTED.

## 2026-11-02 — Bond Section 6 (this lane)

- **Header fix (B064):** the B00 line “Skeleton only: no logic yet” was
  false above 3,500 lines of port. Replaced with a statement that the
  B20 port is implemented and the header is historical
  (`lib.rs:29-32`).
- **Parity fix found by the error tests:** `parse_artifact_ref`
  accepted `artifact:/out@v1` (empty job) because only the name and
  version were checked. Python's regex requires at least one character
  in the job (`disk_audit.py:64`), so the Rust now refuses it too.
- **Testable file seam:** `build_rows_from_disk` now delegates to a
  private `build_rows_from_path`, so the “cannot read” refusal has a
  unit test without moving the repo fixture. Same behaviour and error
  text; the public surface did not grow.
- **New records:** `os-build/records/os-budget.md` (behaviour, every
  claim tied to a line range), `-gaps.md` (20 unported behaviours, with
  Python line numbers), `-records.md` (12 worked record shapes, field
  by field), `-callers.md`, `-config.md`, `-drill.md`, `-surface.md`,
  and this file.
- **New tests (not yet run in this slice):**
  - `crates/os-budget/tests/error_paths.rs` — the refusal and failure
    branches.
  - `crates/os-budget/tests/edge_cases.rs` — empty, maximum,
    duplicate, out-of-order.
  - `crates/os-budget/tests/gap_close.rs` — the cost/brief-cost
    sections brought up to the test depth of the gate/forecast
    sections.
- **Findings raised, not fixed:** table rate text prints `3` where
  Python prints `3.0`; `FakeQueue::claim` accepts an unknown job id;
  duplicate slice keys resolve first-wins vs Python last-wins;
  duplicate manifest names resolve first-wins vs Python last-wins;
  `build_rows_from_disk` has no caller; `HOG_*` constants are unused
  until the host phase lands; rate parsing accepts negative/NaN.

## Owed next

1. Run `cargo test -p os-budget -j1` and record the pass count
   (the lane's own command, not inherited from the 1,379 report).
2. Close or pin the 20 gap items; the two duplicate-key divergences
   are the only ones that change an answer on the same input.
3. Gate 2 (the boss's Mac) for B20 as a whole.

## Commit history (appended by coordinator, from git)

- 2ea5f75 2026-10-30 B20: port budget & resource policy to crates/os-budget (Milo, gate 1)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
