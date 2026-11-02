# `crates/os-supervisor` — callers and expectations (B019)

Every place in the repo that names this crate, what it expects, and
whether the crate meets it.

## The call graph inside the crate

The crate is a chain; each link calls the next. These are the real
callers of the public API today.

| Caller | Callee surface | Expectation | Met? |
|---|---|---|---|
| `watchman_bridge::watchman_tick` (`watchman_bridge.rs:159-196`) | `watchman_watch::watchman_watch_tick` | one journal record set per tick, inputs untouched | yes — returns `(records, new_journal)` |
| `watchman_loop::loop_cycle` (`watchman_loop.rs:383-…`) | `watchman_bridge::{fold_tick, snapshot_from_records, watchman_tick}`, `watchman_watch` | malformed lines skipped, failures reported not raised | yes |
| `watchman_cycle::run_cycle` (`watchman_cycle.rs:180-…`) | `watchman_loop::loop_cycle` | per-machine records plus diagnostics | yes |
| `watchman_runner::run_cycle_with_subprocess` (`watchman_runner.rs:283-…`) | `watchman_cycle::run_cycle`, `watchman_loop::parse_event_lines` | a non-zero run is discarded, timeout is a failure | yes |
| `watchman_service::default_cycle_fn` (`watchman_service.rs:219-264`) | `watchman_runner::run_cycle_with_subprocess` | the cycle is injectable; the default is the subprocess runner | yes |
| `watchman_service::serve_cycles` (`watchman_service.rs:265-443`) | `default_cycle_fn`, `watchman_watch` | stop when asked, never mutate caller inputs | yes |
| `watchman_boot::verify_boot_cycle` (`watchman_boot.rs:254-310`) | `post_boot_rings`, `sweep_mismatch` | rings reconciled against the sweep; counter ignored | yes |
| `drills/*` (e.g. `drills/watchman_bridge.rs:54-56`, `drills/watchman_cycle.rs:72-74`) | the chain modules above | drive each phase and return pass/fail | yes |
| `watchdog::tick` (`watchdog.rs:1866-1881`) | every `detect_*` in `DETECTORS` | one alert list per snapshot; a panicking detector is skipped | yes (`watchdog.rs:1813-1864`) |
| `thresholds::Thresholds::from_env` (`thresholds.rs:137-200`) | `parse_env_int` | silent fallback, no panic | yes |

## Outside the crate

| Caller | What it expects | Met? |
|---|---|---|
| Workspace member list `Cargo.toml:19` | the crate builds as `os-supervisor` | yes (single-crate check) |
| `crates/os-boot/src/cli.rs:115,162` | comments only: "the real implementation lives in the B21 crate (`os-supervisor`)" | it points at this crate; **no call** is made. Not a mismatch, but the seam is documentation, not code. |
| `crates/os-worker/src/lib.rs:43` | comment: worker restart/baton is B21's crate | no call; same documentation seam |
| `crates/intel/src/b12a_drills/deps.rs:5` | comment: watchdog lives in `os-supervisor` | no call |
| `os-build/aegis/SWEEP.md:24` | treats the crate as this tree's own code (skipped in the sweep) | yes; it is not shielded from the audit by the name |
| `SUPER_PROMPT.md:240-261`, `batches/B21.md` | the B21 port task set (T117-T136) | the modules exist; the batch report is not this file |

## Flag

No crate outside `os-supervisor` imports or calls its API. The only
consumers are the crate's own modules, drills, and tests. That is
expected while B21 is a library in progress, but it means:
**a green `cargo test -p os-supervisor` is the only external evidence
today**. Any claim that another program "uses the watchdog" is a
comment-derived claim, not a call-site fact. Named so no one reads the
`os-boot`/`os-worker` pointers as live integration.
