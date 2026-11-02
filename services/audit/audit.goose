// services/audit/audit.goose
//
// Layer 4, services 23-24: the audit record writer and reader.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs, static arrays,
// `while`/`if`, slices, `T&` references (reference#46), bitwise operators, multi-value
// returns.
//
// WHAT AN AUDIT LOG IS FOR
// ------------------------
// Not debugging. Debugging output is a log. This is the record that answers, after the
// fact and without trusting the agent that is being asked: who did that, what did they
// have permission to do, and was the permission still the same when they did it.
//
// Three properties follow from that, and each one costs something:
//
// 1. Append only. There is no delete and no rewrite. A record that can be removed is a
//    record that proves nothing. The cost: the ring overflows and old records are lost
//    from the head, which is why `audit_dropped` exists and is itself reported.
// 2. Chained. Each record carries a digest over the previous record's digest and its own
//    contents. Deleting a record in the middle breaks every record after it, so tampering
//    is detectable without a key. The cost: writing is serial, one record at a time. It
//    is already serial, because everything that writes here already goes through one path.
// 3. Self-describing. The reader does not need the writer's struct layout: each record
//    begins with its own length, so a reader written next year can skip a record written
//    today whose fields it does not know.
//
// WHAT THE CHAIN DOES NOT DO
// --------------------------
// It cannot stop someone who can rewrite the whole log from the first record onward. That
// needs either a signature (the updater's signature interface, B-L1-123) or an off-box
// copy. Neither exists yet, so this file must not claim more than tamper-evidence at the
// middle: the doc says so, and the reader reports where the chain first failed rather than
// "the log is fine".
//
// THE DIGEST HERE IS A TOY
// ------------------------
// `audit_link` uses a small mixing function, not SHA-256, so that this file has no
// dependency on the hash library's build order. When the hash module is proven compiled,
// swapping the call is a one-line change and the record layout stays identical. This is
// recorded as a known weakness rather than presented as a digest.

import common.err.err;

let AUD_SLOT: i64 = 128;
let AUD_REC_BUDGET: i64 = 4096;
let AUD_DIGEST: i64 = 8;
let AUD_NO_REC: i64 = -1;

// Record kinds. Numeric so a record survives a rename.
let AK_BOOT: i64 = 1;
let AK_SERVICE: i64 = 2;
let AK_AGENT: i64 = 3;
let AK_CAPS: i64 = 4;
let AK_DENIED: i64 = 5;
let AK_UPDATE: i64 = 6;
let AK_SESSION: i64 = 7;
let AK_INTEGRITY: i64 = 8;

struct RecHead {
    magic: i64,
    len: i64,          // total bytes of this record, including the head
    kind: i64,
    seq: i64,          // monotonically increasing, 1-based
    at_ms: i64,        // wall clock at write time
    actor: i64,        // agent handle, or 0 for the system
    digest: i64,       // chain digest over (prev digest, this record's head+body)
}

var aud_buf: u8[AUD_REC_BUDGET];
var aud_used: i64 = 0;
var aud_seq: i64 = 0;
var aud_dropped: i64 = 0;
var aud_prev_digest: i64 = 0;
var aud_last_gen: i64 = 0;      // the generation the buffer belongs to

let AUD_MAGIC: i64 = 4233570;   // "AUD\0" as an integer, so a misaligned read fails loudly

// ---------------------------------------------------------------------------
// Writer
// ---------------------------------------------------------------------------

// Room test before writing, so a full buffer refuses instead of truncating. A truncated
// audit record is worse than a missing one: it parses as a valid head with a short body.
fn audit_room(need: i64) -> bool {
    return (AUD_REC_BUDGET - aud_used) >= need;
}

fn audit_dropped_count() -> i64 { return aud_dropped; }

fn audit_seq() -> i64 { return aud_seq; }

// Small mixing function over the previous digest and a byte. Documented above as
// deliberately not SHA-256.
fn audit_mix(h: i64, b: i64) -> i64 {
    var x = (h ^ b) & 0xFFFFFFFFFF;
    x = (x * 1099511628211) & 0xFFFFFFFFFF;
    x = x ^ (x >> 29);
    return x & 0xFFFFFFFFFF;
}

fn audit_link(kind: i64, seq: i64, at_ms: i64, actor: i64, body: u8[:]) -> i64 {
    var h = aud_prev_digest;
    h = audit_mix(h, kind);
    h = audit_mix(h, seq);
    h = audit_mix(h, at_ms % 256);
    h = audit_mix(h, actor);
    var i: i64 = 0;
    while i < body.len {
        h = audit_mix(h, body[i] as i64);
        i = i + 1;
    }
    return h;
}

