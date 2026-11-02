# `crates/agent-runtime` — changelog record (B108)

**Evidence limit, stated first:** this record was written by a worker
with no terminal and no git command. It is built from the repo's own
records — `BATCHES.md`, `batches/B04.md`, `batches/B07-report-wave1.md`,
`OPENCODE_FINISH_REPORT.md`, `SUPER_PROMPT.md` and the crate header —
not from `git log`. Commit ids below are the ones those records name.
A coordinator with git should append the exact `git log --follow --
crates/agent-runtime` trail; no commit id here is guessed.

## Timeline as recorded

| Order | What changed | Evidence in repo | Commit named |
|---|---|---|---|
| 1 | B04 spec opened: port `server/queue/trio_agent.py` into `crates/agent-runtime`, behaviour not redesign; original stays live until PORTED | `BATCHES.md:87-90`, `batches/B04.md:1-45` | — |
| 2 | B04 skeleton landed (claimed at batch level; crate builds as a library) | `Cargo.toml:8`, `Cargo.lock` package entry | `batch/B04 45a4833` per `batches/B07-report-wave1.md:10` |
| 3 | B04 gap closure: category-only `validate_stub` replaced with full `validate_assessment` mirroring `js/schema.js`; envelope product wired into the claim path; 3/3 tests | `OPENCODE_FINISH_REPORT.md:21`, `:24-28` | `a34e1c9` |
| 4 | B07 integration: `assess-server`'s private structural contract check replaced by `agent_runtime::validate_assessment` (single implementation) | `OPENCODE_FINISH_REPORT.md:36-40`, `crates/assess-server/src/main.rs:566-571` | not named |
| 5 | B07 wave-1 report counted agent-runtime at 2 tests at that point, then 3 after the validator vectors | `batches/B07-report-wave1.md:42`, `OPENCODE_FINISH_REPORT.md:57` | — |
| 6 | B097-B108 (this pass): eight records written; error/edge/gap-close tests added; two panic bugs fixed in `relay_notify_payload` and `finish_failed`; header and `now_iso` comments corrected to the code's real behaviour | this record set, `crates/agent-runtime/tests/` | uncommitted |

## Current state, from the files

- One library target, one source file (`src/lib.rs`, 470+ lines with
  tests), three existing unit tests (`lib.rs:391-470`).
- Public surface: 1 used function (`validate_assessment`), 5 unused
  exports (see `agent-runtime-surface.md`).
- Not carried: heartbeat, poll loop, relay POST, ISO timestamps (see
  `agent-runtime-gaps.md`).
- No caller constructs an `Agent`; the Python resident is still the
  only running implementation (`agent-runtime-callers.md`).

## What changed in this pass

| File | Change |
|---|---|
| `crates/agent-runtime/src/lib.rs` | Header now lists the not-carried rules; `now_iso` comment states epoch millis, not ISO; relay text capped at 500 chars on both branches; `finish_failed` caps by characters (500 result / 200 note); dead pre-build `env` removed from the test helper |
| `crates/agent-runtime/tests/error_paths.rs` | New: every refusal branch R1-R7 plus the claim race |
| `crates/agent-runtime/tests/edge_cases.rs` | New: empty id, empty image, duplicate serve, out-of-order claim, 500/200 caps, UTF-8 error |
| `crates/agent-runtime/tests/gap_close.rs` | New: untested validator branches and ISO-8601 boundary cases |
| `os-build/records/agent-runtime*.md` | New: behaviour, gaps, records, callers, config, drill, surface, changes |

No dependency was added, no public signature changed, and no existing
test was deleted. The two panic fixes are behaviour changes only on
inputs that previously panicked; the Python original already capped by
characters, so they move the port toward parity.

## Still open

- The coordinator should run `cargo test -p agent-runtime -j1` and
  record the count; this worker could not.
- Append the real `git log` trail (see the evidence limit above).
- G1-G4 (heartbeat, ISO timestamp, relay POST, poll loop) remain gaps,
  not work done here.

## Commit history (appended by coordinator, from git)

- a34e1c9 2026-10-30 FINISH: B04 gap — full ok-gating (validate_assessment per js/schema.js)
- 5d7ec68 2026-10-30 B07: wave-1 integration (B02-B05 ports over main B01+B06) + parity-tests E0119 seam fix — UNCOMPILED (gate 2 pending)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
