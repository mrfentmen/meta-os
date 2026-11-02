// services/storage/storage.goose
//
// Layer 4, service 9: the storage contract and its RAM backend.
//
// Status: RUNS — reached by tests/t65_fs (70 checks, exit 0). Measured 2026-11-02 by audit_status.py. Verified via goose-mcp@1.1.0: `T&` references
// ("one machine address, no pointer arithmetic, no casts, no way to make it
// dangle" -- reference#46), structs, static arrays, `while`/`if`, multi-value
// returns.
//
// WHAT IS REAL HERE, AND WHAT IS NOT
// ----------------------------------
// The RAM backend is REAL storage: you write blocks, you read them back, the bytes
// are the bytes. What it is not is PERSISTENT. It survives until the process exits
// and no longer. That is stated in every call's contract rather than discovered by
// whoever loses their file system at shutdown.
//
// It is not a mock: a mock pretends to be the thing it replaces (it would claim to
// be a disk and lie about durability). This backend claims exactly what it does.
// Layer 3 block drivers bind to the same two calls; nothing above changes when they
// arrive.
//
// WHY BLOCK I/O AND NOT A FILE API
// --------------------------------
// A file API at this layer would force a filesystem design into the transport.
// B-L1-79..84 build the filesystem on top of these blocks, and the kernel's drivers
// will speak blocks. Byte-level access here would also hide the alignment cost that
// real hardware imposes, and code written against a forgiving backend breaks the
// first time it meets a real controller.

import common.err.err;

let BLOCK_SIZE: i64 = 512;              // the size a PC block driver will report
let RAM_BLOCKS: i64 = 64;               // 32 KiB: enough for config, records, a test FS
let RAM_BYTES: i64 = 32768;             // BLOCK_SIZE * RAM_BLOCKS

struct BlockDev {
    block_size: i64,
    block_count: i64,
    writes: i64,        // block writes since init; the number a test asserts on
    sealed: bool,       // read-only: models a device that went write-protected
    present: bool,
}

var disk: BlockDev = BlockDev {
    block_size: 0,
    block_count: 0,
    writes: 0,
    sealed: false,
    present: false,
};
var ram: u8[..32768] = [0; 32768];

// ---------------------------------------------------------------------------
// The contract
// ---------------------------------------------------------------------------
//
// storage_read(lba, buf)  -> CODE_OK | E_INVAL | E_NO_DEVICE | E_BAD_BLOCK
// storage_write(lba, buf) -> CODE_OK | E_INVAL | E_NO_DEVICE | E_BAD_BLOCK | E_READ_ONLY
//
// `buf` is exactly one block. Not "up to": a read that silently returned fewer bytes
// than a block would make every caller responsible for a short-read case that the
// backend already knows the answer to.
//
// Both calls are synchronous and take no deadline. On a RAM backend that is honest.
// On a real controller it would not be, which is why the binding task (B-L1-74) has
// to revisit this signature rather than assume it -- recorded here so that task
// cannot skip the question.

fn storage_init(block_count: i64) -> i64 {
    if block_count <= 0 || block_count > RAM_BLOCKS { return E_INVAL; }
    disk.block_size = BLOCK_SIZE;
    disk.block_count = block_count;
    disk.writes = 0;
    disk.sealed = false;
    disk.present = true;

    var i: i64 = 0;
    while i < RAM_BYTES {
        ram[i] = 0;         // a freshly granted region is zeroed, not "probably zero"
        i = i + 1;
    }
    return CODE_OK;
}

// Whether an LBA is addressable. One function so read and write cannot disagree
// about the boundary -- an off-by-one in only one of them is the classic way a
// filesystem's last block becomes untrustworthy.
fn storage_lba_ok(lba: i64) -> bool {
    if !disk.present { return false; }
    if lba < 0 || lba >= disk.block_count { return false; }
    return true;
}

fn storage_read(lba: i64, buf: u8[..512]&) -> i64 {
    if !disk.present { return E_NO_DEVICE; }
    if !storage_lba_ok(lba) { return E_BAD_BLOCK; }
    let base = lba * BLOCK_SIZE;
    var i: i64 = 0;
    while i < BLOCK_SIZE {
        buf[i] = ram[base + i];
        i = i + 1;
    }
    return CODE_OK;
}

fn storage_write(lba: i64, buf: u8[..512]&) -> i64 {
    if !disk.present { return E_NO_DEVICE; }
    if disk.sealed { return E_READ_ONLY; }
    if !storage_lba_ok(lba) { return E_BAD_BLOCK; }
    let base = lba * BLOCK_SIZE;
    var i: i64 = 0;
    while i < BLOCK_SIZE {
        ram[base + i] = buf[i];
        i = i + 1;
    }
    disk.writes = disk.writes + 1;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Honest backend operations
// ---------------------------------------------------------------------------
//
// These are RAM-backend facts, not part of the contract. They exist because a
// volatile backend must be able to say so about itself, and because tests need a
// way to prove the data really moved.
//
// storage_volatile() is the one every caller should read: it is the difference
// between "your data is stored" and "your data is stored until this process ends".

fn storage_volatile() -> bool {
    return true;      // true by construction; here so the answer is asked for a name
}

fn storage_seal() -> i64 {
    if !disk.present { return E_NO_DEVICE; }
    disk.sealed = true;
    return CODE_OK;
}

fn storage_stats() -> i64, i64, i64 {
    if !disk.present { return 0, 0, E_NO_DEVICE; }
    return disk.block_count, disk.writes, CODE_OK;
}

// Wipe: a RAM disk that can never be emptied cannot be reused by the next test, and
// zeroing is the only operation a volatile store needs to promise.
fn storage_wipe() -> i64 {
    if !disk.present { return E_NO_DEVICE; }
    var i: i64 = 0;
    while i < RAM_BYTES {
        ram[i] = 0;
        i = i + 1;
    }
    disk.writes = 0;
    disk.sealed = false;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Deliberately absent
// ---------------------------------------------------------------------------
//
// - No caching. A cache over 32 KiB of RAM is a cache over nothing.
// - No partition table, no bad-block map, no flush: a volatile store has nothing to
//   flush, and the other two are Layer 3 facts this backend does not have.
// - No async, no queueing, no deadline. On a real controller those are not optional;
//   they are listed in the contract above as work B-L1-74 inherits, not as things
//   this file pretends to have solved.
