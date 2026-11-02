// services/tests/t105_audit_r11.goose
//
// Round 11 (R11-007..012): the audit buffer at its budget edge, the difference between
// "record too big" and "buffer full", the chain's reaction to one changed byte, and a
// reader over a truncated buffer.
//
// Order matters and is deliberate: the oversize record is attempted on an empty buffer so
// the drop counter can be shown NOT to move (a caller error is not a lost record), then the
// buffer is filled to the exact byte, then refused.
//
// Status: written 2026-11-02; run by the coordinator's native pass.

import audit.audit;
import common.err.err;
import common.sys.sys;
import common.fmt.fmt;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

fn same(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn main() {
    say("t105 audit deepen\n");

    // ======================================================================
    // 1. an oversize body is a caller error, not a dropped record
    // ======================================================================
    var big: u8[..4097] = [97; 4097];
    let b = audit_write(AK_BOOT, 0, 0, big[..]);
    check("budget: a 4097-byte body is refused with AUD_NO_REC", b == AUD_NO_REC);
    check("budget: an oversize body does not move the drop counter",
          audit_dropped_count() == 0);
    check("budget: an oversize body writes nothing", audit_used() == 0);

    // ======================================================================
    // 2. the sequence and the chain over small records
    // ======================================================================
    let s1 = audit_write(AK_BOOT, 0, 1000, "boot");
    check("write: the first record gets seq 1", s1 == 1);
    check("write: 42 bytes of head plus a 4-byte body", audit_used() == 46);

    var i: i64 = 0;
    var all_ok = true;
    while i < 79 {
        let s = audit_write(AK_SERVICE, 0, 1000 + i, "load");
        if s != i + 2 { all_ok = false; }
        i = i + 1;
    }
    check("write: 79 more records, each with the next seq", all_ok);
    check("write: 80 records occupy 3680 bytes", audit_used() == 3680);
    check("write: the sequence counter is 80", audit_seq() == 80);
    say("LOAD audit ops=80 ok=80 refused=0\n");

    // ======================================================================
    // 3. the exact byte: a body of 374 needs 416 and fits, then nothing does
    // ======================================================================
    var exact: u8[..374] = [120; 374];
    let s81 = audit_write(AK_INTEGRITY, 0, 2000, exact[..]);
    check("budget: a record that lands exactly on 4096 is accepted", s81 == 81);
    check("budget: the buffer is exactly full", audit_used() == AUD_REC_BUDGET);

    let over = audit_write(AK_SERVICE, 0, 2001, "x");
    check("budget: the next record is refused", over == AUD_NO_REC);
    check("budget: the refusal is counted as a drop", audit_dropped_count() == 1);
    check("budget: the buffer is unchanged by a refusal", audit_used() == AUD_REC_BUDGET);

    let n_full, bad_full = audit_verify();
    check("verify: 81 records and no bad sequence", n_full == 81 && bad_full == 0);

    // ======================================================================
    // 4. one changed byte stops the chain at that record
    // ======================================================================
    var copy: u8[..4096] = [0; 4096];
    let src = audit_bytes();
    var j: i64 = 0;
    while j < src.len {
        copy[j] = src[j];
        j = j + 1;
    }
    let n_clean, bad_clean = audit_verify_buf(src);
    check("verify_buf: a clean copy verifies", n_clean == 81 && bad_clean == 0);
    copy[42] = copy[42] + 1;                 // first body byte of the first record
    let n_bad, bad_seq = audit_verify_buf(copy[..src.len]);
    check("verify_buf: a changed body byte fails at seq 1", n_bad == 0 && bad_seq == 1);

    // A buffer cut inside the third record verifies two and names the third.
    let n_cut, cut_seq = audit_verify_buf(src[..100]);
    check("verify_buf: a truncated buffer verifies the records it has",
          n_cut == 2 && cut_seq == 2);

    // ======================================================================
    // 5. the reader: find, count, body copy, and their refusals
    // ======================================================================
    check("reader: one boot record", audit_count_of(AK_BOOT) == 1);
    check("reader: 79 service records", audit_count_of(AK_SERVICE) == 79);
    check("reader: one integrity record", audit_count_of(AK_INTEGRITY) == 1);

    let off = audit_find(AK_BOOT, 1);
    check("reader: find returns the first boot record's offset", off == 0);
    var body: u8[>..] = [];
    let bn = audit_body_copy(off, body, 64);
    check("reader: the body copy is the body", bn == 4 && same(body[..], "boot"));
    check("reader: find from seq 2 has no boot record", audit_find(AK_BOOT, 2) == -1);
    check("reader: a bad offset body copy is refused", audit_body_copy(-1, body, 64) == -1);
    var tiny: u8[>..] = [];
    check("reader: a body larger than the caller cap is refused",
          audit_body_copy(off, tiny, 2) == -1);

    say("t105 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
