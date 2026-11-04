# Lane D test results — `cargo test --release -p <crate>` per crate with tests/ (2026-11-04)

Method: one log per crate in `crates/test-logs/<name>.log` (`EXIT=` = cargo's
exit code on the last line). Counts below are sums of every
`test result: ok. N passed; M failed` line in each log.
`agent-ops` has no `tests/` directory (library only) — nothing to run.

| Crate | cargo test exit | Passed | Failed | Note |
|---|---|---|---|---|
| agent-runtime | 101 | 46 | 1 | `section14_registry::registry_fixture_loads` fails: test loads the live `agents/registry.json`, whose entry 0 (`imperium-patrol`) has `"command": []`, rejected by `RegistryError("entry 0 (imperium-patrol) command must not be empty")` (`crates/test-logs/agent-runtime.log`). Data-vs-test drift outside `crates/`; not fixed by this lane. All other targets green (3+11+12+17+3). |
| assess-server | 0 | 46 | 0 | — |
| dashboard | 0 | 138 | 0 | — |
| guardrail | 0 | 49 | 0 | — |
| intel | 101 | 0 (none ran) | 0 (compile) | `tests/edge_cases.rs` + `tests/error_paths.rs` do not compile: E0063 missing field `req` in `PlanJob` and missing field `summary` in `b10_brief::dispatch::Plan` (`crates/test-logs/intel.log:23-62`). Lib itself builds; the two stale test files block the whole `cargo test -p intel` run. Pre-existing; not fixed by this lane. |
| os-boot | 0 | 62 | 0 | — |
| os-budget | 0 | 125 | 0 | — |
| os-identity | 0 | 59 | 0 | — |
| os-jobs | 0 | 181 | 0 | — |
| os-memory | 0 | 72 | 0 | — |
| os-misc | 0 | 83 | 0 | — |
| os-supervisor | 0 | 433 | 0 | — |
| os-worker | 0 | 133 | 0 | — |
| os-workspace | 0 | 77 | 0 | — |
| parity-tests | 0 | 237 | 0 | — |
| queue-core | 0 | 54 | 0 | — |
| queue-store | 0 | 48 | 0 | — |
| relay | 0 | 66 | 0 | Rust-side unit/parity tests only; HTTP contract vs Node in `crates/verify-logs/relay-blackbox.log`. |
| stack | 0 | 43 | 0 | — |

Totals: 17 crates fully green (1,899 passed, 0 failed); `agent-ops` has no
test targets; `agent-runtime` 46/47 (1 data-drift failure); `intel` 0 run
(2 test files fail to compile).
