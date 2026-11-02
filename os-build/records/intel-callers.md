# `crates/intel` — callers (B175)

Read from the tree at the time of this pass. "Caller" means code that
names the crate or a module in it. A name mentioned in prose is not a
caller.

## The short answer

**No production Rust code calls `crates/intel` today.**

- `crates/intel/Cargo.toml` declares no dependencies.
- The workspace lists it as a member (`Cargo.toml:12`), and no other
  member's `Cargo.toml` names `intel` as a dependency.
- A repo-wide search for `use intel::` finds hits only inside
  `crates/intel/tests/*.rs`.
- The one hit outside the crate is a string check, not a call:
  `crates/os-supervisor/src/drills/watchman_boot.rs:254` tests whether
  source text contains `"intel::push"`. It never resolves the crate.

The live intel path is still the Python package under `os/intel/`
(imported by `os/intel.py`, the e2e loops and the drill scripts). The
Rust crate is a port waiting for an adapter; wiring it in is not in
this task list.

## Callers inside the crate (the only compiled consumers)

Each integration test file imports the modules and states what it
expects. These are the expectations the crate must keep satisfying.

| Caller | Imports | What it expects |
|---|---|---|
| `crates/intel/tests/b09_parity.rs:7-8` | `b09_core::{capability, capability_files, explanations, gate, join, ladder, store}`, `capability::Grant` | The B09 behaviour equals the Python cases: grant validation, refusal records, ladder rungs, store keys. `cli`, `ingest`, `integration` are exercised inline (lines 41-227). |
| `crates/intel/tests/b10_parity.rs:3-6` | `b10_brief::{alerts, baton, brief, dispatch, forecast, notify, push, sections, wake}`, `BatonSpec`, `BriefRecord`, `Plan`, `PlanJob` | Brief records validate, announcements are frozen strings, plan parsing refuses bad jobs, push payloads validate. `window` is imported at line 207. |
| `crates/intel/tests/b11_parity.rs:4-5` | `b11_spark::{mind_image, mind_loader, skills_loader, spark_agent, spark_client}`, `Completion`, `CompletionRequest`, `SparkError`, `StubTransport`, `Transport`, `TransportKind` | Spark is never faked: an unconfigured client errors before sending; the two transports behave as the Python does; the stub is test-only. |
| `crates/intel/tests/b12a_parity.rs:24-28` | `b12a_drills::{boot_selfcheck, sam_check, security_pass, soak_review, watchdog_tuning}`, `deps::Thresholds`, `drills::demo_thresholds_dropin`, `sha256`, `value` | Drills are fixture-only, phases run in order, the `PASS` line prints on success, and the fixture JSON round-trips. |
| `crates/intel/tests/b13_parity.rs:6-7` | `b13_devpack::{alerts_feed, brief_entry, crew_board, plan_preview, AlertRow, PreviewJob, PreviewPlan}`, `serde_json_like::Json` | The pack shapers match the checked-in payloads; the order must cover exactly the plan's jobs; ties break stably. |
| `crates/intel/tests/b14_parity.rs:4` | `b14_trust::{launch_run, timer_sweep, trust}` | Verify-first launch refusal, unsigned/negative trust refusal, tick dedupe, expired-lease sweep, demo env profile. |

## Callers that are named but not built

`crates/intel/src/b12a_drills/deps.rs:1-20` says the B12a drills call
sibling modules owned by other batches — `intel.watchdog` /
`intel.thresholds` (B21, `os-supervisor`), `intel.gate` / `intel.store`
/ `intel.capability` / `intel.integration` / `intel.ladder` (B09),
`intel.baton` / `intel.brief` / `intel.dispatch` / `intel.push` /
`intel.wake` (B10), the Spark client (B11), and `intel.trust` /
`intel.timer_sweep` (B14).

In the Rust tree those are **traits** (`Watchdog`, `TimerSweep`,
`Trust`, `Wake`, `Ladder`, `SparkClient`, `BriefSurface`,
`DispatchSurface`, `AlertRecords`, `BootStatus`, `Capability`, `Gate`,
`Push`, `Baton`), not implementations. No adapter exists yet. So:

- Every drill runs against a test double, not against the real B09/B10
  modules. The drill *contract* is met; the cross-batch wiring is not.
- `Thresholds` is duplicated here (`deps.rs:66-176`) instead of using
  `os-supervisor`'s copy. When the adapter lands, one of the two must
  become the source of truth or the demo env can drift.

## Python callers still on the live path

The port does not replace these; they are listed so the adapter work
has a target.

| Python caller | Evidence | Expectation |
|---|---|---|
| Relay CLI `os/intel.py` | imports `intel.brief` (line 131), `intel.dispatch` (453-530), `intel.store` (596), `intel.ingest` (655) | Brief/dispatch/store/ingest shapes as documented; the CLI is the entry point. |
| `os/intel/e2e1.py` | lines 79, 151-186 | End-to-end loop reads ingest, composes a brief, posts a plan. |
| `os/intel/timer_sweep.py` | line 73 imports `intel.thresholds` | Sweep interval and lease defaults come from the shared thresholds module. |
| `os/intel/watchman_runner.py` | line 77 imports `intel.watchman_cycle` | Runner drives cycles; not ported in this crate. |
| `os/intel/drills/*.py` | e.g. `drills/boot_status.py:46`, `drills/trust_enforcement.py:31` | Drills import the real modules they exercise; the Rust drills use trait doubles instead. |
| `os/tests/test_intel_*.py` (many) | e.g. `test_intel_brief.py:16`, `test_intel_store.py:8`, `test_intel_trust.py:60` | The Python suite is the parity oracle the Rust tests mirror. |

## Expectations the crate does not meet

1. **No adapter to B09/B10/B21.** Drills compile against traits; the
   production modules that implement those traits do not exist as
   adapters. Expectation "run the drill against the real watchdog"
   fails today.
2. **No CLI or binary target.** Every Python caller above invokes a
   module; the Rust crate has no `[[bin]]` and no argument parser
   (the only CLI-shaped code is `b09_core::cli`, which is pure
   predicates).
3. **Live fallback still wins.** `os/intel.py` and the Python drills
   remain the only executable intel path, so a change in the Rust
   crate cannot affect production until wiring lands.
