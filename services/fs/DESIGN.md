# FS design — MOSFS01 (B-L1-79)

A real filesystem, laid directly over the block contract in
`services/storage/storage.goose` (`storage_read` / `storage_write`, 512-byte
blocks). Not a path table, not a mock: blocks, inodes, a bitmap and directory
entries, with an fsck that can be wrong in a way you can see.

Status: **RUNS** through `tests/t65_fs` (75 checks) and `tests/t82_fs_deep`
(35 checks). The RAM backend is real storage and volatile — see §7.

## 1. The layout

64 blocks (32 KiB) is the RAM backend's whole disk, so the layout is sized for
that and states its limits rather than pretending to a bigger disk.

| Block(s) | Contents | Bytes |
|---|---|---|
| 0 | superblock | 512 |
| 1 | allocation bitmap | 512 (4096 block bits) |
| 2–9 | inode table, 16 inodes per block | 4096 (128 inodes) |
| 10–63 | data blocks | 27,648 |

All integers are **little-endian**, written and read by hand (`g16`/`g32`,
`p16`/`p32` in `fs.goose`). Hand-rolled rather than `binary` from the stdlib
because the on-disk format is the one thing in this layer that must never
silently change with a library version, and 20 lines of shift-and-or is auditable
in a way a library call is not.

### Superblock

| Offset | Field | Type |
|---|---|---|
| 0 | magic `MOSFS01` | 8 bytes |
| 8 | version (1) | u32 |
| 12 | block_size (512) | u32 |
| 16 | block_count | u32 |
| 20 | inode_start (2) | u32 |
| 24 | inode_blocks (8) | u32 |
| 28 | data_start (10) | u32 |
| 32 | data_blocks | u32 |
| 36 | free_blocks | u32 |
| 40 | root_ino (1) | u32 |
| 44 | crc32 of bytes 0..44 | u32 |
| 48–511 | reserved, must be zero | |

Mount checks magic, version, the CRC, and that the layout fields agree with the
constants in the source. A superblock that parses but describes a different
layout is rejected — a filesystem that mounts "mostly right" is how blocks get
written over.

### Inode (32 bytes, 16 per block)

| Offset | Field | Type |
|---|---|---|
| 0 | mode: 0 free, 1 file, 2 dir | u16 |
| 2 | links | u16 |
| 4 | size in bytes | u32 |
| 8 | direct[5] block numbers | 5 × u32 |
| 28–31 | reserved | |

**No indirect blocks.** A file is at most 5 × 512 = 2560 bytes. That is a
stated limit, not an oversight: adding an indirect block doubles the mount-time
validation work and the fsck's traversal, and nothing in Layer 4 writes a file
bigger than a log page. The limit is checked at write time and returns
`E_NOROOM`, so it is a refusal rather than a silent truncation.

Inode 0 is reserved and never allocated, so `ino 0` means "no inode" everywhere
and no caller needs a separate `-1`.

### Directory entry (16 bytes, 32 per block)

| Offset | Field | Type |
|---|---|---|
| 0 | inode | u16 |
| 2 | name length (1..12) | u8 |
| 3 | flags (reserved, 0) | u8 |
| 4 | name, not NUL-terminated | 12 bytes |

`ino == 0` marks a free slot, so removal is a zeroing and never a compaction.
Entries are scanned linearly: 32 per block × 5 blocks = 160 entries per
directory. That is the whole-directory limit, and it is stated.

Names: 1–12 bytes, no `/`, no NUL, no leading `.` unless the name is exactly
`.` or `..` (which are **not stored** — see §4).

## 2. Allocation

One bitmap block, one bit per block, bit set = allocated. The bitmap's own block
and the superblock are marked allocated at format time so a bug in the allocator
cannot hand out block 0.

Allocation is first-fit from the lowest free bit. Not best-fit, not free-list:
first-fit over 4096 bits is a scan of 64 bytes and has no state to get wrong
after a crash.

## 3. Writing a file

`fs_write` is deliberately small: it does not extend the file past its last
allocated block implicitly. Growing allocates one block at a time
(`fs_grow_ino`), zeroing the new block first, and updates `size` only after the
block pointer is durably in the inode. Order matters — a crash between the two
leaves a file that is shorter than its blocks, which fsck reports as a lost
block; the reverse order leaves a file claiming bytes in a block nobody will
ever read again, which fsck reports as a hole. Both are detectable; neither is
silent.

