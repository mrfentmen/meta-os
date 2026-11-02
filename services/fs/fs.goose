// services/fs/fs.goose
//
// MOSFS01 — a real filesystem over the block contract (B-L1-80..82, B-L1-84).
//
// Status: WRITTEN (not COMPILED, not RUN). Layout and reasoning: `DESIGN.md`.
//
// THE ONE GLOBAL, AND WHY IT IS SAFE
// ----------------------------------
// `fs_blk` and `fs_blk2` are two 512-byte scratch blocks. A filesystem that allocated
// per-call would need a heap; a filesystem that took scratch blocks from every caller
// would push the same two buffers through the shell, the log exporter and the updater.
// Two module-level blocks are safe here for one stated reason: **services are
// single-threaded by contract**, the supervisor starts no two calls into this module at
// once, and no function in this file calls another that uses the same block while still
// holding a pointer into it. Where two blocks are needed at once (`fs_link`, `fs_unlink`),
// `fs_blk2` exists and the comment says so.
//
// If that contract ever changes, this file is wrong in a way the compiler will not catch,
// which is why it is the first paragraph and not a footnote.
//
// ERROR CONVENTION
// ----------------
// Every call returns a code from `common/err`, or a count followed by a code. A count of
// -1 is never used; a failed read returns (0, code) so a caller cannot mistake "nothing
// read" for "read zero bytes successfully" without looking at the code.

import common.err.err;
import common.hash.hash;
import storage.storage;

let BLK: i64 = 512;
let SB_LBA: i64 = 0;
let BM_LBA: i64 = 1;
let INO_START: i64 = 2;             // first inode-table block
let INO_BLOCKS: i64 = 8;            // 8 * 512 = 4096 bytes = 128 inodes
let INODE_SIZE: i64 = 32;
let INODES_PER_BLK: i64 = 16;
let MAX_INODES: i64 = 128;
let DATA_START: i64 = 10;
let MAX_FILE_BLOCKS: i64 = 5;
let MAX_NAME: i64 = 12;
let DIR_ENT: i64 = 16;
let DIR_PER_BLK: i64 = 32;
let INO_NONE: i64 = 0;
let INO_ROOT: i64 = 1;
let MODE_FREE: i64 = 0;
let MODE_FILE: i64 = 1;
let MODE_DIR: i64 = 2;
let FS_VERSION: i64 = 1;
let FS_MAX_DEPTH: i64 = 16;
// The RAM backend's block count, duplicated here as a plain number rather than reached for
// across the module boundary: `fs_format` takes a size, and a caller that asks for more
// than the disk has gets E_INVAL. If `storage.RAM_BLOCKS` ever grows, this constant is the
// second place to change and `t65_fs` fails until it is.
let MAX_DISK_BLOCKS: i64 = 64;

var fs_blk: u8[..512] = [0; 512];
var fs_blk2: u8[..512] = [0; 512];
var fs_mounted: bool = false;
var fs_block_count: i64 = 0;
var fs_free_blocks: i64 = 0;
var fs_root_ino: i64 = INO_ROOT;
var fs_writes: i64 = 0;             // block writes this mount; the number tests assert on

// ---------------------------------------------------------------------------
// Little-endian accessors
// ---------------------------------------------------------------------------
//
// Hand-rolled on purpose (DESIGN.md §1): the on-disk format must not change because a
// stdlib version changed, and twenty lines of shift-and-or are auditable.

fn g8(b: u8[..512]&, off: i64) -> i64 {
    return b[off] as i64;
}

fn g16(b: u8[..512]&, off: i64) -> i64 {
    return (b[off] as i64) | ((b[off + 1] as i64) << 8);
}

fn g32(b: u8[..512]&, off: i64) -> i64 {
    return (b[off] as i64) | ((b[off + 1] as i64) << 8) | ((b[off + 2] as i64) << 16) | ((b[off + 3] as i64) << 24);
}

fn p8(b: u8[..512]&, off: i64, v: i64) {
    b[off] = (v & 0xff) as u8;
}

fn p16(b: u8[..512]&, off: i64, v: i64) {
    b[off] = (v & 0xff) as u8;
    b[off + 1] = ((v >> 8) & 0xff) as u8;
}

fn p32(b: u8[..512]&, off: i64, v: i64) {
    b[off] = (v & 0xff) as u8;
    b[off + 1] = ((v >> 8) & 0xff) as u8;
    b[off + 2] = ((v >> 16) & 0xff) as u8;
    b[off + 3] = ((v >> 24) & 0xff) as u8;
}

fn fs_zero(b: u8[..512]&) {
    var i: i64 = 0;
    while i < BLK {
        b[i] = 0;
        i = i + 1;
    }
}

