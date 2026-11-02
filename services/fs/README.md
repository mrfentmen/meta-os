# fs — MOSFS01 (B-L1-79..86)

A real filesystem over the block contract: superblock, allocation bitmap, inode
table, directory entries, path resolution, and an fsck-style checker.

| File | What it is |
|---|---|
| `DESIGN.md` | the layout, the limits, and the crash story — read this first |
| `fs.goose` | format, mount, allocate, inodes, files, directories (B-L1-80..82) |
| `paths.goose` | path parsing and resolution, hostile cases included (B-L1-83) |
| `fsck.goose` | consistency checker and its safe repairs (B-L1-86) |

**Status: RUNS** as a host process: `tests/t65_fs` (75 checks) and
`tests/t82_fs_deep` (35 checks), both exit 0. Round 11 adds `tests/t119_fs_r11`
(refusal catalogue, inode exhaustion, path depth).

## Limits, stated up front

- Max file size **2560 bytes** (5 direct blocks, no indirect blocks).
- Max directory **160 entries**; max name **12 bytes**.
- Max path depth **15 named components**. The resolver's chain holds 16 inodes
  including the root; the 16th *name* is `E_NOROOM`.
- Two 512-byte scratch blocks shared by the whole module — safe only because
  services are single-threaded by contract (`fs.goose`, first paragraph).

## Persistence: none, and it says so

The backend is `storage`'s RAM disk. A remount **within one process** keeps your
files; a restart does not. `storage_volatile()` is the call that answers this,
and `DESIGN.md` §7 is the paragraph that does not hide it.

Binding to a real Layer 3 block driver is B-L1-74 and changes nothing here: the
FS talks `storage_read` / `storage_write` and nothing else.

Tests: `services/tests/t65_fs.goose` (round trip, hostile paths, remount, checker
on a clean tree and on a planted leak), `services/tests/t82_fs_deep.goose`
(corruption injection, name and block boundaries, remount) and
`services/tests/t119_fs_r11.goose` (every reachable refusal with its code, inode
exhaustion, the real path-depth edge).
