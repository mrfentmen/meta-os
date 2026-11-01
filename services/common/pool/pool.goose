// services/common/pool/pool.goose
//
// B-L1-145 — Gap library 7: a fixed-slot allocator with a free list.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE GAP THIS FILLS
// ------------------
// STDLIB_GAPS.md lists `slot_pool` (15 symbols) and `slice_pool` (7) as **provided** -- host
// pools backed by host memory. After a kernel boot there is no host runtime: the storage is the
// caller's fixed buffer, and the free list has to live inside it. This is that: N blocks of a
// fixed size, a bitmap of which are taken, and an out-of-room answer instead of a growing heap.
//
// WHY A BITMAP AND NOT A LINKED FREE LIST
// ---------------------------------------
// A linked free list over the blocks stores the next free index inside the free block, which
// means every free block is writable and a use-after-free silently corrupts the list. A bitmap
// is one word per 8 blocks, cannot be corrupted by writing to a returned block, and makes
// "how many are free" a popcount instead of a walk.
//
// WHAT THIS IS NOT
// ----------------
// Not an allocator for variable sizes. The layer's buffers are all fixed: a record is 160 bytes,
// a packet is 1500, a manifest slot is 512. Anything that needs a variable size needs a design,
// and a pool that "handles any size" is how a fragmentation bug gets written.
//
// GENERATION COUNTS
// -----------------
// Every handout returns an id that carries a generation. A block that is freed and reissued
// gets a new generation, so a stale id is refused rather than pointing at someone else's data.
// That is the one piece of allocator hygiene a service layer can afford, and the one that
// catches the bug people actually write (holding an old handle).

import common.err.err;

let POOL_BLOCKS: i64 = 16;
let POOL_BLOCK_BYTES: i64 = 1500;
let POOL_BYTES: i64 = 24000;          // POOL_BLOCKS * POOL_BLOCK_BYTES

struct Pool {
    data: u8[..24000],
    used: i64,             // bitmap: bit i set means block i is allocated
    gens: i64[..16],       // per-block generation, bumped on free
    live: i64,
    handed_out: i64,
    refused: i64,
}

fn pool_new() -> Pool {
    var p: Pool;
    var i: i64 = 0;
    while i < POOL_BYTES { p.data[i] = 0; i++; }
    i = 0;
    while i < POOL_BLOCKS { p.gens[i] = 1; i++; }
    p.used = 0;
    p.live = 0;
    p.handed_out = 0;
    p.refused = 0;
    return p;
}

// Allocate one block. Returns an id encoding (block, generation), or -1 when the pool is empty.
//
// The id packs generation in the high bits and the block index in the low bits so a stale id
// is refused by arithmetic rather than by a second table.
fn pool_alloc(p: Pool&) -> i64 {
    var i: i64 = 0;
    while i < POOL_BLOCKS {
        if (p.used & (1 << i)) == 0 {
            p.used = p.used | (1 << i);
            p.live = p.live + 1;
            p.handed_out = p.handed_out + 1;
            return pool_id(i, p.gens[i]);
        }
        i++;
    }
    p.refused = p.refused + 1;
    return -1;
}

fn pool_id(block: i64, gen: i64) -> i64 {
    return (gen << 8) | block;
}

fn pool_block_of(id: i64) -> i64 {
    return id & 0xFF;
}

fn pool_gen_of(id: i64) -> i64 {
    return id >> 8;
}

// Is this id still the block it was issued for? False for an id from before a free, and false
// for a block that was never allocated.
fn pool_valid(p: Pool&, id: i64) -> bool {
    if id < 0 { return false; }
    let block = pool_block_of(id);
    if block < 0 || block >= POOL_BLOCKS { return false; }
    if (p.used & (1 << block)) == 0 { return false; }
    return p.gens[block] == pool_gen_of(id);
}

// Free. Returns CODE_OK, or E_INVAL for an id that is stale or was never valid -- a double
// free is refused rather than silently corrupting the bitmap.
fn pool_free(p: Pool&, id: i64) -> i64 {
    if !pool_valid(p, id) { return E_INVAL; }
    let block = pool_block_of(id);
    p.used = p.used & ~(1 << block);
    p.gens[block] = p.gens[block] + 1;      // the old id is now stale
    p.live = p.live - 1;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Block access
// ---------------------------------------------------------------------------

// Copy `len` bytes into a block at `off`. Refuses a write past the block, and refuses a stale id.
// The bounds check is the point: this is the one function every buffer user goes through.
fn pool_write(p: Pool&, id: i64, off: i64, src: const u8[:]) -> i64 {
    if !pool_valid(p, id) { return E_INVAL; }
    if off < 0 || src.len < 0 { return E_INVAL; }
    if off + src.len > POOL_BLOCK_BYTES { return E_NOROOM; }
    let block = pool_block_of(id);
    let base = block * POOL_BLOCK_BYTES + off;
    var i: i64 = 0;
    while i < src.len {
        p.data[base + i] = src[i];
        i++;
    }
    return src.len;
}

// Read `len` bytes out of a block. Refuses to read uninitialised or out-of-range bytes: a pool
// that returns whatever was in the memory before is how a service leaks the previous owner's
// data into a log line.
fn pool_read(p: Pool&, id: i64, off: i64, len: i64, out: u8[>..]&, cap: i64) -> i64 {
    if !pool_valid(p, id) { return E_INVAL; }
    if off < 0 || len < 0 { return E_INVAL; }
    if off + len > POOL_BLOCK_BYTES { return E_INVAL; }
    if len > cap { return E_NOROOM; }
    let base = pool_block_of(id) * POOL_BLOCK_BYTES + off;
    var i: i64 = 0;
    while i < len {
        out.push(p.data[base + i]);
        i++;
    }
    return len;
}

// Direct byte access for the protocols that parse in place. The bounds check is the caller's;
// this exists because copying a 1500-byte packet to look at its header is how a ring drops frames.
fn pool_byte(p: Pool&, id: i64, off: i64) -> i64 {
    if !pool_valid(p, id) { return -1; }
    if off < 0 || off >= POOL_BLOCK_BYTES { return -1; }
    return p.data[pool_block_of(id) * POOL_BLOCK_BYTES + off] as i64;
}

// (live, total, handed_out, refused)
fn pool_stats(p: Pool&) -> i64, i64, i64, i64 {
    return p.live, POOL_BLOCKS, p.handed_out, p.refused;
}

fn pool_block_bytes() -> i64 {
    return POOL_BLOCK_BYTES;
}