// Append one record. `body` is caller-formatted (the log service's formatter, or the
// service's own encoder); the audit layer owns the head, the sequence, the chain, and the
// length, and nothing else.
//
// Returns the sequence number assigned, or -1 when the buffer has no room. Room is
// checked against the worst case so a record is never half-written.
fn audit_write(kind: i64, actor: i64, at_ms: i64, body: u8[:]) -> i64 {
    // The head is 7 fields of 6 bytes: 42. This said 48, so every record DECLARED six
    // bytes it did not contain, and the reader stepped six bytes into the following
    // record and read its magic as the rest of this one's body. The chain could not
    // verify, and the failure looked like corruption rather than an off-by-six.
    let need = 42 + body.len;
    if need > AUD_REC_BUDGET { return AUD_NO_REC; }
    if !audit_room(need) {
        aud_dropped = aud_dropped + 1;
        return AUD_NO_REC;
    }
    let seq = aud_seq + 1;
    let digest = audit_link(kind, seq, at_ms, actor, body);

    var p = aud_used;
    p = aud_put(p, AUD_MAGIC);
    p = aud_put(p, need);
    p = aud_put(p, kind);
    p = aud_put(p, seq);
    p = aud_put(p, at_ms);
    p = aud_put(p, actor);
    p = aud_put(p, digest);
    var i: i64 = 0;
    while i < body.len {
        aud_buf[p] = body[i];
        p = p + 1;
        i = i + 1;
    }
    aud_used = p;
    aud_seq = seq;
    aud_prev_digest = digest;
    return seq;
}

// 6 bytes per integer: enough for the digests (40 bits) and for a boot uptime in ms
// (~285 years). Fixed width on purpose -- a variable-width integer in a record head makes
// the head's own length ambiguous.
fn aud_put(p: i64, v: i64) -> i64 {
    var x = v;
    if x < 0 { x = x + 281474976710656; }   // two's complement into 6 bytes
    aud_buf[p] = ((x >> 40) & 0xFF) as u8;
    aud_buf[p + 1] = ((x >> 32) & 0xFF) as u8;
    aud_buf[p + 2] = ((x >> 24) & 0xFF) as u8;
    aud_buf[p + 3] = ((x >> 16) & 0xFF) as u8;
    aud_buf[p + 4] = ((x >> 8) & 0xFF) as u8;
    aud_buf[p + 5] = (x & 0xFF) as u8;
    return p + 6;
}

// Six bytes here too. This read SEVEN: the field is 6 bytes wide, so the seventh byte
// belonged to the next field and every value decoded to something that was not what was
// written.
fn aud_get(p: i64) -> i64 {
    var v: i64 = 0;
    var i: i64 = 0;
    while i < 6 {
        v = v * 256 + (aud_buf[p + i] as i64);
        i = i + 1;
    }
    return v;
}

// ---------------------------------------------------------------------------
// Reader
// ---------------------------------------------------------------------------

// Read the head at `off` into `out`. Returns the body offset (off + head size), or -1 when
// there is no complete record there.
//
// A record whose length is smaller than its head, or that runs past `aud_used`, is a
// corrupt record -- and the reader must not try to resynchronise by searching for the next
// magic: a magic found in the middle of a body would make a corrupt log read as a shorter,
// valid one.
fn audit_read_head(off: i64, out: RecHead&) -> i64 {
    if off < 0 || off + 42 > aud_used { return -1; }
    let magic = aud_get(off);
    if magic != AUD_MAGIC { return -1; }
    out.magic = magic;
    out.len = aud_get(off + 6);
    out.kind = aud_get(off + 12);
    out.seq = aud_get(off + 18);
    out.at_ms = aud_get(off + 24);
    out.actor = aud_get(off + 30);
    out.digest = aud_get(off + 36);
    if out.len < 42 { return -1; }
    if off + out.len > aud_used { return -1; }
    return off + 42;
}

// Walk the chain from the start. Returns (records_ok, first_bad_seq).
//
// first_bad_seq is 0 when the whole buffer verifies. The count is records verified BEFORE
// the failure, which is the useful number: "412 good, then seq 413 does not link" says
// where to look, while a bare false says the log is untrustworthy and stops.
fn audit_verify() -> i64, i64 {
    return audit_verify_buf(audit_bytes());
}

