# Changelog — `crates/os-boot` since the port began (B012)

**Provenance limit, stated first:** this slice had no terminal, so `git log` was not available
and no commit hash or date below is quoted from git. The entries are reconstructed from the
repository's own records: `BATCHES.md:557-596`, `batches/B23.md`, `TASKS.md:189-191`,
`SUPER_PROMPT.md:279-290`, and the crate's source/test names. Anything that needs a commit
hash is marked **UNVERIFIED**.

## Timeline as documented

| Stage | What the records say | Evidence |
|---|---|---|
| B00 — workspace skeleton | `os-boot` was created as one member of the Rust rebuild workspace | `Cargo.toml:7-23`, `batches/B00.md:9` |
| B23 — port | The crate ports `os/mos/cli.py`, adds a real git backend for `review`/`merge`, and carries the `os/os/` deployment assets byte-identical | `BATCHES.md:557-596`, `crates/os-boot/src/lib.rs:52-56` |
| B23 tests | Test names mirror the Python roots `test_mos_gitops.py` and the CLI cases: 4 git tests, 16 CLI tests, 3 carried tests | `crates/os-boot/src/git.rs:189-243`, `cli.rs:845-1160`, `carried.rs:107-140` |
| Later report | `os_boot 23` appears in the per-crate test tally | `OPENCODE_FINISH_REPORT.md:114` |

## What changed, by module

### `src/lib.rs`

- Module set fixed at three: `carried`, `cli`, `git` (`lib.rs:58-60`).
- Header corrected in this pass: "skeleton (B00)" → "rebuild (B23)"; asset count 39 → 47.

### `src/carried.rs`

- Manifest grown in documented stages: T153 (10), T154 (10), T155 (10), T156 (9), Meta Custos
  stage 2 (4), metaos-loop (4) — 47 total (`carried.rs:24-88`).
- `CARRIED_COUNT` added as the single count constant (`:88`).
- `source_path` / `asset_path` added as the two path resolvers (`:91-101`).
- Three tests: count, byte identity per entry, unit-section shape (`:107-140`).
- Mode policy recorded: modes were normalized to 100644 by the fold, so byte identity is the
  criterion and no exec-bit assertion is made (`carried.rs:16-22`).

### `src/cli.rs`

- `os/mos/cli.py` ported as a library: every command is a `cmd_*` function returning
  `CliOutcome`, with `run_cli` as the dispatcher (`cli.rs:263-695`).
- Backend seams introduced as five traits instead of direct imports (`:85-217`), because the
  owning crates do not implement them.
- argparse replaced by a hand parser (`:482-536`); the approximations are documented
  (`:38-42`).
- 16 tests added, one per command family plus argument errors (`:845-1160`).
- Wording fixed in this pass: "not merged to main yet" → "none of them implements these traits
  on main yet" (`:31-36`).

### `src/git.rs`

- Real git backend added for the two CLI gitops operations (`git.rs:20-149`).
- Guard order pinned to the Python source: not-a-repo → branch==base → unknown branch for
  review; branch==base → dirty → unknown branch for merge (`:69-116`).
- `--no-ff` merge with the fixed message `Merge <branch> (MOS approved)` (`:121-124`).
- Four tests mirroring `test_mos_gitops.py` (`:189-243`).
- Two documented approximations: no timeout (Python has 120 s) and no `reject_branch` /
  worktree helpers (those live in `os-workspace`, `git.rs:9-14`).

## What did not change

- No binary target was added; the crate remains a library.
- No production backend implementation was added.
- No git timeout was added.
- The carried assets are still byte-identical copies; nothing in `os/os/` was rewritten.

## What a real `git log` should confirm (UNVERIFIED here)

1. The B23 port commit(s) and their dates.
2. Whether the 47-entry manifest grew in separate commits per group (T153-T156, Custos, loop)
   or landed at once.
3. Whether the header's "39 assets" was ever correct, or was stale from the moment the
   Custos/loop groups were added.
4. Whether any test count changed after `OPENCODE_FINISH_REPORT.md` recorded 23.

Run `git log --oneline -- crates/os-boot` and `git log -p -- crates/os-boot/src/carried.rs` to
fill these in; this record deliberately does not invent them.

## Commit history (appended by coordinator, from git)

- d44d8fc 2026-11-01 Merge rowan/custos at e4f8057: Meta Custos stages 1 and 2 plus RW-001 CT watcher. Conflict resolved tip, Milo gate-1 green. Pax re-verified on the merged tree: cargo 1412 pass 0 fail, node 1877 pass 56 known WKWebView fails, queue python 110 OK, officina 49 OK, custos python 32 OK.
- 55f6881 2026-11-01 Merge 8 non-overlapping branches into main (boss order 2026-11-01): hana/ui-fix-list, milo/tier-gate, hana/crew-ui-evidence, rowan/os-agent-loop, milo/officina (stages 1+2a), eval/taxonomy-defaults, hana/native-test-prep, feature/nearest-camera-handoff (package.json test list unioned), test-footage/weapons-fires-batch. Verified on merged tree: node 1933 tests 1877 pass / 56 fail (exact known WKWebView set), cargo 1412/0, queue python 110 OK, officina 43 OK, packs 9/9, loop harness 12/12.
- f7a5344 2026-10-30 B23: port boot CLI/gitops + carry 39 OS assets to crates/os-boot (Milo, gate 1)
- 87cb6dd 2026-10-30 B00: cargo workspace skeleton + batch map (Pax)