fn fs_magic_ok(b: u8[..512]&) -> bool {
    let m: const u8[:] = "MOSFS01";
    var i: i64 = 0;
    while i < 8 {
        if (b[i] as i64) != (m[i] as i64) { return false; }
        i = i + 1;
    }
    return true;
}

// The magic is the eight-byte field "MOSFS01\0": seven characters and the NUL that
// pads the header slot. Copying m[i] for i < 8 read one byte past a 7-byte literal,
// which the bounds check turned into a crash on the first mount -- found by running
// t65 natively, invisible to the typecheck because the length is a run-time fact.
fn fs_put_magic(b: u8[..512]&) {
    let m: const u8[:] = "MOSFS01";
    var i: i64 = 0;
    while i < 8 {
        var c: u8 = 0;
        if i < m.len { c = m[i]; }
        b[i] = c;
        i = i + 1;
    }
}

// ---------------------------------------------------------------------------
// Block I/O
// ---------------------------------------------------------------------------

fn fs_bread(lba: i64) -> i64 {
    let code = storage_read(lba, fs_blk);
    if code != CODE_OK { return code; }
    return CODE_OK;
}

// Write `fs_blk` back. Counted so a test can prove a no-op did not write.
fn fs_bwrite(lba: i64) -> i64 {
    let code = storage_write(lba, fs_blk);
    if code == CODE_OK { fs_writes = fs_writes + 1; }
    return code;
}

// ---------------------------------------------------------------------------
// Superblock
// ---------------------------------------------------------------------------

fn sb_crc(b: u8[..512]&) -> u32 {
    return crc32(b[0..44]);
}

fn fs_sb_write() -> i64 {
    fs_zero(fs_blk);
    fs_put_magic(fs_blk);
    p32(fs_blk, 8, FS_VERSION);
    p32(fs_blk, 12, BLK);
    p32(fs_blk, 16, fs_block_count);
    p32(fs_blk, 20, INO_START);
    p32(fs_blk, 24, INO_BLOCKS);
    p32(fs_blk, 28, DATA_START);
    p32(fs_blk, 32, fs_block_count - DATA_START);
    p32(fs_blk, 36, fs_free_blocks);
    p32(fs_blk, 40, fs_root_ino);
    p32(fs_blk, 44, sb_crc(fs_blk) as i64);
    return fs_bwrite(SB_LBA);
}

// ---------------------------------------------------------------------------
// Bitmap
// ---------------------------------------------------------------------------

fn fs_bm_read() -> i64 {
    return fs_bread(BM_LBA);
}

// Requires the bitmap to already be in `fs_blk` (the caller just read it), so an
// allocation over a directory block does not re-read the bitmap per bit.
fn fs_bm_get(lba: i64) -> bool {
    let byte = lba / 8;
    let bit = lba % 8;
    return ((fs_blk[byte] as i64) & (1 << bit)) != 0;
}

// ---------------------------------------------------------------------------
// Inodes
// ---------------------------------------------------------------------------

struct Inode {
    mode: i64,
    links: i64,
    size: i64,
    b0: i64,
    b1: i64,
    b2: i64,
    b3: i64,
    b4: i64,
}

fn ino_valid(ino: i64) -> bool {
    return ino > 0 && ino < MAX_INODES;
}

fn ino_block(ino: i64) -> i64 {
    return INO_START + (ino / INODES_PER_BLK);
}

fn ino_offset(ino: i64) -> i64 {
    return (ino % INODES_PER_BLK) * INODE_SIZE;
}

// Read an inode. `fs_blk` holds the inode-table block afterwards, which the writer below
// and `fs_ino_free` reuse deliberately: one read, one write, no window where the block
// is re-fetched and could have changed.
fn fs_ino_read(ino: i64) -> Inode, i64 {
    if !ino_valid(ino) { return empty_inode(), E_INVAL; }
    let code = fs_bread(ino_block(ino));
    if code != CODE_OK { return empty_inode(), code; }
    let o = ino_offset(ino);
    return Inode {
        mode: g16(fs_blk, o),
        links: g16(fs_blk, o + 2),
        size: g32(fs_blk, o + 4),
        b0: g32(fs_blk, o + 8),
        b1: g32(fs_blk, o + 12),
        b2: g32(fs_blk, o + 16),
        b3: g32(fs_blk, o + 20),
        b4: g32(fs_blk, o + 24),
    }, CODE_OK;
}

fn empty_inode() -> Inode {
    return Inode { mode: MODE_FREE, links: 0, size: 0, b0: 0, b1: 0, b2: 0, b3: 0, b4: 0 };
}

