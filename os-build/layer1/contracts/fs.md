# fs — contract (Round 7 B, refreshed 2026-11-02)

**RUNS** as a host process against a RAM block device; nothing boots it. 128 inodes,
64 blocks fixed at format time, no journal, no heap.

## Inputs

| Input | Accepts | Refuses |
|---|---|---|
| `fs_format(n)` | `DATA_START+4 ≤ n ≤ MAX_DISK_BLOCKS` (64) | too small / too big → `E_INVAL`; unmounted/absent device → `E_STATE` |
| `fs_mount()` / `fs_umount()` | a formatted image | bad magic → `E_INVAL`; wrong version or geometry → `E_STATE`; CRC mismatch → `E_VERIFY`; double umount → `E_STATE` |
| `fs_create(parent, name, kind)` | `kind` ∈ {`MODE_FILE`, `MODE_DIR`}; name 1..`MAX_NAME`; parent is a live directory | name too long → `E_INVAL`; parent is a file → `E_INVAL`; duplicate name → `E_STATE`; inode table full → `E_NOROOM` |
| `fs_write(ino, off, src)` | up to `MAX_FILE_BLOCKS` × 512 bytes per file | past the block budget → `E_NOROOM`; disk full → `E_NOROOM` |
| `fs_read(ino, off, out, cap)` | a file inode | not found → `E_NOTFOUND` |
| `fs_resolve(start, path, want_dir)` | absolute or relative, `.` and `..` | traversal through a file → `E_INVAL`/`E_NOTFOUND`; unmounted → `E_STATE` |
| `fs_sync()` | mounted | unmounted → `E_STATE` |

## Outputs

- `fs_stats() → (free_blocks, writes, code)` — **free first**, not last.
- `fsck_run(report) → (problems, code)`; `fsck_clean(report)` is the single
  definition of "clean". `fsck_fix` repairs orphans, leaks and the free count, and
  **refuses** to repair duplicates, bad entries or out-of-range pointers — those are
  decisions, not repairs.

## Limits

MAX_NAME 12, MAX_FILE_BLOCKS 5, MAX_INODES 128, MAX_DISK_BLOCKS 64, FS_MAX_DEPTH 16
(**DEAD** — see below). All exercised or explained; `LIMITS.md` has the table.

## Failure modes proven

| Case | Result | Driver |
|---|---|---|
| block 0 zeroed | mount `E_INVAL` (magic checked first) | `t82_fs_deep` |
| valid CRC, wrong version | mount `E_STATE` (version is checked, not implied) | `t82_fs_deep` |
| one byte changed under a stale CRC | mount `E_VERIFY` | `t82_fs_deep` |
| name of MAX_NAME+1 | `E_INVAL`, nothing created | `t82_fs_deep` |
| duplicate name | `E_STATE`, original untouched | `t82_fs_deep`, `t65_fs` |
| resolve through a file | fails, no partial walk | `t82_fs_deep` |
| disk filled | `E_NOROOM`, free count 0, no wrap onto block 0 | `t80_limit_drivers2` |

## Restart semantics

`fs_umount()` + `fs_mount()` is the restart, and it is a real one: every global is
rebuilt from block 0. Proven by transcript — a file written before the cycle
resolves afterwards, reads back byte-identical, the free-block count returns as
synced (52), and `fsck_run` reports 0 problems. The data survives because the RAM
backend outlives the mount; a reboot does not keep it.

## The DEAD limit

`FS_MAX_DEPTH = 16` is declared and **never read**. A path of any depth is accepted
as long as inodes remain (128). Either enforce it in the resolver or delete the
constant; both change frozen source, so it is reported, and `LIMITS.md` marks it
DEAD rather than letting it read as coverage.

## Drivers

`t65_fs` (76 checks, functional), `t82_fs_deep` (35 checks, adversarial),
`t80_limit_drivers2` (inode and block caps), `t77_gaps` (fsck on damaged images).
