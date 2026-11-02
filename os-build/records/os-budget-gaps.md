# `crates/os-budget` — behaviours the Rust port does not carry (B065)

Source of truth: the Python files named in the crate header. Each item
below is a task, not a port performed here. Line numbers are from the
2026-11-02 tree.

## A. Reusable helpers that are narrower than the original

1. **Default `day_hours` for `forecast_entry`.**
   Python: `os/intel/forecast.py:99-100` — `forecast_entry(..., day_hours=DAY_HOURS)`.
   Rust: `crates/os-budget/src/lib.rs:419-461` requires an explicit
   `day_hours: &Value`. `forecast_lines` supplies the default
   (`lib.rs:473-479`), but direct callers cannot omit it.
   Task: add a wrapper with the Python default, or pin the explicit
   argument as the intended API and delete the claim of parity.

2. **Unknown brief kind.**
   Python: `os/intel/cost_check.py:143-157` indexes
   `_brief.BRIEF_BUDGETS[kind]`, so an unknown kind raises `KeyError`.
   Rust: `lib.rs:558-566` (`brief_budget`) returns 220 for anything not
   `onjoin`/`ondemand`. `compose_brief_no_client` also maps unknown
   kinds to `morning` (`lib.rs:992-997`).
   Task: decide whether an unknown kind refuses (Python) or falls back
   (Rust), and make the docs say which.

3. **Full `compose_brief` path in the busy-fixture measurement.**
   Python: `os/intel/brief_cost_check.py:149-177` calls
   `_brief.compose_brief`, which can render optional records
   (`previous_brief`, `memory_budget`, `daily`, `memory_depth`,
   `federation`, `held_decisions`, `source_pointers`,
   `priority_order`, `blocked_contacts`, `screenshots`) and the
   WDG-028 watchdog line.
   Rust: `lib.rs:989-1004` only renders the core morning template;
   the omissions are listed at `lib.rs:574-586`.
   Task: port the optional sections, or add a pinned exclusion case
   per section proving the B20 fixtures never carry it.

4. **Rate defaults come from the client module.**
   Python: `os/intel/cost_check.py:179-186` imports
   `DEFAULT_RATE_IN_PER_MTOK` / `DEFAULT_RATE_OUT_PER_MTOK` from
   `intel/spark_client.py`.
   Rust: `lib.rs:1269-1287` hardcodes `3.0` / `15.0`.
   Task: make the defaults one value (a shared const or a generated
   table), so a client change cannot leave the crate quoting old rates.

5. **Rate text in the cost table.**
   Python: `os/intel/cost_check.py:270-306` interpolates the float
   (`f"...${rate_in}/Mtok..."`), so 3.0 prints `3.0`.
   Rust: `lib.rs:1468-1497` uses `{}` on `f64`, so the same value
   prints `3`. This is a visible parity difference in the header line.
   Task: format with `py_float_str` (already public) or pin the Rust
   spelling deliberately.

6. **Rate text in the busy-brief table.**
   Python: `os/intel/brief_cost_check.py:188-228` has the same float
   interpolation.
   Rust: `lib.rs:1717-1745` has the same `{}` behavior.
   Task: same fix as item 5, one decision for both tables.

7. **`audit` refuses an unknown job id.**
   Python: `os/intel/drills/budget_gate.py:47-74` — `FakeQueue.claim`
   indexes `self.jobs[job_id]`, so an unknown id raises `KeyError`.
   Rust: `lib.rs:1816-1864` returns `true` for an unknown id when the
   gate allows the claim, and marks nothing.
   Task: return a refusal for an unknown job (or document the
   difference and drop the “mirrors jobs.py” claim).

