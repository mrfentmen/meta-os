# `dashboard` — callers (B151)

## Who links the crate

| Caller | Where | What it expects |
|---|---|---|
| Workspace build | `Cargo.toml:10` (`"crates/dashboard"`) | The package builds as a workspace member; nothing else |
| Parity tests | `crates/dashboard/tests/b15_crewboard.rs:12`, `b15_parity.rs:60`, `b15_spec_notes.rs`, `b15_rollback_parity.rs`, plus this pass's `error_paths.rs`, `edge_cases.rs`, `gap_close.rs` | `use dashboard::contract::*`; every rule and record shape named in `dashboard.md` |
| In-file unit tests | `crates/dashboard/src/contract.rs` (`#[cfg(test)] mod tests`) | Seven checks over brief payloads, staleness, verdicts, deep links, demo mode and today counts |

**No production crate depends on `dashboard`.** A search for
`dashboard::` / `use dashboard` across the repo returns only the test
files above; no `Cargo.toml` in `crates/*` lists it as a dependency.
The crate has no binary target, so there is no runtime caller either.

## Documentation and tooling that names it

| File | Line | What it says |
|---|---|---|
| `BATCHES.md` | 49 | B15 owner Hana, crate `crates/dashboard`, 31 parity cases |
| `BATCHES.md` | 419-431 | The batch contract: port the spec, viewer excluded, `cargo test -p dashboard` |
| `TASKS.md` | 226 | B15 is the dashboard backend contract |
| `SUPER_PROMPT.md` | 409-418 | T236-T243: contract, five crewboard test files, the dashboard test files, compile fix |
| `batches/B15.md` | 1-7 | Source-file list and the "do not invent a viewer" trap |
| `os-build/aegis/DRILL.json` | 32 | Names `crates/dashboard/Cargo.toml` as an audited path |

## Callers that would expect something the crate does not do

None today. The only documented omission is the web viewer (G1 in
`dashboard-gaps.md`), and every doc above states that exclusion
explicitly. The first future production caller would be a server or
viewer that reads these rules; it does not exist in this tree.

One stale name worth flagging: the crate header used to call itself
"skeleton (B00)" with "no logic yet", which would mislead a caller
looking for an empty placeholder. This pass corrected it
(`crates/dashboard/src/lib.rs:1`).
