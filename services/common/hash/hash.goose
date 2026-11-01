// services/common/hash/hash.goose
//
// CRC32 (IEEE 802.3) and SHA-256 (FIPS 180-4), written from the published
// specifications. The updater's verification depends on SHA-256; record
// integrity depends on CRC32.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0:
// - unsigned arithmetic wraps in every build ................. tutorial#3, stdlib#1
// - signed overflow aborts in debug, wraps in release ......... tutorial#3
// - `u32`/`u64`/`u8` integer keywords ........................ list_keywords
// - `while`, `if`, `return`, `as` casts ...................... list_keywords
//
// WHY EVERY VALUE HERE IS UNSIGNED
// --------------------------------
// The docs are explicit: "Unsigned arithmetic wraps, in every build, by
// definition, because that is what hashes and PRNGs mean by unsigned math.
// Signed overflow aborts in debug and wraps in release" (tutorial#3). A hash
// implemented over signed integers would therefore behave differently in a debug
// build, which is the one place a test would catch it -- and identical in
// release, which is where it ships. So: no signed arithmetic touches a word in
// this file, and that is a correctness requirement, not a style choice.
//
// TEST VECTORS live in README.md and are checked by B-L1-55. Nothing here is
// claimed correct until those vectors pass on a real toolchain.

// ---------------------------------------------------------------------------
// Rotations
// ---------------------------------------------------------------------------

fn rotr32(x: u32, n: u32) -> u32 {
    // n is always 1..31 here; a shift by 32 would be undefined in C, so the
    // caller never passes 0 or 32 and this function does not guard it.
    return (x >> n) | (x << (32 - n));
}

fn shr32(x: u32, n: u32) -> u32 {
    return x >> n;
}

// ---------------------------------------------------------------------------
// CRC32, IEEE 802.3: reflected polynomial 0xEDB88320, init 0xFFFFFFFF, final xor
// ---------------------------------------------------------------------------
//
// Bit-at-a-time rather than a 256-entry table: the table costs 1 KiB of static
// storage per service that links it, and the records this protects are tens of
// bytes. If a future path hashes megabytes, a table is a size/time trade the
// size audit (B-L1-136) should decide with numbers, not a guess made here.

fn crc32(data: u8[:]) -> u32 {
    var crc: u32 = 0xFFFFFFFF;
    var i: i64 = 0;
    while i < data.len {
        crc = crc ^ (data[i] as u32);
        var bit: i64 = 0;
        while bit < 8 {
            if (crc & 1) != 0 {
                crc = (crc >> 1) ^ 0xEDB88320 as u32;
            } else {
                crc = crc >> 1;
            }
            bit++;
        }
        i++;
    }
    return crc ^ 0xFFFFFFFF;
}

// Incremental form, for a record assembled in pieces. `crc` is carried between
// calls and the final xor is the caller's last step via crc32_finish.
fn crc32_update(crc: u32, data: u8[:]) -> u32 {
    var c = crc;
    var i: i64 = 0;
    while i < data.len {
        c = c ^ (data[i] as u32);
        var bit: i64 = 0;
        while bit < 8 {
            if (c & 1) != 0 {
                c = (c >> 1) ^ 0xEDB88320 as u32;
            } else {
                c = c >> 1;
            }
            bit++;
        }
        i++;
    }
    return c;
}

fn crc32_start() -> u32 { return 0xFFFFFFFF; }
fn crc32_finish(crc: u32) -> u32 { return crc ^ 0xFFFFFFFF; }

// ---------------------------------------------------------------------------
// SHA-256, FIPS 180-4
// ---------------------------------------------------------------------------

// The 64 round constants: the first 32 bits of the fractional parts of the cube
// roots of the first 64 primes. Written out rather than computed, because a
// computed table needs a floating-point cube root at start-up.
let SHA256_K: u32[..64] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5, 0x3956c25b, 0x59f111f1,
    0x923f82a4, 0xab1c5ed5, 0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174, 0xe49b69c1, 0xefbe4786,
    0x0fc19dc6, 0x240ca1cc, 0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7, 0xc6e00bf3, 0xd5a79147,
    0x06ca6351, 0x14292967, 0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85, 0xa2bfe8a1, 0xa81a664b,
    0xc24b8b70, 0xc76c51a3, 0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5, 0x391c0cb3, 0x4ed8aa4a,
    0x5b9cca4f, 0x682e6ff3, 0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2,
];

struct Sha256Ctx {
    h: u32[..8],
    // Bytes of the current partial block, and its length.
    block: u8[..64],
    block_len: i64,
    total_len: u64,     // bytes hashed so far
}

fn sha256_init() -> Sha256Ctx {
    return Sha256Ctx {
        h: [
            0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a,
            0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19,
        ],
        block: [],
        block_len: 0,
        total_len: 0,
    };
}

fn sha256_ch(x: u32, y: u32, z: u32) -> u32 {
    return (x & y) ^ (~x & z);
}

fn sha256_maj(x: u32, y: u32, z: u32) -> u32 {
    return (x & y) ^ (x & z) ^ (y & z);
}

