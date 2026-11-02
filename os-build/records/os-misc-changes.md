# Changelog — `crates/os-misc`, since the port began

B216 deliverable. Built from the repository's own batch records and
port reports. **`git log` was not available in this slice**, so no commit
hash or date is invented here; every entry names the file that carries
the evidence, and the command to confirm it is at the bottom.

## Origin

| Change | Evidence |
|---|---|
| B00 created the Rust rebuild workspace and its member crates, including `os-misc` | `Cargo.toml:1-21`; `batches/B00.md:1-12` |
| B24–B30 were assigned to this shared crate, one subtree per batch | `BATCHES.md:58-64`, `:606-714`; `docs/RUST_REBUILD_PLAN.md:274-280` |

The crate's own header now says "Meta OS Rust rebuild" and "Batches
B24–B30 land here, each in its own subtree" (`src/lib.rs:1-6`); the
older "skeleton (B00)" wording is gone.

## Port arrivals (from the port reports)

| Batch | What landed | Evidence |
|---|---|---|
| B24 | `poll`, `presence`, `send`, `store`, `watch`, `watch_nick` modules with inline tests | `crates/os-misc/src/b24/**`; `batches/B24.md` |
| B25 | `announce`, `clipboard`, `edits`, `forward`, `paste`, `saved` modules with inline tests | `crates/os-misc/src/b25/**`; `batches/B25.md` |
| B26 | `admin`, `digest`, `export`, `health`, `timecapsule`, `webhook` modules with inline tests | `crates/os-misc/src/b26/**`; `batches/B26.md` |
| B27 | world-pack validator `b27/validate.rs` landed (report names commit `c8b2a325`, +367 lines) | `OPENCODE_PROMPT.md:27` |
| B27 | FDNY PAR clock ported into `b27/par_clock.rs` (T015) and parity T035 closed: 15 cases green against the real module, 3 CLI cases exclusion-blocked | `OPENCODE_PROMPT.md:29-31`; `OPENCODE_TASKS_REPORT.md:26` |
| B27 | worlds-pack parity T061 closed: 13 cases green against the real validator | `OPENCODE_TASKS_REPORT.md:52` |
| B27 | carry consts T016–T020 added; `os-misc` made a real dependency of `parity-tests` (not dev-only) | `OPENCODE_FINISH_REPORT.md:12-14` |
| B28 | 16 docs/role files inventoried as CARRIED, not ported | `crates/os-misc/src/b28/mod.rs:1-38` |
| B29 | 22 crew/demo/submission assets inventoried as CARRIED | `crates/os-misc/src/b29/mod.rs:1-42` |
| B30 | 12 lane-plan files inventoried as CARRIED | `crates/os-misc/src/b30/mod.rs:1-27` |

The last recorded test count for the crate in the port reports is 47
tests (`OPENCODE_FINISH_REPORT.md:115`); the inline modules still carry
47 `#[test]` functions today.

## This pass (Bond lane, 2026-11-02)

| Change | Files |
|---|---|
| Read the crate end to end and wrote the behaviour record, gap list, worked records, caller map, config table, failure drill and surface inventory | `os-build/records/os-misc.md`, `-gaps.md`, `-records.md`, `-callers.md`, `-config.md`, `-drill.md`, `-surface.md` |
| Added integration coverage: every refusal branch, the four named edge cases, and the zero-test transport module brought to the crate's best-covered depth | `crates/os-misc/tests/error_paths.rs`, `edge_cases.rs`, `gap_close.rs` |
| Doc/comment corrections where the code is right | none required beyond the report: no stale "skeleton" header remained in `src/lib.rs`; the seven findings in `os-misc.md` are statements about overstated or missing behaviour, not typos, and were **reported, not rewritten**, because each describes code that is not present (timecapsule requeue, webhook delivery) or dead code (`par_clock` helper) |

## Confirm the timeline

```
git log --oneline --follow -- crates/os-misc
git log --oneline -- crates/os-misc/src/b24 crates/os-misc/src/b25 \
  crates/os-misc/src/b26 crates/os-misc/src/b27
```

Append the real hashes and dates under "Port arrivals" when the log is
reachable; this record deliberately leaves them untyped rather than
guessed.

## Commit history (appended by coordinator, from git)

- 37c9a7e 2026-10-30 T020 [B27] verify-carried nypd pack — CARRIED
- e95d592 2026-10-30 T019 [B27] verify-carried hospital/mta packs — CARRIED
- f6cd517 2026-10-30 T018 [B27] verify-carried ems/fdny packs — CARRIED
- 90f6b82 2026-10-30 T017 [B27] verify-carried doe/dsny packs — CARRIED
- 4c77a60 2026-10-30 B27: par_clock runtime + T016 verify-carried — UNCOMPILED
- 2daef26 2026-10-30 B28: OS docs, roles and root docs CARRIED
- c8b2a32 2026-10-30 B27: world packs — UNCOMPILED
- 83f923b 2026-10-30 B26: bus bridges, digest and admin — UNCOMPILED
- 2d92895 2026-10-30 B25: bus messaging extras — UNCOMPILED
- 4d6b210 2026-10-30 B24: bus messaging core — UNCOMPILED
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
