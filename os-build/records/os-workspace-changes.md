# Changelog — `crates/os-workspace`

## Method (read this first)

This worker had no terminal, so a path-filtered `git log` could not be run.
The entries below are reconstructed from the files on `main` @ `6d8d54e`:
`batches/B00.md`, `batches/B19.md`, `BATCHES.md`, the crate header, and the
tests present in the tree. They are ordered by what the tree proves, not by
invented dates. To replace this with the authoritative history, run:

```sh
git log --oneline --follow -- crates/os-workspace
git log --stat -- crates/os-workspace
```

and correct any entry whose commit message disagrees.

## 1. B00 — the skeleton

- `crates/os-workspace` was created as a workspace member with only
  `Cargo.toml` and a doc-comment `lib.rs` (`batches/B00.md:10`,
  `Cargo.toml:21`). The header still said "skeleton (B00)"; it was corrected
  in this pass (`lib.rs:1-38`).
- No logic, no tests at this point.

## 2. B19 — the port

- `os/mos/artifact_store.py` and `os/mos/gitops.py` were ported behavior for
  behavior into one module (`lib.rs:1-38`, `698-1631`), per
  `batches/B19.md:4-15` and `BATCHES.md:472`.
- Added with the port, all std-only:
  - `JsonValue` + parser/serializer for manifests (`lib.rs:90-553`);
  - SHA-256 with NIST vectors (`555-633`);
  - timed git runner with reader threads (`641-711`);
  - artifact store: deposit, list, read, history, attach, CLI (`698-1405`);
  - gitops: review, approve/merge, reject, worktrees (`1407-1631`).
- 35 in-file `#[test]` cases came with it, covering the store, CLI, JSON,
  SHA-256, and gitops.
- The port was never wired to a program: no `[[bin]]`, no caller outside the
  crate (`os-workspace-callers.md`).
- The parity tests written before the port still describe the crate as a
  skeleton (`crates/parity-tests/src/tests/test_os083_artifact_store.rs:6-8`,
  `test_os094_job_artifacts.rs:6-8`). That is a stale description, not a
  change to this crate.

## 3. 2026-11-02 — Section 8 records pass (this branch)

Production logic unchanged. Changes are docs and tests only:

- **Docs corrected where the code is right (B088):**
  - header no longer says "skeleton"/"no logic yet"; it states the port and the
    missing binary (`lib.rs:1-12`);
  - the JSON byte-compat claim is qualified, with the parser differences
    listed in `os-workspace.md` finding 2 and `os-workspace-gaps.md:gaps 9-11`;
  - `STORE_ROOT_DEFAULT` documented as informational (`lib.rs:710-713`);
  - `AttachedArtifact` documented as a shape `attach` does not construct
    (`lib.rs:753-758`).
- **JSON test-gap close (B095):** 4 new in-file tests, so the parser has 6
  (the same count as gitops): escapes/surrogate pairs, numbers/nesting/
  literals, malformed escapes, compact serialization order
  (`lib.rs:2077-2118`).
- **New integration tests (B086, B087, B095):**
  - `tests/error_paths.rs` — 15 cases, exact refusal messages;
  - `tests/edge_cases.rs` — 9 cases, empty/maximum/duplicate/out-of-order;
  - `tests/gap_close.rs` — 9 cases, gitops/CLI paths.
- **New records (B085, B089-B094, B096):** `os-workspace.md`,
  `os-workspace-gaps.md`, `os-workspace-records.md`,
  `os-workspace-callers.md`, `os-workspace-config.md`,
  `os-workspace-drill.md`, `os-workspace-surface.md`, this file.

## Not changed

- No public signature changed.
- No dependency added (`Cargo.toml` still has no `[dependencies]`).
- No Python original touched.
- No behaviour "fixed" for parity; the gaps are listed, not papered over.

## Commit history (appended by coordinator, from git)

- dba1859 2026-10-30 B19: port workspace & artifact store to crates/os-workspace (Milo, gate 1)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