## 4. Paths, and why `.` and `..` are not stored

`services/fs/paths.goose` resolves a path component by component, starting at
the root, with a stack of at most 16 inodes for `..`. Storing `.` and `..` as
real entries is what most on-disk formats do and it makes every directory modify
two entries and keeps two link counts in sync; with fixed buffers and no journal
that is two more places to be inconsistent. The resolver treats them as path
syntax instead. The cost: `..` from a directory reached through a hard link
resolves to the path you walked, not the directory's "true" parent — there are
no hard links to directories here (`fs_link` refuses `mode == 2`), so they
cannot disagree.

Rules the resolver enforces, each with a hostile case in `t65_fs`:

- `//` collapses; a trailing `/` is allowed and ignored.
- `.` is skipped; `..` pops, and at the root it stays at the root (no escape).
- A component longer than 12 bytes is `E_NAME` (not truncated).
- More than 15 named components is `E_NOROOM` (not truncated). The resolver's
  16-slot chain includes the root, so 15 names is the real maximum.
- An empty path is `E_INVAL`. A path not starting with `/` is resolved relative
  to a caller-supplied directory, and `fs_resolve` takes that as an argument
  rather than assuming a current directory, because the process-wide cwd is
  exactly the global this layer avoids.

## 5. Directory growth

A directory grows like a file: entries fill block 0, then block 1, up to 5. There
is no directory block that holds `.`/`..`, so a directory with no entries has no
blocks at all — an empty directory is a free inode with mode 2, size 0, and five
zero block pointers. That is a legal state fsck must accept, and it does.

## 6. Failure and crash behaviour, stated honestly

There is no journal and no write-ahead log. Every multi-block update can be
interrupted between blocks, and the FS makes no claim to atomicity beyond a
single 512-byte block write.

What can be recovered:

- **A torn block write** is not modelled here; a real driver either writes the
  block or does not. If it can tear, this FS is not safe on it, and that is a
  property of the driver, not something this design papers over.
- **A crash mid-create** leaves an inode with `links = 1` and no directory entry
  pointing at it. `fsck` reports ORPHAN and `fsck_fix` frees it.
- **A crash mid-unlink** leaves a directory entry pointing at a freed inode,
  which `fsck` reports as BAD_ENTRY.
- **A crash between growing a file and updating its size** leaves a lost block,
  reported as LEAK.

`fsck` (B-L1-86) detects all four and can fix the three that are safely
fixable. The design's honest position: **this is a filesystem for a demo and a
shell, not for data you cannot lose.** The RAM backend under it is volatile
anyway, so the crash story is currently theoretical — and it will stop being
theoretical the day Layer 3 storage lands, which is why it is written now.

## 7. The backend, and what "persistent" means

`fs_format` / `fs_mount` run over `storage`'s RAM backend: real block I/O,
volatile storage. Write a file, unmount, mount again **within the same process**
and the file is there (the blocks are still in RAM); restart the process and it
is gone. `README.md` says this in one line, and `storage_volatile()` is the call
that answers it truthfully, so nothing above has to guess.

Binding to a real Layer 3 block driver is B-L1-74 and changes nothing in this
directory: the FS talks to `storage_read` / `storage_write`, and that is the
whole contract.

## 8. Sizes, and the numbers to argue about

| Thing | Value | Why |
|---|---|---|
| Block size | 512 | what a PC block driver reports; no re-blocking layer |
| Blocks on the RAM backend | 64 | 32 KiB total, set by `storage.RAM_BLOCKS` |
| Inodes | 128 | 8 blocks; enough for a shell's worth of files with headroom |
| Max file size | 2560 B | 5 direct blocks, no indirect |
| Max directory entries | 160 | 32 per block, 5 blocks |
| Max name | 12 B | 16-byte entries, name starts at byte 4 |
| Path depth | 15 names | resolver stack of 16 inodes includes the root |
| Block cache | 1 scratch block | single-threaded services, stated in `fs.goose` |

Every one of these is a refusal at the boundary rather than a truncation.