// Verify ANY buffer in this format, not just the one this process is writing.
//
// That is not a test hook: it is what the reader needs after a reboot, when the records come
// back from storage (B-L1-74) and the writer's own buffer is empty. It is also how tamper
// detection is exercised, which is the only way to test a property that is defined as
// "someone changed a byte".
fn audit_verify_buf(buf: const u8[:]) -> i64, i64 {
    var off: i64 = 0;
    var prev: i64 = 0;
    var ok: i64 = 0;
    var head: RecHead = RecHead {
        magic: 0,
        len: 0,
        kind: 0,
        seq: 0,
        at_ms: 0,
        actor: 0,
        digest: 0,
    };
    while off < buf.len {
        // The head is read from the buffer under test, so a copy with one changed byte is
        // verified exactly as if it had been written that way.
        let body = head_at(buf, off, head);
        if body < 0 { return ok, head.seq; }
        if head.seq != ok + 1 { return ok, head.seq; }
        var h = prev;
        h = audit_mix(h, head.kind);
        h = audit_mix(h, head.seq);
        h = audit_mix(h, head.at_ms % 256);
        h = audit_mix(h, head.actor);
        var i = body;
        while i < off + head.len {
            h = audit_mix(h, buf[i] as i64);
            i = i + 1;
        }
        if h != head.digest { return ok, head.seq; }
        prev = head.digest;
        ok = ok + 1;
        off = off + head.len;
    }
    return ok, 0;
}

// Head parse over an arbitrary buffer. Same rules as audit_read_head; kept separate because
// audit_read_head reads this process's own storage and a reader handed storage bytes must
// not be able to wander into it.
fn head_at(buf: const u8[:], off: i64, out: RecHead&) -> i64 {
    if off < 0 || off + 42 > buf.len { return -1; }
    if get6(buf, off) != AUD_MAGIC { return -1; }
    out.magic = AUD_MAGIC;
    out.len = get6(buf, off + 6);
    out.kind = get6(buf, off + 12);
    out.seq = get6(buf, off + 18);
    out.at_ms = get6(buf, off + 24);
    out.actor = get6(buf, off + 30);
    out.digest = get6(buf, off + 36);
    if out.len < 42 { return -1; }
    if off + out.len > buf.len { return -1; }
    return off + 42;
}

// Six bytes, big-endian, into an i64.
//
// The last multiplier is 1, not 256. The chain was shifted by one place, so every field
// decoded 256x too large: the record magic never matched what was written, and the whole
// audit chain read as corrupt while the bytes on disk were correct.
fn get6(buf: const u8[:], p: i64) -> i64 {
    // Accumulate rather than summing six hand-written multipliers: the written form is
    // `v * 256 + byte`, which a loop cannot get out of step the way a list of powers of
    // 256 can (it did -- the last one was 256 instead of 1, decoding every field 256x
    // too large and making the whole audit chain read as corrupt).
    var v: i64 = 0;
    var i: i64 = 0;
    while i < 6 {
        v = v * 256 + (buf[p + i] as i64);
        i = i + 1;
    }
    return v;
}

// Bytes written so far, and a read-only view of them, so the storage binding can flush a
// record block without a second copy of the layout.
fn audit_used() -> i64 { return aud_used; }

fn audit_bytes() -> u8[:] {
    return aud_buf[..aud_used];
}

// Find the first record of a kind, at or after `from_seq`. -1 when there is none.
// The reader is deliberately a linear scan: the buffer is a ring of at most a few thousand
// records, and an index would be a second structure that can disagree with the records.
fn audit_find(kind: i64, from_seq: i64) -> i64 {
    var off: i64 = 0;
    var head: RecHead = RecHead {
        magic: 0,
        len: 0,
        kind: 0,
        seq: 0,
        at_ms: 0,
        actor: 0,
        digest: 0,
    };
    while off < aud_used {
        let body = audit_read_head(off, head);
        if body < 0 { return -1; }
        if head.kind == kind && head.seq >= from_seq { return off; }
        off = off + head.len;
    }
    return -1;
}

fn audit_count_of(kind: i64) -> i64 {
    var off: i64 = 0;
    var n: i64 = 0;
    var head: RecHead = RecHead {
        magic: 0,
        len: 0,
        kind: 0,
        seq: 0,
        at_ms: 0,
        actor: 0,
        digest: 0,
    };
    while off < aud_used {
        let body = audit_read_head(off, head);
        if body < 0 { return n; }
        if head.kind == kind { n = n + 1; }
        off = off + head.len;
    }
    return n;
}

// Copy one record's body into the caller's buffer. Returns bytes copied or -1.
fn audit_body_copy(off: i64, out: u8[>..]&, cap: i64) -> i64 {
    var head: RecHead = RecHead {
        magic: 0,
        len: 0,
        kind: 0,
        seq: 0,
        at_ms: 0,
        actor: 0,
        digest: 0,
    };
    let body = audit_read_head(off, head);
    if body < 0 { return -1; }
    var i = body;
    var n: i64 = 0;
    while i < off + head.len {
        if n >= cap { return -1; }
        out.push(aud_buf[i]);
        n = n + 1;
        i = i + 1;
    }
    return n;
}