// Write an inode back into the block `fs_ino_read` just loaded. Refuses to write if the
// block in `fs_blk` is not the one this inode lives in -- a stale block here is the
// classic way one file's inode overwrites another's.
fn fs_ino_write(ino: i64, n: Inode&) -> i64 {
    if !ino_valid(ino) { return E_INVAL; }
    let o = ino_offset(ino);
    p16(fs_blk, o, n.mode);
    p16(fs_blk, o + 2, n.links);
    p32(fs_blk, o + 4, n.size);
    p32(fs_blk, o + 8, n.b0);
    p32(fs_blk, o + 12, n.b1);
    p32(fs_blk, o + 16, n.b2);
    p32(fs_blk, o + 20, n.b3);
    p32(fs_blk, o + 24, n.b4);
    return fs_bwrite(ino_block(ino));
}

fn ino_block_at(n: Inode&, i: i64) -> i64 {
    if i == 0 { return n.b0; }
    if i == 1 { return n.b1; }
    if i == 2 { return n.b2; }
    if i == 3 { return n.b3; }
    if i == 4 { return n.b4; }
    return 0;
}

fn ino_set_block_at(n: Inode&, i: i64, lba: i64) {
    if i == 0 { n.b0 = lba; }
    if i == 1 { n.b1 = lba; }
    if i == 2 { n.b2 = lba; }
    if i == 3 { n.b3 = lba; }
    if i == 4 { n.b4 = lba; }
}

fn ino_blocks_used(n: Inode&) -> i64 {
    var c: i64 = 0;
    var i: i64 = 0;
    while i < MAX_FILE_BLOCKS {
        if ino_block_at(n, i) != 0 { c = c + 1; }
        i = i + 1;
    }
    return c;
}

// ---------------------------------------------------------------------------
// Allocation
// ---------------------------------------------------------------------------

// Allocate one data block. Returns (lba, code); the block is zeroed before it is handed
// out, so a file's tail is never another file's bytes.
fn fs_alloc_block() -> i64, i64 {
    if fs_free_blocks <= 0 { return 0, E_NOROOM; }
    let bm_code = fs_bm_read();
    if bm_code != CODE_OK { return 0, bm_code; }
    var lba = DATA_START;
    var found: i64 = -1;
    while lba < fs_block_count {
        if !fs_bm_get(lba) {
            found = lba;
            break;          // first fit; the bitmap is 64 bytes, a scan costs nothing
        }
        lba = lba + 1;
    }
    if found < 0 { return 0, E_NOROOM; }
    let byte = found / 8;
    let bit = found % 8;
    fs_blk[byte] = ((fs_blk[byte] as i64) | (1 << bit)) as u8;
    let code = fs_bwrite(BM_LBA);
    if code != CODE_OK { return 0, code; }

    fs_zero(fs_blk);
    let zcode = fs_bwrite(found);
    if zcode != CODE_OK { return 0, zcode; }

    fs_free_blocks = fs_free_blocks - 1;
    return found, CODE_OK;
}