8. **`budget_warning_alerts` ignores alerts already filed.**
   Python: the live branch is `intel/watchdog.py` `tick`, which dedupes
   against the existing alert list; the drill filters those results
   (`os/intel/drills/budget_gate.py:83-86`).
   Rust: `lib.rs:1866-1920` dedupes only within one tick (one entry per
   lane) and never receives prior alerts, so calling it twice returns
   the same alert twice.
   Task: accept the prior alert keys (or the snapshot's `alerts`) and
   suppress a second filing.

9. **Budget-line age formatting.**
   Python: `intel/brief.py` `memory_budget_lines` appends
   `" (as of YYYY-MM-DD HH:MM ET)"` or
   `" (snapshot time not reported)"`.
   Rust: `lib.rs:1922-1964` takes `age_label: &str` from the caller and
   formats nothing.
   Task: port the ET formatting once the brief crate owns the clock.

## B. Host-only phases

10. **Cgroup `verify` phase.**
    Python: `os/intel/drills/cgroup_limits.py:125-137` runs
    `systemd-analyze verify` and requires exit 0.
    Rust: absent. Task: keep it host-only, but name it in the crate
    docs as environment-gated.

11. **Cgroup `gate` phase.**
    Python: `cgroup_limits.py:139-156` reads
    `/sys/fs/cgroup/cgroup.controllers` and prints
    ENVIRONMENT-BLOCKED on failure.
    Rust: `lib.rs:2011-2025` only models the answer
    (`Option<&str>` → missing controllers).
    Task: keep the read in a host adapter; the pure gate is already
    ported.

12. **Cgroup `enforcement` phase.**
    Python: `cgroup_limits.py:158-261` installs the transient slice,
    runs a burner and a hog, waits for stats, and cleans up.
    Rust: absent; `HOG_TARGET_CHUNKS` / `HOG_CHUNK_MB` / `HOG_TEST_CAP`
    (`lib.rs:1968-1972`) are unused constants.
    Task: a host-only drill binary or an explicit exclusion record.

## C. Store seams

13. **Missing store root.**
    Python: `os/mos/disk_audit.py:126-139` and `:141-158` return `{}`
    when the memory root is not a directory; a missing artifact root
    reads as empty through the store module.
    Rust: `ArtifactStore` / `MemoryStore` (`lib.rs:2041-2056`) leave
    that rule to the backend; `FakeStores` returns empty, but the
    contract is not written down.
    Task: state the backend contract (“missing root = empty, not an
    error”) in the trait docs, and test one backend against it.

14. **A skipped journal class.**
    Python: `disk_audit.py:141-158` catches `memory.MemoryError` (loud
    leak) and `ValueError` (silently empty) as two different outcomes.
    Rust: `MemoryStore::list_keys` returns one `String` error, so a
    caller cannot tell “corrupt journal” from “wrong agent name”.
    Task: split the error type or pin the single-error collapse as a
    deliberate simplification.

15. **Duplicate manifest names.**
    Python: `disk_audit.py:160-212` builds a dict by name, so the LAST
    manifest entry wins.
    Rust: `lib.rs:2190-2378` uses `entries.iter().find(...)`, so the
    FIRST wins. A store with two entries for one name would verify a
    different version than Python.
    Task: match last-wins, or reject duplicate names in the store
    contract.

16. **Disk-audit CLI.**
    Python: `disk_audit.py:306-end` — argparse, reads a jobs JSON file,
    prints one line per job and `LEAK ...` lines, exits 0/1/2.
    Rust: no binary and no CLI.
    Task: add a `src/bin/disk_audit.rs` only if the OS lane needs the
    command; otherwise record the shell as the caller's job.

## D. Parsing and timing differences

17. **Duplicate slice keys.**
    Python: `os/intel/drills/cgroup_limits.py:64-77` parses into a
    dict, so the LAST `key=value` wins.
    Rust: `lib.rs:1976-1998` keeps a `Vec` and `slice_value` returns
    the FIRST match. A slice with two `MemoryMax` lines is read
    differently.
    Task: match the Python last-wins rule, or reject duplicates.

18. **Warning-percent read timing.**
    Python: `os/intel/budgets.py:78` computes
    `BUDGET_WARN_PERCENT` once at import.
    Rust: `lib.rs:239-249` reads the environment on every call.
    Same value in a normal process; different if the environment is
    changed after start. The Rust comment calls this equivalent “for
    every caller here”.
    Task: either freeze the value once (`OnceLock`) or state the
    environment-stability requirement.

19. **Boot-row absence panics.**
    Python: `os/intel/cost_check.py:247-268` indexes
    `[row for ... ][0]`, raising `IndexError`.
    Rust: `lib.rs:1449` uses `.expect("boot row")`, panicking.
    Task: return `Result` so a malformed row set is a refusal, not a
    process abort.

20. **Dispatch path resolution.**
    Python: `os/intel/cost_check.py:194-245` walks up from
    `__file__` to the repo root.
    Rust: `lib.rs:1433-1442` uses `CARGO_MANIFEST_DIR` and
    `../../os/intel/prompts/dispatch.md`.
    Works in the checkout; breaks if the crate is built from a copied
    tree that does not carry `os/`.
    Task: one path resolver shared with the other crates that read
    `os/` fixtures.

## Not a gap

- `Value` has no tuple variant; Python's `budgets_from_snapshot`
  accepts a tuple (`budgets.py:162-184`), but no JSON snapshot produces
  one. Recorded so nobody “fixes” it by widening the value model.
- `py_repr` escapes only `\\`, `'`, `\n`, `\r`, `\t`; Python also
  escapes other control characters. The prompt text this crate prints
  never carries them; a hostile snapshot could. Tracked as a finding,
  not a task, until a caller needs it.
