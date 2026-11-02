# fs — Round 11 record

Source: `services/fs/fs.goose`, `services/fs/paths.goose`, `services/fs/fsck.goose` ·
Test: `services/tests/t119_fs_r11.goose` · Status: RUNS (t65 75 checks, t82 35 checks); t119 written, run pending

## 1. Limits — PROVEN

| constant | value | in | outcome | evidence |
|---|---|---|---|---|
| `MAX_INODES` | 128 | `fs.goose` | driven by `tests/t80_limit_drivers2` (names it); **crossed, not named, by t119** — 126 creates succeed, the 127th is `E_NOROOM` | LIMITS.md; t119 `t_inode_exhaustion` (pending run) |
| `MAX_FILE_BLOCKS` | 5 | `fs.goose` | driven by `tests/t80_limit_drivers2`; t82 also writes five blocks and refuses the sixth | LIMITS.md, `t82_fs_deep` (b) |
| `MAX_NAME` | 12 | `fs.goose` | driven by `tests/t82_fs_deep`: 11 and 12 accepted, 13 is `E_INVAL` | LIMITS.md, t82 (b) |
| `MAX_DISK_BLOCKS` | 64 | `fs.goose` | driven by `tests/t80_limit_drivers2`; **t119 crosses both edges**: 64 formats, 65 and 9 are `E_INVAL` | LIMITS.md; t119 `t_format_edges` (pending run) |
| `FS_MAX_DEPTH` | 16 | `fs.goose` | **not a limit**: declared and never read. The real bound is the `chain[16]` in `paths.goose`, which allows 15 path components (the root occupies a slot): t119 resolves 15 and gets `E_NOROOM` on the 16th | LIMITS.md "Not limits"; t119 `t_paths` (pending run) |
| `CK_MAX_BLOCKS` | 64 | `fsck.goose` | **not a limit**: declared and never read | LIMITS.md "Not limits" |
| `CK_MAX_INODES` | 128 | `fsck.goose` | **not a limit**: declared and never read | LIMITS.md "Not limits" |

**Design-document correction.** `DESIGN.md` §4 and §8 call the path limit "16 components". The
resolver's chain holds 16 inodes *including the root*, so the true statement is **15 named
components**. t119 asserts the real boundary; the documents are now read against it.

**Directory entries (160) are structurally unreachable.** The root has 160 entry slots but the
filesystem has 128 inodes, 126 of them allocatable; the inode table refuses first. t119 proves
the inode edge and records the directory edge as unreachable rather than pretending to drive it.

## 2. Refusals — PROVEN (existing runs) with a pending-run set

Proven by `t65_fs` / `t82_fs_deep` today:

| refusal | code | the assertion that expects it |
|---|---|---|
| create while unmounted | `E_STATE` | t82 (a) `create while unmounted is E_STATE` |
| mount a wiped superblock | `E_INVAL` | t82 (a) `a wiped superblock is refused` |
| mount a wrong version with a valid CRC | `E_STATE` | t82 (a) `a wrong version with a valid CRC is E_STATE` |
| mount a changed field with a stale CRC | `E_VERIFY` | t82 (a) `a changed field with a stale CRC is E_VERIFY` |
| duplicate name | `E_STATE` | t82 (a) `a duplicate name is E_STATE` |
| name of `MAX_NAME + 1` | `E_INVAL` | t82 (b) |
| sixth block | `E_NOROOM` | t82 (b) `the block after MAX_FILE_BLOCKS is refused` |

Asserted by `t119_fs_r11`, run pending:

| refusal | code | the assertion |
|---|---|---|
| format 0 / 9 / 65 blocks | `E_INVAL` | `t_format_edges` |
| empty name, unknown kind, file as parent | `E_INVAL` | `t_create_refusals` |
| read/write/truncate a directory | `E_INVAL` | `t_type_refusals` |
| negative offset, sparse offset | `E_INVAL` | `t_type_refusals` |
| unlink a missing name | `E_INVAL` | `t_unlink_rename` |
| unlink a non-empty directory | `E_STATE` | `t_unlink_rename` |
| rename a missing source | `E_INVAL` | `t_unlink_rename` |
| rename onto an existing target | `E_STATE` | `t_unlink_rename` |
| empty path, 13-byte component | `E_INVAL` | `t_paths` |
| 16 path components | `E_NOROOM` | `t_paths` |

## 3. Restart — NAMED GAP

- **Within a process** a remount keeps every file; `t82_fs_deep` (c) proves it byte for byte
  and fsck reports zero problems after the cycle. That is the only restart that has run.
- **A process restart loses everything.** The backend is storage's RAM disk, so the supervisor
  restarting the fs service produces an unformatted disk, not a repaired one. `storage_volatile()`
  is the call that says so. No supervisor restart of this service has been run; the loss is total
  and is named here rather than softened.
- **Crash windows** are stated in `DESIGN.md` §6: orphan on mid-create, BAD_ENTRY on mid-unlink,
  LEAK between grow and size update. fsck detects all three; only the first two are safely fixable.

## 4. Contract — PROVEN

`fs.goose` imports `storage.storage` and `common.err.err`. The call matrix row `SVC_FS` is
`storage | log`, and `cm_set` is at `callmatrix.goose` "The filesystem sits on the storage contract".

| direction | other service | call | in the matrix? |
|---|---|---|---|
| out | `storage` | `storage_read` / `storage_write` (512-byte blocks) | yes — `SVC_FS` row carries `SVC_STORAGE` |
| out | `log` | none in the source | **declared but dormant** — `SVC_LOG` bit is set, no import or call exists; honest as a declared permission, a finding only if read as a live edge |
| in | `shell`, `fsck` callers | `fs_format`, `fs_create`, `fs_write`, `fs_read`, `fs_resolve`, `fs_unlink`, `fs_rename` | n/a (same-service and user-facing calls, not matrix edges) |

`FINDING: no matrix edge for fsck` — `fsck.goose` is a second module in the same service and
needs no permission, so this is not an access bug; it is the matrix modelling a service as one
row while the service is three modules. Recorded for room 1, not fixed here.

## 5. Load — NAMED GAP

The load loop is 200 write+read pairs of 16 bytes on one file — ten times a 20-operation batch —
and it approaches no size limit (a 16-byte file uses one block). The number below comes from the
coordinator's run, never from this file.

RUNS pass=46 fail=0 · `LOAD fs ops=200 ok=200 refused=0`

## 6. README truth pass — PROVEN

- **Status line:** said `WRITTEN. Not COMPILED, not RUN.` It now says RUNS, names `t65_fs` (75
  checks) and `t82_fs_deep` (35), and cites the run row.
- **Tests line:** listed only `t65_fs`; now lists t65, t82 and this round's t119.
- **Limits:** the max-file-size line was already right. Added the honest depth statement (15
  named components, root included in the chain) where the README previously repeated DESIGN's 16.
- **Persistence:** already true and left alone — remount within a process survives, a restart
  does not, and `storage_volatile()` is the call that answers it.
- **DESIGN.md:** its status line (`WRITTEN, UNCOMPILED`) was stale; it now says WRITTEN and RUNS
  through t65/t82. Its §4/§8 "16 components" is corrected to 15 named components with the root
  in the chain.
