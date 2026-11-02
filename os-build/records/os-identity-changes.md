# Changelog — crates/os-identity (B060)

**Source limitation, stated first.** This slice had no terminal, so
`git log` could not be read. The entries below come from the recorded batch
history in `BATCHES.md`, `batches/B18.md`, `batches/B00.md`, the crate
header, and `Cargo.toml`. Append the real commit history with:

```sh
git log --oneline --decorate -- crates/os-identity
```

Line counts are not estimated here; take them from the files with
`wc -l` when reporting the section on room 1.

## Recorded history

### B00 — crate created

- `crates/os-identity` added as a workspace member (root `Cargo.toml:15`;
  `batches/B00.md:9` lists it among the skeleton crates).
- At this point the crate carried only the batch header and doc comments;
  the title said "skeleton (B00)".

### B18 — capabilities port

- `os/mos/capabilities.py` ported behavior-for-behavior into
  `crates/os-identity/src/lib.rs` (`lib.rs:4-5` names the source).
- The port introduced the storage seam (`CapStore`, `lib.rs:200-217`),
  the in-memory implementation (`MemoryStore`, `lib.rs:484-570`), the
  typed record and error shapes (`AgentRecord` 114-170, `StoreError`
  178-187, `RegisterError` 221-238, `RegistryError` 242-261), and four
  documented deviations from Python in the header (`lib.rs:21-44`).
- Twenty in-crate tests landed with it (`lib.rs:574-938`).
- Batch state per `batches/B18.md`: `UNCOMPILED` until gate 1 and gate 2
  pass; no gate report for this crate exists in the tree read for this
  record. The batch's completion line is therefore still unproven.

### This pass (Bond lane, 2026-11-02)

No production logic changed. The changes are records, tests, and comment
corrections:

- Title corrected from "skeleton (B00)" to "port (B18)" — the code is a
  port with tests, so the old title was stale (B052).
- Header error-path claim qualified: per-job read failures return 0 here
  where Python propagates them; empty `MUSE_RELAY_CAPNS` also differs.
- `Config::from_env`, `active_claims`, and `is_fresh` docs corrected to
  match the code (empty namespace handling; per-job error behaviour; the
  i64 overflow caveat).
- Behaviour, gaps, record-shapes, callers, config, failure-drill, public
  surface, and this changelog written under `os-build/records/`.
- Three public-API integration test files added:
  `crates/os-identity/tests/error_paths.rs`,
  `edge_cases.rs`, `gap_close.rs`.

## Not changed

- `os/mos/capabilities.py` and every Python caller are untouched.
- No dependency was added to `crates/os-identity/Cargo.toml`.
- No public API was widened for the tests.

## Commit history (appended by coordinator, from git)

- 3a680b0 2026-10-30 B18: port identity & capabilities service to crates/os-identity (Milo, gate 1)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
