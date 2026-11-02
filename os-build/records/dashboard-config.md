# `dashboard` — config surface (B152)

## Runtime configuration

| Kind | Count | Detail | Default | Refusal if wrong |
|---|---:|---|---|---|
| Environment variables | 0 | No `std::env` use in `src/lib.rs` or `src/contract.rs` | n/a | n/a |
| CLI flags | 0 | No `main`, no argument parsing, no binary target | n/a | n/a |
| Files read at runtime | 0 | No `std::fs`, no network, no stdin | n/a | n/a |
| Files written | 0 | Pure functions only | n/a | n/a |

## Compile-time inputs

| Input | Read by | Default | Failure mode |
|---|---|---|---|
| `crates/dashboard/fixtures/DASHBOARD_SPEC.md` | `tests/b15_spec_notes.rs`, `b15_parity.rs` (`include_str!`) | The carried spec | Missing/renamed file: test build fails to compile |
| `crates/dashboard/fixtures/DASHBOARD_SMOKE_CHECKLIST.md` | `tests/b15_parity.rs` | The carried checklist | Compile error |
| `crates/dashboard/fixtures/DSH-035-CROSS-BROWSER-CHECK.md` | `tests/b15_spec_notes.rs` | The carried log | Compile error |
| `crates/dashboard/fixtures/DEPLOY_RUNBOOK.md` | `tests/b15_parity.rs`, `b15_rollback_parity.rs` | The carried runbook | Compile error |
| `crates/dashboard/fixtures/DEMO.md` | `tests/b15_spec_notes.rs` | The carried demo notes | Compile error |
| `crates/dashboard/Cargo.toml` | Cargo | `name = "dashboard"`, `version = "0.1.0"`, `edition = "2021"`, no dependencies | `cargo -p dashboard` cannot find the package |

## Constants that act as configuration

| Constant | Value | Used by |
|---|---|---|
| `BRIEF_STALE_SECONDS` (`contract.rs:29`) | `7200` | `is_stale` |
| `BRIEF_KINDS` (`contract.rs:26`) | `morning`, `onjoin`, `ondemand` | `validate_brief_payload` |
| `VERDICTS` (`contract.rs:32`) | `build ok`, `build broken`, `unclear` | nothing (see finding 4 in `dashboard.md`) |
| `PALETTE_FOREGROUNDS` (`contract.rs:91`) | 6 named colours | contrast tests |
| `PALETTE_BACKGROUNDS` (`contract.rs:101`) | `#0d1117`, `#161b22` | contrast tests |
| `BRIEF_SECTION_ORDER` (`contract.rs:143`) | 5 section keys | titles/default-open tests |
| `ROLLBACK_STEPS` (`contract.rs:366`) | 4 step names | `rollback_runbook_ok` |

## What "wrong" means here

There is no runtime config to validate, so the refusal column is
mostly "not applicable". The only wrong-configuration failures are
build-time: a missing fixture, a renamed package, or a fixture edited
so a pinned assertion no longer matches. Those are refused by the
compiler or by the test, never silently accepted at runtime.
