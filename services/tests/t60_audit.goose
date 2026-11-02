// services/tests/t60_audit.goose
//
// B-L1-60 — test program for the audit writer and reader (B-L1-41/B-L1-42).
//
// Status: RUNS — tests/t60_audit: 33 checks, 0 failures. Measured 2026-11-02 by audit_status.py.
//
// WHAT IS UNDER TEST
// ------------------
// The audit log's value is entirely in its integrity claims, so this test attacks them:
//
//   1. Round trip: what was written reads back with the same kind, actor, sequence and body.
//   2. Sequence: the reader sees 1..n in order with no gaps, and the chain verifies.
//   3. Tampering: change one byte of one record's BODY and the chain must fail AT that
//      record -- not "somewhere", and not "the log is fine". A chain check that can only say
//      pass/fail tells an operator nothing about which records to trust.
//   4. Truncation: a record that claims to be longer than the buffer is refused, rather than
//      read past the end.
//
// What is NOT claimed: this does not prove the log is unforgeable. Someone who rewrites every
// record from the first one onward produces a log that verifies. The writer's header says so;
// so does this test's comment, because a test that implied otherwise would be the most
// dangerous kind of lie in this repo.

import audit.audit;
import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn main() {
    say("t60 audit round trip\n");

    let n0 = audit_seq();
    check("starts empty", n0 == 0);

    // --- write ---
    let s1 = audit_write(AK_BOOT, 0, 1000, "boot v1.2.3");
    check("first record", s1 == 1);
    let s2 = audit_write(AK_AGENT, 12345, 1100, "agent spawned");
    check("sequence increments", s2 == 2);
    let s3 = audit_write(AK_CAPS, 12345, 1200, "cap net granted");
    check("third record", s3 == 3);
    let s4 = audit_write(AK_DENIED, 12345, 1300, "cap storage denied");
    check("fourth record", s4 == 4);

    check("seq counter", audit_seq() == 4);

    // --- verify the chain ---
    let ok_n, bad_seq = audit_verify();
    check("chain verifies", ok_n == 4 && bad_seq == 0);

    // --- read back by kind ---
    check("count of agent records", audit_count_of(AK_AGENT) == 1);
    check("count of denied records", audit_count_of(AK_DENIED) == 1);
    check("count of a kind never written", audit_count_of(AK_UPDATE) == 0);

    let at = audit_find(AK_DENIED, 1);
    check("find locates the record", at >= 0);

    var body: u8[>..] = [];
    let n = audit_body_copy(at, body, 64);
    check("body copies", n == 18 && body[0] == 'c');
    check("body is the body, not the head", body.len == 18);

    // A head read at that offset reports the same facts the writer was given.
    var head: RecHead = RecHead {
        magic: 0,
        len: 0,
        kind: 0,
        seq: 0,
        at_ms: 0,
        actor: 0,
        digest: 0,
    };
    check("head reads", audit_read_head(at, head) > 0);
    check("head kind", head.kind == AK_DENIED);
    check("head actor", head.actor == 12345);
    check("head seq", head.seq == 4);
    check("head timestamp", head.at_ms == 1300);
    check("head length is sane", head.len > 42 && head.len < 256);

    // --- find from a later sequence skips earlier records ---
    let none = audit_find(AK_BOOT, 2);
    check("find respects from_seq", none == -1);

    // --- tampering ---
    // Copy the log, flip one byte inside the LAST record's body, and verify the COPY. The
    // chain must break at that record, which means the reader must have verified the three
    // before it -- "the log is bad" is not a useful answer, "seq 4 is where it breaks" is.
    var copy: u8[..4096] = [0; 4096];
    let bytes = audit_bytes();
    check("the log is readable as bytes", bytes.len == audit_used() && bytes.len > 168);
    var c: i64 = 0;
    while c < bytes.len && c < 4096 {
        copy[c] = bytes[c];
        c = c + 1;
    }

    var h4: RecHead = RecHead { magic: 0, len: 0, kind: 0, seq: 0, at_ms: 0, actor: 0, digest: 0 };
    let at4 = audit_find(AK_DENIED, 1);
    let body4 = audit_read_head(at4, h4);
    check("tampering target located", body4 > 0 && h4.seq == 4);

    let ok_before = ok_n;
    copy[at4 + 42] = (copy[at4 + 42] ^ 0x01) as u8;   // first body byte of the last record
    let ok_after, bad_after = audit_verify_buf(copy[..audit_used()]);
    check("tampered chain fails", bad_after == 4);
    check("records before the tamper still verify", ok_after == ok_before - 1);
    // And the untampered original still verifies: the check is over the bytes, not over a
    // flag the writer set.
    let orig_ok, orig_bad = audit_verify();
    check("the original is unaffected", orig_bad == 0 && orig_ok == ok_before);

    // --- a head that claims to run past the end is refused ---
    var past: RecHead = RecHead {
        magic: 0,
        len: 0,
        kind: 0,
        seq: 0,
        at_ms: 0,
        actor: 0,
        digest: 0,
    };
    let beyond = audit_read_head(audit_used(), past);
    check("read past the end refused", beyond == -1);
    let negative = audit_read_head(-1, past);
    check("negative offset refused", negative == -1);

    // A buffer whose last record claims more bytes than it has is refused rather than read
    // past the end.
    var clipped: u8[..4096] = [0; 4096];
    var k: i64 = 0;
    while k < audit_used() && k < 4096 {
        clipped[k] = bytes[k];
        k = k + 1;
    }
    let short_ok, short_bad = audit_verify_buf(clipped[..audit_used() - 4]);
    check("truncated buffer is caught", short_bad != 0 || short_ok < ok_before);

    // --- a full buffer refuses rather than truncating ---
    // Fill with records until the writer refuses. The refusal must be reported, and the
    // dropped counter must move -- a silent drop is the failure this counter exists for.
    var wrote: i64 = 0;
    var refused: bool = false;
    var i: i64 = 0;
    while i < 20000 && refused == false {
        if audit_write(AK_SERVICE, 0, 1400 + i, "filler record body") == AUD_NO_REC {
            refused = true;
        } else {
            wrote = wrote + 1;
        }
        i = i + 1;
    }
    check("writer eventually refuses", refused);
    check("drops are counted", audit_dropped_count() >= 1);
    // Whatever did fit must still be a valid chain: a full buffer must not corrupt what it
    // already holds.
    let final_ok, final_bad = audit_verify();
    check("the log is still coherent after a refusal", final_bad == 0);
    check("the verified prefix is non-empty", final_ok > 0);
    check("every count matches the records", final_ok == 4 + wrote);

    var r: u8[>..] = [];
    let _ = append_int(r, 32, t_pass);
    say("passed ");
    say(r);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t60 done\n");
    sys_exit(0);
}


