// services/audit/retention.goose
//
// B-L1-115 — Audit retention: compaction with the chain still intact.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// THE PROBLEM, STATED PROPERLY
// ----------------------------
// The audit store is a hash-chained append-only log: each record's digest covers the previous
// digest, so deleting a record from the middle breaks every record after it. Verification
// (audit_verify_buf) checks two things -- contiguous sequence numbers starting at 1, and each
// digest -- which means "delete the oldest N records" is not a file operation, it is a
// RE-CHAINING: every surviving record gets a new sequence number and a new digest.
//
// That is what this file does, and it is why compaction has to be a deliberate, recorded act
// rather than a background tidy-up. The compacted file is a new chain. It verifies. It also
// no longer proves anything about the records that were dropped, which is why the caller
// writes an integrity record into the LIVE log saying what was dropped and when.
//
// WHAT IS NEVER DROPPED
// ---------------------
// Kinds listed in `keep_kinds` survive compaction regardless of age: an integrity record
// explaining an earlier compaction, or a denied-capability record, is exactly the kind of
// thing that must outlive the policy that wanted the space back. The store can therefore
// exceed `max_records` -- deliberately, and `kept` reports the true count so nobody has to
// guess whether the policy was honoured.
//
// WHAT IS NOT HERE
// ----------------
// No timer, no size trigger, no automatic compaction. A policy that fires itself during a
// boot is a policy that can drop evidence of the failure that is being debugged.

import common.err.err;
import audit.audit;

let RET_REC_HEAD: i64 = 42;          // the fixed head, as aud_put writes it

struct RetPolicy {
    max_records: i64,                // 0 = keep everything
    keep_kinds: i64,                 // bitmask over AK_*
}

struct RetResult {
    kept: i64,
    dropped: i64,
    bytes: i64,
    protected: i64,                  // survivors kept only because of keep_kinds
}

fn ret_policy(max_records: i64, keep_kinds: i64) -> RetPolicy {
    return RetPolicy { max_records: max_records, keep_kinds: keep_kinds };
}

// Compact `src` into `out`. Returns (result, code).
//
// E_CORRUPT when the input does not parse: a compaction over a broken chain would launder it
// into a clean-looking one, which is the single worst thing this file could do.
// E_NOROOM when the output does not fit, with `result.kept` counting what was written before
// the failure -- the caller must discard the partial output, not ship it.
fn ret_compact(src: const u8[:], p: RetPolicy&, out: u8[>..]&, cap: i64) -> RetResult, i64 {
    var res: RetResult;
    res.kept = 0;
    res.dropped = 0;
    res.bytes = 0;
    res.protected = 0;

    // Pass 1: count, and refuse a broken input before writing anything.
    var total: i64 = 0;
    var off: i64 = 0;
    var head: RecHead;
    while off < src.len {
        let body = head_at(src, off, head);
        if body < 0 { return res, E_CORRUPT; }
        total = total + 1;
        off = off + head.len;
    }
    if total == 0 { return res, CODE_OK; }

    var to_drop: i64 = 0;
    if p.max_records > 0 && total > p.max_records { to_drop = total - p.max_records; }

    // Pass 2: re-emit survivors with a fresh sequence and a fresh chain.
    var prev: i64 = 0;
    var seq: i64 = 1;
    var ordinal: i64 = 0;
    off = 0;
    while off < src.len {
        let body_off = head_at(src, off, head);
        if body_off < 0 { return res, E_CORRUPT; }

        let protected = (p.keep_kinds & (1 << head.kind)) != 0;
        let drop = ordinal < to_drop && !protected;
        if !drop {
            // Digest over (prev, kind, new_seq, at_ms % 256, actor, body) -- the exact order
            // audit_verify_buf recomputes, or the output would not verify.
            var h = prev;
            h = audit_mix(h, head.kind);
            h = audit_mix(h, seq);
            h = audit_mix(h, head.at_ms % 256);
            h = audit_mix(h, head.actor);
            var i = body_off;
            while i < off + head.len {
                h = audit_mix(h, src[i] as i64);
                i++;
            }

            let need = RET_REC_HEAD + (off + head.len - body_off);
            if out.len + need > cap { return res, E_NOROOM; }
            ret_put6(out, cap, AUD_MAGIC);
            ret_put6(out, cap, need);
            ret_put6(out, cap, head.kind);
            ret_put6(out, cap, seq);
            ret_put6(out, cap, head.at_ms);
            ret_put6(out, cap, head.actor);
            ret_put6(out, cap, h);
            i = body_off;
            while i < off + head.len {
                out.push(src[i]);
                i++;
            }

            prev = h;
            seq = seq + 1;
            res.kept = res.kept + 1;
            if protected && ordinal < to_drop { res.protected = res.protected + 1; }
        } else {
            res.dropped = res.dropped + 1;
        }
        ordinal = ordinal + 1;
        off = off + head.len;
    }
    res.bytes = out.len;
    return res, CODE_OK;
}

