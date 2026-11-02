# Callers — `crates/os-workspace`

Method: repo-wide text search on `main` @ `6d8d54e` for the crate name
(`os-workspace`, `os_workspace`) and for its public entry points
(`artifact_store`, `review_branch`, `approve_merge`, `reject_branch`,
`worktree_add`, `run_cli`). Result: **no crate or program imports
`os_workspace` today**. Every mention is either the workspace manifest, a
document, or another crate's comment.

## What expects this crate — and what it actually gets

| Caller | Where | Expectation | Accurate today? |
|---|---|---|---|
| Cargo workspace | `Cargo.toml:21` | member builds | Yes |
| Parity test, OS-083 | `crates/parity-tests/src/tests/test_os083_artifact_store.rs:6-8`, `34-46` | "os-workspace crate is still the B00 skeleton", 11 store cases exclusion-blocked | **No** — the port exists; the cases can now run against it |
| Parity test, OS-094 | `crates/parity-tests/src/tests/test_os094_job_artifacts.rs:6-8`, `23-33` | "os-jobs crate and os-workspace crate are still B00 skeletons", 9 cases blocked | **No for this crate** — the store half exists; the jobs-record half is still absent |
| Supervisor comment | `crates/os-supervisor/src/overseer.rs:20` | os-workspace API "being written in parallel" | **No** — it is written; nothing calls it |
| Boot crate comment | `crates/os-boot/src/git.rs:15` | B19 crate ports the full gitops module | Yes |
| Boot crate backend | `crates/os-boot/src/cli.rs:200-217` | its own `GitopsBackend` trait for review/merge | Yes — and it duplicates this crate's `review_branch`/`approve_merge` rather than depending on them |
| Boot changelog | `os-build/records/os-boot-changes.md:55` | worktree helpers live in `os-workspace` | Yes |
| Batch map | `batches/B19.md:4-6`, `BATCHES.md:472` | crate target and parity rule | Yes |
| Task map | `TASKS.md:181`, `SUPER_PROMPT.md:220-225` | B19 port tasks | Yes |
| Aegis sweep | `os-build/aegis/SWEEP.md:24` | crate skipped as this tree's own | Yes |

## Callers that would break if the API moved

None outside the crate. Inside the crate:

- `review_branch` and `approve_merge` are used by the in-file gitops tests
  (`lib.rs:2193-2281`); no other function calls them.
- `run_cli` is used only by the CLI tests (`lib.rs:2134-2185`) and the new
  integration tests. There is no `[[bin]]`.
- `worktree_add` / `worktree_remove` have no caller except the last in-file
  test (`lib.rs:2269-2281`) and `tests/gap_close.rs`.

## Flagged mismatches

1. **The parity tests still describe this crate as a skeleton.** That is the
   one concrete caller expectation the crate does not meet. The OS-083 cases
   are now runnable: `deposit and read round trip`, `binary bytes survive
   versioned read`, `versions increment and history counts`, `identical
   redeposit is a noop`, `nested artifact path`, `traversal names refused`,
   `bad job ids refused`, `list sorted and empty job empty`, `read missing
   artifact and bad version raise`, `attach copies record and carries paths`,
   `cli deposit and list`, `cli bad command exits two`.
   Task for the parity owner: point those cases at `os_workspace` and drop the
   exclusion label; do not edit `parity-tests` from this lane.
2. **Two gitops implementations exist**: this crate's `review_branch` /
   `approve_merge` and `os-boot`'s `GitCliBackend` (`os-boot/src/git.rs:64-126`)
   behind its own trait. Neither calls the other. Nothing has broken yet, but
   a fix in one will not reach the other. Reported, not merged, because both
   are other owners' surfaces.
3. **No production construction of the store.** `STORE_ROOT_DEFAULT`
   (`lib.rs:713`) names the image path, but no caller passes it; the image
   scripts create the directory (`os/os/build-image.sh:127-138`) and the crate
   is never invoked there. A booted image would still have an empty store until
   some program calls `deposit`.