// One compression block. `p` is the index into `data` where the block starts;
// the final block is assembled in a local buffer and passed the same way, so
// there is exactly one implementation of the round function.
fn sha256_compress(ctx: Sha256Ctx&, data: u8[:], p: i64) {
    var w: u32[..64];
    var i: i64 = 0;

    // First 16 words: big-endian, as the specification requires.
    while i < 16 {
        let b = p + i * 4;
        w[i] = ((data[b] as u32) << 24)
             | ((data[b + 1] as u32) << 16)
             | ((data[b + 2] as u32) << 8)
             | (data[b + 3] as u32);
        i++;
    }
    while i < 64 {
        let s0 = rotr32(w[i - 15], 7) ^ rotr32(w[i - 15], 18) ^ shr32(w[i - 15], 3);
        let s1 = rotr32(w[i - 2], 17) ^ rotr32(w[i - 2], 19) ^ shr32(w[i - 2], 10);
        w[i] = w[i - 16] + s0 + w[i - 7] + s1;     // unsigned: wraps
        i++;
    }

    var a = ctx.h[0];
    var b = ctx.h[1];
    var c = ctx.h[2];
    var d = ctx.h[3];
    var e = ctx.h[4];
    var f = ctx.h[5];
    var g = ctx.h[6];
    var h = ctx.h[7];

    i = 0;
    while i < 64 {
        let big_s1 = rotr32(e, 6) ^ rotr32(e, 11) ^ rotr32(e, 25);
        let t1 = h + big_s1 + sha256_ch(e, f, g) + SHA256_K[i] + w[i];
        let big_s0 = rotr32(a, 2) ^ rotr32(a, 13) ^ rotr32(a, 22);
        let t2 = big_s0 + sha256_maj(a, b, c);

        h = g;
        g = f;
        f = e;
        e = d + t1;
        d = c;
        c = b;
        b = a;
        a = t1 + t2;
        i++;
    }

    ctx.h[0] = ctx.h[0] + a;
    ctx.h[1] = ctx.h[1] + b;
    ctx.h[2] = ctx.h[2] + c;
    ctx.h[3] = ctx.h[3] + d;
    ctx.h[4] = ctx.h[4] + e;
    ctx.h[5] = ctx.h[5] + f;
    ctx.h[6] = ctx.h[6] + g;
    ctx.h[7] = ctx.h[7] + h;
}

// Feed bytes. Whole blocks are compressed as they arrive; a tail is kept for the
// next call, which is why this can hash a file in chunks with no buffer growth.
fn sha256_update(ctx: Sha256Ctx&, data: u8[:]) -> bool {
    ctx.total_len = ctx.total_len + data.len as u64;

    var i: i64 = 0;
    // Top up a partial block first.
    while i < data.len && ctx.block_len > 0 {
        ctx.block[ctx.block_len] = data[i];
        ctx.block_len++;
        i++;
        if ctx.block_len == 64 {
            // Compress the assembled block, then start a fresh one. `block` is a
            // fixed array of 64, so the slice below is exactly one block.
            sha256_compress(ctx, ctx.block[:], 0);
            ctx.block_len = 0;
        }
    }

    // Then whole blocks straight from the input, no copy.
    while i + 64 <= data.len {
        sha256_compress(ctx, data, i);
        i = i + 64;
    }

    // Then keep the tail.
    while i < data.len {
        ctx.block[ctx.block_len] = data[i];
        ctx.block_len++;
        i++;
    }
    return true;
}

// Finish: pad to 512 bits with 0x80, zeros, and the bit length big-endian, then
// write the digest into the caller's buffer as 32 bytes.
fn sha256_final(ctx: Sha256Ctx&, out: u8[>..]&, cap: i64) -> bool {
    if cap < 32 { return false; }

    // Bit length must be the length of the message, not of the padded message.
    let bits = ctx.total_len * 8 as u64;

    // 0x80, then zeros, until 8 bytes remain in a 64-byte block.
    var pad_block: u8[..64];
    var n = ctx.block_len;
    var i: i64 = 0;
    while i < 64 { pad_block[i] = 0; i++; }
    // Copy the tail.
    i = 0;
    while i < n { pad_block[i] = ctx.block[i]; i++; }
    pad_block[n] = 0x80;
    n++;

    if n > 56 {
        // The length does not fit in this block: compress it, then a zero block
        // with only the length.
        sha256_compress(ctx, pad_block[:], 0);
        i = 0;
        while i < 64 { pad_block[i] = 0; i++; }
        n = 0;
    }

    // Length in bits, big-endian, in the last 8 bytes.
    i = 0;
    while i < 8 {
        pad_block[56 + i] = ((bits >> (56 - i * 8)) & 0xFF) as u8;
        i++;
    }

    sha256_compress(ctx, pad_block[:], 0);

    // Digest: eight big-endian words.
    i = 0;
    while i < 32 {
        let word = ctx.h[i / 4];
        let shift = (3 - (i % 4)) * 8;
        out.push(((word >> shift) & 0xFF) as u8);
        i++;
    }
    return true;
}

// One-shot: hash a slice, write 32 bytes. The common case, and the one the
// updater uses on a manifest or a small file.
fn sha256(data: u8[:], out: u8[>..]&, cap: i64) -> bool {
    var ctx = sha256_init();
    if !sha256_update(ctx, data) { return false; }
    return sha256_final(ctx, out, cap);
}

// ---------------------------------------------------------------------------
// Constant-time comparison
// ---------------------------------------------------------------------------
//
// The updater compares a computed digest against a signed one. A comparison that
// returns early on the first differing byte leaks how much of a forgery was
// right, which is a gift to anyone attacking an updater. This form always reads
// every byte.
fn equal_constant_time(a: u8[:], b: u8[:]) -> bool {
    if a.len != b.len { return false; }
    var diff: u8 = 0;
    var i: i64 = 0;
    while i < a.len {
        diff = diff | (a[i] ^ b[i]);
        i++;
    }
    return diff == 0;
}