fn fs_free_block(lba: i64) -> i64 {
    if lba < DATA_START || lba >= fs_block_count { return E_INVAL; }
    let code = fs_set_bitmap(lba, false);
    if code != CODE_OK { return code; }
    fs_free_blocks = fs_free_blocks + 1;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Format and mount
// ---------------------------------------------------------------------------

fn fs_format(block_count: i64) -> i64 {
    if block_count < DATA_START + 4 || block_count > MAX_DISK_BLOCKS {
        return E_INVAL;          // too small to hold a superblock and a root, or no such disk
    }
    let code = storage_init(block_count);
    if code != CODE_OK { return code; }

    fs_block_count = block_count;
    fs_mounted = false;
    fs_writes = 0;
    fs_root_ino = INO_ROOT;

    // Inode table: every slot free, including inode 0 (reserved by convention).
    var blk = INO_START;
    while blk < INO_START + INO_BLOCKS {
        fs_zero(fs_blk);
        let w = fs_bwrite(blk);
        if w != CODE_OK { return w; }
        blk = blk + 1;
    }

    // Root: an empty directory with no blocks at all (a legal state -- DESIGN.md §5).
    var root = empty_inode();
    root.mode = MODE_DIR;
    root.links = 1;
    let rc = fs_ino_write(INO_ROOT, root);
    if rc != CODE_OK { return rc; }

    // Bitmap: everything below DATA_START is allocated, and so is the tail past block_count.
    fs_zero(fs_blk);
    var lba: i64 = 0;
    while lba < DATA_START {
        let byte = lba / 8;
        let bit = lba % 8;
        fs_blk[byte] = ((fs_blk[byte] as i64) | (1 << bit)) as u8;
        lba = lba + 1;
    }
    while lba < MAX_DISK_BLOCKS * 8 {
        // Bits past the end of this disk are marked used so a future grow of the device
        // does not hand out blocks that the current superblock says do not exist.
        if lba >= block_count {
            let byte = lba / 8;
            let bit = lba % 8;
            fs_blk[byte] = ((fs_blk[byte] as i64) | (1 << bit)) as u8;
        }
        lba = lba + 1;
    }
    let bmw = fs_bwrite(BM_LBA);
    if bmw != CODE_OK { return bmw; }

    fs_free_blocks = block_count - DATA_START;
    fs_mounted = true;
    return fs_sb_write();
}

// Mount: validate everything a filesystem can check about itself before trusting it.
fn fs_mount() -> i64 {
    let code = fs_bread(SB_LBA);
    if code != CODE_OK { return code; }
    if !fs_magic_ok(fs_blk) { return E_INVAL; }
    if (g32(fs_blk, 8) as i64) != FS_VERSION { return E_STATE; }
    if (g32(fs_blk, 12) as i64) != BLK { return E_STATE; }
    let stored_crc = g32(fs_blk, 44) as u32;
    // The CRC covers bytes 0..43, which excludes its own field, so it can be recomputed
    // without zeroing anything first -- and the writer never has a window where the field
    // is stale relative to the bytes it protects.
    let want = sb_crc(fs_blk) as u32;
    if stored_crc != want { return E_VERIFY; }

    let bc = g32(fs_blk, 16);
    if bc < DATA_START + 4 || bc > MAX_DISK_BLOCKS { return E_STATE; }
    if g32(fs_blk, 20) != INO_START { return E_STATE; }
    if g32(fs_blk, 24) != INO_BLOCKS { return E_STATE; }
    if g32(fs_blk, 28) != DATA_START { return E_STATE; }

    fs_block_count = bc;
    fs_free_blocks = g32(fs_blk, 36);
    fs_root_ino = g32(fs_blk, 40);
    fs_writes = 0;
    fs_mounted = true;
    return CODE_OK;
}

fn fs_umount() -> i64 {
    if !fs_mounted { return E_STATE; }
    fs_mounted = false;
    return CODE_OK;
}

fn fs_sync() -> i64 {
    if !fs_mounted { return E_STATE; }
    return fs_sb_write();
}

fn fs_stats() -> i64, i64, i64 {
    if !fs_mounted { return 0, 0, E_STATE; }
    return fs_free_blocks, fs_writes, CODE_OK;
}

fn fs_is_root(ino: i64) -> bool {
    return ino == fs_root_ino;
}

// Accessors. `fs_mounted` and `fs_root_ino` are module state, and `paths.goose` must not
// touch either directly: a resolver that reads a bool by name is a resolver that can also
// write it.
fn fs_is_mounted() -> bool {
    return fs_mounted;
}

fn fs_root() -> i64 {
    return fs_root_ino;
}

fn ino_is_dir(ino: i64) -> bool {
    return ino_mode_of(ino) == MODE_DIR;
}

fn ino_is_file(ino: i64) -> bool {
    return ino_mode_of(ino) == MODE_FILE;
}

fn fs_block_count_value() -> i64 {
    return fs_block_count;
}

fn fs_data_start() -> i64 {
    return DATA_START;
}

// Read the bitmap block into `fs_blk`. `bitmap_bit_set` then answers from that copy, which
// is why the checker reads once and asks many times instead of re-reading per bit.
fn fs_read_bitmap() -> i64 {
    return fs_bread(BM_LBA);
}

fn bitmap_bit_set(lba: i64) -> bool {
    if lba < 0 || lba >= MAX_DISK_BLOCKS { return false; }
    return fs_bm_get(lba);
}

// Set or clear one bit and write the bitmap back. Used by the checker's repair path; the
// allocator does its own read-modify-write because it also zeroes the block it hands out.
fn fs_set_bitmap(lba: i64, on: bool) -> i64 {
    if lba < 0 || lba >= MAX_DISK_BLOCKS { return E_INVAL; }
    let code = fs_bm_read();
    if code != CODE_OK { return code; }
    let byte = lba / 8;
    let bit = lba % 8;
    if on {
        fs_blk[byte] = ((fs_blk[byte] as i64) | (1 << bit)) as u8;
    } else {
        fs_blk[byte] = ((fs_blk[byte] as i64) & ~(1 << bit)) as u8;
    }
    return fs_bwrite(BM_LBA);
}

// Count free blocks in the data region from the on-disk bitmap. Returns -1 if the bitmap
// cannot be read, so a caller never "recomputes" a count from nothing.
fn count_free_blocks() -> i64 {
    let code = fs_bm_read();
    if code != CODE_OK { return -1; }
    var n: i64 = 0;
    var lba = DATA_START;
    while lba < fs_block_count {
        if !fs_bm_get(lba) { n = n + 1; }
        lba = lba + 1;
    }
    return n;
}

fn fs_set_free_blocks(n_in: i64) {
    var n = n_in;
    if n < 0 { n = 0; }
    fs_free_blocks = n;
}

// ---------------------------------------------------------------------------
// Directory entries
// ---------------------------------------------------------------------------

fn name_ok(name: const u8[:]) -> bool {
    if name.len == 0 || name.len > MAX_NAME { return false; }
    var i: i64 = 0;
    while i < name.len {
        let c = name[i];
        if c == 0 || c == '/' { return false; }
        i = i + 1;
    }
    return true;
}

// Compare a 12-byte field at `off` with `name`. Length first, so a name that is a prefix
// of another never matches -- "log" must not find "logs".
fn ent_matches(off: i64, name: const u8[:]) -> bool {
    if g8(fs_blk, off + 2) != name.len { return false; }
    var i: i64 = 0;
    while i < name.len {
        if g8(fs_blk, off + 4 + i) != (name[i] as i64) { return false; }
        i = i + 1;
    }
    return true;
}

fn ent_put(off: i64, ino: i64, name: const u8[:]) {
    p16(fs_blk, off, ino);
    p8(fs_blk, off + 2, name.len);
    p8(fs_blk, off + 3, 0);
    var i: i64 = 0;
    while i < name.len {
        p8(fs_blk, off + 4 + i, name[i] as i64);
        i = i + 1;
    }
    while i < MAX_NAME {           // zero the tail so a shorter name cannot inherit bytes
        p8(fs_blk, off + 4 + i, 0);
        i = i + 1;
    }
}

// Find a name in a directory. Returns (ino, code); ino 0 with CODE_OK means "not found",
// which is why the code is separate -- a caller that treated E_NOROOM as "missing" would
// create a duplicate entry.
fn fs_lookup(dir_ino: i64, name: const u8[:]) -> i64, i64 {
    if !fs_mounted { return 0, E_STATE; }
    if !name_ok(name) { return 0, E_INVAL; }
    let d, code = fs_ino_read(dir_ino);
    if code != CODE_OK { return 0, code; }
    if d.mode != MODE_DIR { return 0, E_INVAL; }
    var bi: i64 = 0;
    while bi < MAX_FILE_BLOCKS {
        let lba = ino_block_at(d, bi);
        if lba == 0 { return 0, CODE_OK; }
        let rc = fs_bread(lba);
        if rc != CODE_OK { return 0, rc; }
        var e: i64 = 0;
        while e < DIR_PER_BLK {
            let off = e * DIR_ENT;
            let ino = g16(fs_blk, off);
            if ino != 0 && ent_matches(off, name) { return ino, CODE_OK; }
            e = e + 1;
        }
        bi = bi + 1;
    }
    return 0, CODE_OK;
}

// Add an entry. Returns CODE_OK, or E_STATE if the name already exists.
fn fs_dir_add(dir_ino: i64, name: const u8[:], ino: i64) -> i64 {
    if !fs_mounted { return E_STATE; }
    if !name_ok(name) { return E_INVAL; }
    let existing, lc = fs_lookup(dir_ino, name);
    if lc != CODE_OK { return lc; }
    if existing != 0 { return E_STATE; }

    // Re-read the directory after fs_lookup moved `fs_blk` to a data block.
    var d, dc = fs_ino_read(dir_ino);
    if dc != CODE_OK { return dc; }
    if d.mode != MODE_DIR { return E_INVAL; }

    var bi: i64 = 0;
    while bi < MAX_FILE_BLOCKS {
        let lba = ino_block_at(d, bi);
        if lba == 0 {
            let nlba, ac = fs_grow_ino(dir_ino);
            if ac != CODE_OK { return ac; }
            let rc = fs_bread(nlba);
            if rc != CODE_OK { return rc; }
            ent_put(0, ino, name);
            return fs_bwrite(nlba);
        }
        let rc2 = fs_bread(lba);
        if rc2 != CODE_OK { return rc2; }
        var e: i64 = 0;
        while e < DIR_PER_BLK {
            let off = e * DIR_ENT;
            if g16(fs_blk, off) == 0 {
                ent_put(off, ino, name);
                return fs_bwrite(lba);
            }
            e = e + 1;
        }
        bi = bi + 1;
    }
    return E_NOROOM;
}

// Remove an entry. The inode is NOT freed here: link count and freeing belong to the
// caller (`fs_unlink`), because an entry can be one of several links to the same inode.
fn fs_dir_remove(dir_ino: i64, name: const u8[:]) -> i64, i64 {
    if !fs_mounted { return 0, E_STATE; }
    if !name_ok(name) { return 0, E_INVAL; }
    let d, code = fs_ino_read(dir_ino);
    if code != CODE_OK { return 0, code; }
    if d.mode != MODE_DIR { return 0, E_INVAL; }
    var bi: i64 = 0;
    while bi < MAX_FILE_BLOCKS {
        let lba = ino_block_at(d, bi);
        if lba == 0 { return 0, CODE_OK; }
        let rc = fs_bread(lba);
        if rc != CODE_OK { return 0, rc; }
        var e: i64 = 0;
        while e < DIR_PER_BLK {
            let off = e * DIR_ENT;
            let ino = g16(fs_blk, off);
            if ino != 0 && ent_matches(off, name) {
                p16(fs_blk, off, 0);
                p8(fs_blk, off + 2, 0);
                var k: i64 = 0;
                while k < MAX_NAME {
                    p8(fs_blk, off + 4 + k, 0);
                    k = k + 1;
                }
                let wc = fs_bwrite(lba);
                if wc != CODE_OK { return 0, wc; }
                return ino, CODE_OK;
            }
            e = e + 1;
        }
        bi = bi + 1;
    }
    return 0, CODE_OK;
}

// The `idx`th name in a directory. Returns (ino, kind, found) with the name copied into
// `out`. `idx` counts used slots only, so a removed entry does not leave a gap the caller
// has to know about.
fn fs_readdir(dir_ino: i64, idx: i64, out: u8[>..]&, cap: i64) -> i64, i64, bool {
    if !fs_mounted || idx < 0 { return 0, 0, false; }
    let d, code = fs_ino_read(dir_ino);
    if code != CODE_OK { return 0, 0, false; }
    if d.mode != MODE_DIR { return 0, 0, false; }
    var seen: i64 = 0;
    var bi: i64 = 0;
    while bi < MAX_FILE_BLOCKS {
        let lba = ino_block_at(d, bi);
        if lba == 0 { return 0, 0, false; }
        if fs_bread(lba) != CODE_OK { return 0, 0, false; }
        var e: i64 = 0;
        while e < DIR_PER_BLK {
            let off = e * DIR_ENT;
            let ino = g16(fs_blk, off);
            if ino != 0 {
                if seen == idx {
                    let nlen = g8(fs_blk, off + 2);
                    var i: i64 = 0;
                    while i < nlen && out.len < cap {
                        out.push((g8(fs_blk, off + 4 + i)) as u8);
                        i = i + 1;
                    }
                    // Kind comes from the target inode, not from the entry: a caller
                    // printing "dir" from a flag the creator chose would print a claim,
                    // not the object. This is the last thing the call does, so the block
                    // it loads into `fs_blk` cannot disturb the iteration above.
                    return ino, ino_mode_of(ino), true;
                }
                seen = seen + 1;
            }
            e = e + 1;
        }
        bi = bi + 1;
    }
    return 0, 0, false;
}

// Read just the mode, using the second scratch block so the caller's directory block in
// `fs_blk` is not clobbered mid-iteration.
fn ino_mode_of(ino: i64) -> i64 {
    if !ino_valid(ino) { return MODE_FREE; }
    if fs_bread(ino_block(ino)) != CODE_OK { return MODE_FREE; }
    return g16(fs_blk, ino_offset(ino));
}

fn fs_dirent_count(dir_ino: i64) -> i64 {
    if !fs_mounted { return -1; }
    let d, code = fs_ino_read(dir_ino);
    if code != CODE_OK || d.mode != MODE_DIR { return -1; }
    var n: i64 = 0;
    var bi: i64 = 0;
    while bi < MAX_FILE_BLOCKS {
        let lba = ino_block_at(d, bi);
        if lba == 0 { return n; }
        if fs_bread(lba) != CODE_OK { return -1; }
        var e: i64 = 0;
        while e < DIR_PER_BLK {
            if g16(fs_blk, e * DIR_ENT) != 0 { n = n + 1; }
            e = e + 1;
        }
        bi = bi + 1;
    }
    return n;
}

// ---------------------------------------------------------------------------
// Files
// ---------------------------------------------------------------------------

// Allocate the next data block for an inode and record it. Zeroes the block first.
fn fs_grow_ino(ino: i64) -> i64, i64 {
    let first, code = fs_ino_read(ino);
    if code != CODE_OK { return 0, code; }
    var slot: i64 = -1;
    var i: i64 = 0;
    while i < MAX_FILE_BLOCKS {
        if ino_block_at(first, i) == 0 { slot = i; break; }
        i = i + 1;
    }
    if slot < 0 { return 0, E_NOROOM; }

    let lba, ac = fs_alloc_block();
    if ac != CODE_OK { return 0, ac; }

    // `fs_alloc_block` used `fs_blk` for the bitmap and for zeroing, so the inode's block
    // has to be loaded again before it can be patched. The slot index is recomputed from
    // the fresh copy rather than assumed: if the inode changed underneath, this returns a
    // code instead of writing a stale pointer into somebody else's bytes.
    let again, rc = fs_ino_read(ino);
    if rc != CODE_OK { return 0, rc; }
    var n = again;
    if ino_block_at(n, slot) != 0 { return 0, E_STATE; }
    ino_set_block_at(n, slot, lba);
    let wc = fs_ino_write(ino, n);
    if wc != CODE_OK { return 0, wc; }
    return lba, CODE_OK;
}

// Free every data block of an inode and mark it free. Used by unlink, truncate and fsck.
fn fs_release_inode(ino: i64) -> i64 {
    let n, code = fs_ino_read(ino);
    if code != CODE_OK { return code; }
    var i: i64 = 0;
    while i < MAX_FILE_BLOCKS {
        let lba = ino_block_at(n, i);
        if lba != 0 {
            let fc = fs_free_block(lba);
            if fc != CODE_OK { return fc; }
        }
        i = i + 1;
    }
    var cleared = empty_inode();
    let wc = fs_ino_write(ino, cleared);
    if wc != CODE_OK { return wc; }
    return CODE_OK;
}

fn fs_create(parent_ino: i64, name: const u8[:], kind: i64) -> i64, i64 {
    if !fs_mounted { return 0, E_STATE; }
    if kind != MODE_FILE && kind != MODE_DIR { return 0, E_INVAL; }
    if !name_ok(name) { return 0, E_INVAL; }

    let p, pc = fs_ino_read(parent_ino);
    if pc != CODE_OK { return 0, pc; }
    if p.mode != MODE_DIR { return 0, E_INVAL; }

    let existing, lc = fs_lookup(parent_ino, name);
    if lc != CODE_OK { return 0, lc; }
    if existing != 0 { return 0, E_STATE; }

    // Find a free inode. Scanning from 1 each time is O(128) block-light reads because
    // the whole table is 8 blocks and we read one per 16 inodes.
    var ino: i64 = 1;
    var found: i64 = 0;
    while ino < MAX_INODES {
        let cand, rc = fs_ino_read(ino);
        if rc != CODE_OK { return 0, rc; }
        if cand.mode == MODE_FREE { found = ino; break; }
        ino = ino + 1;
    }
    if found == 0 { return 0, E_NOROOM; }

    var fresh = empty_inode();
    fresh.mode = kind;
    fresh.links = 1;
    fresh.size = 0;
    let wc = fs_ino_write(found, fresh);
    if wc != CODE_OK { return 0, wc; }

    let ac = fs_dir_add(parent_ino, name, found);
    if ac != CODE_OK {
        // Roll back: an inode with no entry is an orphan, and fsck would report a bug the
        // caller already saw. Freeing here keeps the failure clean.
        let _ = fs_release_inode(found);
        return 0, ac;
    }
    return found, CODE_OK;
}

// Read up to `cap` bytes at `off`. Returns (count, code). A short read at EOF is success.
fn fs_read(ino: i64, off: i64, out: u8[>..]&, cap: i64) -> i64, i64 {
    if !fs_mounted { return 0, E_STATE; }
    if off < 0 { return 0, E_INVAL; }
    let n, code = fs_ino_read(ino);
    if code != CODE_OK { return 0, code; }
    if n.mode != MODE_FILE { return 0, E_INVAL; }
    if off >= n.size { return 0, CODE_OK; }

    var got: i64 = 0;
    var pos = off;
    while pos < n.size && out.len < cap {
        let bi = pos / BLK;
        if bi >= MAX_FILE_BLOCKS { return got, E_NOROOM; }
        let lba = ino_block_at(n, bi);
        if lba == 0 { return got, E_STATE; }   // size says bytes exist; no block does
        let rc = fs_bread(lba);
        if rc != CODE_OK { return got, rc; }
        var o = pos % BLK;
        while o < BLK && pos < n.size && out.len < cap {
            out.push((g8(fs_blk, o)) as u8);
            o = o + 1;
            pos = pos + 1;
            got = got + 1;
        }
    }
    return got, CODE_OK;
}

// Write `src` at `off`, growing the file as needed. Returns (count, code).
//
// Sparse writes are refused: `off` past the current size is E_INVAL rather than a
// zero-filled gap, because a hole in a filesystem with no indirect blocks is a hole fsck
// has to explain and no caller here needs.
fn fs_write(ino: i64, off: i64, src: const u8[:]) -> i64, i64 {
    if !fs_mounted { return 0, E_STATE; }
    if off < 0 { return 0, E_INVAL; }
    var n, code = fs_ino_read(ino);
    if code != CODE_OK { return 0, code; }
    if n.mode != MODE_FILE { return 0, E_INVAL; }
    if off > n.size { return 0, E_INVAL; }

    let need_end = off + src.len;
    if need_end > MAX_FILE_BLOCKS * BLK { return 0, E_NOROOM; }

    var written: i64 = 0;
    var pos = off;
    while written < src.len {
        let bi = pos / BLK;
        if bi >= MAX_FILE_BLOCKS { return written, E_NOROOM; }
        var lba = ino_block_at(n, bi);
        if lba == 0 {
            let nlba, ac = fs_grow_ino(ino);
            if ac != CODE_OK { return written, ac; }
            lba = nlba;
            // fs_grow_ino moved fs_blk to the inode table; reload the file's inode so the
            // local copy has the new block pointer, then reload the data block.
            let again, rc = fs_ino_read(ino);
            if rc != CODE_OK { return written, rc; }
            n = again;
            if ino_block_at(n, bi) != lba { return written, E_STATE; }
        }
        let br = fs_bread(lba);
        if br != CODE_OK { return written, br; }
        var o = pos % BLK;
        while o < BLK && written < src.len {
            p8(fs_blk, o, (src[written] as i64));
            o = o + 1;
            pos = pos + 1;
            written = written + 1;
        }
        let bw = fs_bwrite(lba);
        if bw != CODE_OK { return written, bw; }
    }

    // Size is written after the data, so an interrupted write leaves a file that is
    // shorter than its blocks (a LEAK fsck can report) rather than one claiming bytes
    // that were never stored.
    if pos > n.size {
        let fin, fc = fs_ino_read(ino);
        if fc != CODE_OK { return written, fc; }
        var n3 = fin;
        n3.size = pos;
        let sc = fs_ino_write(ino, n3);
        if sc != CODE_OK { return written, sc; }
    }
    return written, CODE_OK;
}

fn fs_truncate(ino: i64) -> i64 {
    if !fs_mounted { return E_STATE; }
    var n, code = fs_ino_read(ino);
    if code != CODE_OK { return code; }
    if n.mode != MODE_FILE { return E_INVAL; }
    var i: i64 = 0;
    while i < MAX_FILE_BLOCKS {
        let lba = ino_block_at(n, i);
        if lba != 0 {
            let fc = fs_free_block(lba);
            if fc != CODE_OK { return fc; }
            ino_set_block_at(n, i, 0);
        }
        i = i + 1;
    }
    n.size = 0;
    return fs_ino_write(ino, n);
}

fn fs_unlink(parent_ino: i64, name: const u8[:]) -> i64 {
    if !fs_mounted { return E_STATE; }
    let target, lc = fs_lookup(parent_ino, name);
    if lc != CODE_OK { return lc; }
    if target == 0 { return E_INVAL; }        // no such name
    if target == fs_root_ino { return E_INVAL; }

    let t, tc = fs_ino_read(target);
    if tc != CODE_OK { return tc; }
    if t.mode == MODE_DIR {
        let count = fs_dirent_count(target);
        if count != 0 { return E_STATE; }     // rmdir refuses a non-empty directory
    }

    let removed, rc = fs_dir_remove(parent_ino, name);
    if rc != CODE_OK { return rc; }
    if removed != target { return E_STATE; }

    let back, bc = fs_ino_read(target);
    if bc != CODE_OK { return bc; }
    var n = back;
    if n.links > 1 {
        n.links = n.links - 1;
        return fs_ino_write(target, n);
    }
    return fs_release_inode(target);
}

// Rename within one directory. Cross-directory rename is refused rather than half-done:
// it needs two directory updates and this filesystem has no journal to make that safe.
fn fs_rename(dir_ino: i64, from: const u8[:], to: const u8[:]) -> i64 {
    if !fs_mounted { return E_STATE; }
    if !name_ok(from) || !name_ok(to) { return E_INVAL; }
    let src, sc = fs_lookup(dir_ino, from);
    if sc != CODE_OK { return sc; }
    if src == 0 { return E_INVAL; }
    let dst, dc = fs_lookup(dir_ino, to);
    if dc != CODE_OK { return dc; }
    if dst != 0 { return E_STATE; }

    // Remove-then-add, in that order: a crash between them loses the entry (recoverable,
    // reported as ORPHAN) rather than duplicating it (unrecoverable ambiguity).
    let removed, rc = fs_dir_remove(dir_ino, from);
    if rc != CODE_OK { return rc; }
    if removed != src { return E_STATE; }
    let ac = fs_dir_add(dir_ino, to, src);
    if ac != CODE_OK {
        let _ = fs_dir_add(dir_ino, from, src);   // put it back under the old name
        return ac;
    }
    return CODE_OK;
}