// The body of the integrity record the caller writes after a compaction. Text, not binary:
// a human reading the log is the point of the record.
//
// Shape: "compacted: kept=<n> dropped=<n> protected=<n> max=<n>". The caller appends the
// timestamp and actor by writing it as an AK_INTEGRITY record.
fn ret_note(kept: i64, dropped: i64, protected_kinds: i64, max_records: i64, out: u8[>..]&, cap: i64) -> i64 {
    if !ret_text(out, cap, "compacted: kept=") { return -1; }
    if !ret_num(out, cap, kept) { return -1; }
    if !ret_text(out, cap, " dropped=") { return -1; }
    if !ret_num(out, cap, dropped) { return -1; }
    if !ret_text(out, cap, " protected=") { return -1; }
    if !ret_num(out, cap, protected_kinds) { return -1; }
    if !ret_text(out, cap, " max=") { return -1; }
    if !ret_num(out, cap, max_records) { return -1; }
    return out.len;
}

// Would compaction do anything? Cheaper than compacting to find out, and it is the question
// a health check actually asks.
fn ret_needed(count: i64, p: RetPolicy&) -> bool {
    if p.max_records <= 0 { return false; }
    return count > p.max_records;
}

// ---------------------------------------------------------------------------
// Emit helpers
// ---------------------------------------------------------------------------

fn ret_put6(out: u8[>..]&, cap: i64, v: i64) {
    var x = v;
    if x < 0 { x = x + 281474976710656; }
    if out.len + 6 > cap { return; }     // callers check the total before calling
    out.push(((x >> 40) & 0xFF) as u8);
    out.push(((x >> 32) & 0xFF) as u8);
    out.push(((x >> 24) & 0xFF) as u8);
    out.push(((x >> 16) & 0xFF) as u8);
    out.push(((x >> 8) & 0xFF) as u8);
    out.push((x & 0xFF) as u8);
}

fn ret_text(out: u8[>..]&, cap: i64, s: const u8[:]) -> bool {
    if out.len + s.len > cap { return false; }
    var i: i64 = 0;
    while i < s.len { out.push(s[i]); i++; }
    return true;
}

fn ret_num(out: u8[>..]&, cap: i64, v: i64) -> bool {
    if v < 0 { return ret_text(out, cap, "-"); }
    if v < 10 {
        if out.len + 1 > cap { return false; }
        out.push((48 + v) as u8);
        return true;
    }
    var digits: i64 = 0;
    var x = v;
    while x > 0 { digits++; x = x / 10; }
    var buf: u8[..20];
    if digits > 20 { return false; }
    var i: i64 = 0;
    x = v;
    while i < digits { buf[digits - 1 - i] = (48 + (x % 10)) as u8; x = x / 10; i++; }
    if out.len + digits > cap { return false; }
    i = 0;
    while i < digits { out.push(buf[i]); i++; }
    return true;
}
