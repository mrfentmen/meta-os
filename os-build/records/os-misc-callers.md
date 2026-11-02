# Callers of `crates/os-misc`

B211 deliverable. Every reference in the repo that calls or depends on
the crate, what it expects, and anything it expects that the crate does
not do.

## Build-level

| Caller | What it expects | Verdict |
|---|---|---|
| `Cargo.toml:18` | the crate is a workspace member | OK |
| `crates/parity-tests/Cargo.toml:14` | `os-misc = { path = "../os-misc" }` as a real dependency (not dev-only) | OK; the dependency is normal, so the parity tests link the real crate |
| `Cargo.lock:427` | package entry | OK |

## Parity tests — the only executable callers

### `crates/parity-tests/src/tests/test_worlds_pack.rs`

- `use os_misc::b27::validate as vp;` (`:10`).
- Calls `vp::validate_pack(&manifest)` on the shipped packs under
  `os/worlds/<pack>/pack.json` and on hand-built manifests.
- Expects 13 cases (`CASES`, `:16-28`): shipped packs validate, have
  docs, are honest `spec`, a valid manifest passes, missing key / bad
  status / local-alert-crossing / send-without-never-carries / unknown
  urgency / unknown serves / duplicate rank / bad severity fail.
- Expectation status: satisfied by the current public surface.
  `validate_pack` is exactly the function it calls; no caller asks for
  `validate_pack_at` or the CLI (gap G19), and the test does not call
  them.

### `crates/parity-tests/src/tests/test_fdny_par_clock.rs`

- `use os_misc::b27::par_clock as pc;` (`:13`).
- Calls `pc::new_state`, `enter_crew`, `complete_par`, `exit_crew`,
  `tick`, `render_alert`, and reads `DEFAULT_INTERVAL_SECONDS` /
  `DEFAULT_GRACE_SECONDS`.
- Expects 15 cases (`CASES`, `:18-33`), including enter-twice refusal,
  crew-id rules, exit-unknown refusal, quiet-before-interval, one event
  per cycle, grace escalation, completion reset, exit silencing,
  location on the life-safety event, input immutability, independent
  crews, and the FND-020 line shape.
- Three cases are **exclusion-blocked, named not dropped**
  (`EXCLUSION_BLOCKED`, `:34-39`): CLI show/lifecycle on disk, CLI bad
  crew exit 2, CLI state survives reopen. These are exactly gaps G20
  (no state I/O or CLI in the port). The caller does not expect them to
  pass today.

## Non-callers that name the crate

- `BATCHES.md:58-64` and `docs/RUST_REBUILD_PLAN.md:274-280` map
  B24–B30 to this crate — documentation, not code.
- `os-build/aegis/SWEEP.md:24` excludes the crate as "this tree's own
  crates" — an audit scope note, not a caller.
- `batches/B24.md`…`B30.md`, `TASKS.md`, `SUPER_PROMPT.md` give the
  batch commands (`cargo build/test -p os-misc`) — build instructions.
- `OPENCODE_PROMPT.md:23-31` records the B27 port state and the
  par_clock ownership. Historical notes.

## Flags

- **No production caller exists.** The crate is a library with no
  binary (`Cargo.toml:1-5`); no service, server or OS process calls it.
  "UNWIRED" in the behaviour record is literal.
- **No caller expects behaviour the crate lacks.** The two parity files
  are the only code callers, and both already name their missing CLI
  expectations as exclusion-blocked rather than asserting them.
