# `os-jobs` — changelog of the port, from the checked-in record

B036. What changed since the port began, in behaviour terms. The
sources are the repository's own batch records, not memory:
`BATCHES.md` §B16 (line 453), `batches/B16.md`, `TASKS.md:173-174`,
`SUPER_PROMPT.md` T092-T096, and the crate's module header
(`crates/os-jobs/src/lib.rs:1-70`). No commit hashes are invented here;
this slice could not read git history, so the ordered record below is
what the tree itself states. A coordinator with git access should append
`git log --oneline -- crates/os-jobs` output rather than reconstruct it.

## 1. B00 — the workspace skeleton

- `Cargo.toml:16` added `crates/os-jobs` to the workspace.
- The crate existed as a doc-comment skeleton: no logic, no tests, the
  header said "Skeleton only: no logic yet" (`batches/B00.md` lists
  `os-jobs` among the created members).
- Behaviour: none. The package compiled empty.

## 2. B16 — the port from `os/jobs.py`

- The Python command layer was ported: `post`, `list`, `show`, `attach`,
  `claim`, `heartbeat`, `progress`, `done`, `blocked`, `cancel`,
  `requeue`, `sweep`, `verify` (`lib.rs:1343-2275`).
- The pure helpers came with it: room cleaning and bus keys, URL
  quoting, SHA-256 and HMAC-SHA256 from scratch, canonical v1/v2
  payloads, artifact references, keyring parsing, id validation
  (`lib.rs:319-812`).
- Two seams replaced the Python globals: `JobStore` for Upstash
  (`lib.rs:151-176`) and `Clock` for time (`lib.rs:102-140`). This is
  the change that makes the crate testable without a server, and the
  change that means no server is spoken to.
- The brief environment surface was ported at the same time:
  `environment_jobs_record`, `environment_lines`, and the four
  not-reported lines (`lib.rs:2281-2597`), because
  `test_intel_brief_environment_jobs.py` was in the batch.
- The five named Python test files were ported as one in-crate `mod
  tests` with 102 cases and the same name roots
  (`lib.rs:2604-4347`). The header records the cases that are
  exclusion-blocked (message surfaces, brief composer) rather than
  faked.
- Behaviour change against Python: none in the command outcomes the
  tests pin; three deliberate differences are named in the header and in
  `os-jobs-gaps.md` (no transport, `u64` artifact versions, a
  non-CSPRNG nonce).

## 3. This lane (B025-B036)

- **Header corrected** (`lib.rs:1-70`): the duplicated B00 paragraph and
  the false "Skeleton only: no logic yet" claim were replaced with the
  port status. This is a doc-only change; no code moved.
- **Error-path tests added** (`tests/error_paths.rs`, 55 tests): every
  store-failure and refusal branch that the in-crate `FakeStore` could
  not reach, using a `FaultStore` wrapper over the public `JobStore`
  trait.
- **Edge-case tests added** (`tests/edge_cases.rs`, 6 tests): empty
  input, a 64 KiB spec, duplicate artifact refs, same-second index
  ordering, duplicate deps, zero attempt budget.
- **Encoding gap closed** (`tests/gap_close.rs`, 13 tests): the
  one-test `encoding_tests` group now has the quoting, escaping,
  hashing, keyring, and canonical-payload cases it lacked.
- **Records added** under `os-build/records/`: this file plus the
  behaviour record, gaps, worked shapes, callers, config, drill, and
  surface inventory.

## 4. Not changed, and why

- No store transport, no CLI, no bus sender: those are G1/G3/G6 in
  `os-jobs-gaps.md`, and each needs a dependency or an integration
  decision this batch cannot make.
- `DEFAULT_NS` and `PRESENCE_TTL`: left in place. Removing public
  constants is a breaking change, and the second is asserted by a test.
- The `attempts` strictness divergence: left as the Rust behaviour the
  code documents (G10); changing it would change the command contract.

## Behaviour summary in one line

Before B16 the crate did nothing; after B16 it ports the Python queue's
commands and pure helpers with two injectable seams and 102 tests; this
lane hardens the refusal paths and records the behaviour without adding
a transport.

## Commit history (appended by coordinator, from git)

- 98a4d65 2026-10-30 B16: port jobs service to crates/os-jobs (Milo, gate 1)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
