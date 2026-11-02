// services/tests/t74_failure.goose
//
// BF5-02 — the failure matrix, exercised rather than described.
//
// Status: RUNS — measured 2026-11-02 by `run_native.sh`; this line is rewritten by
// `audit_status.py` when the count changes.
//
// WHAT THIS FILE IS FOR
// ---------------------
// Every service in the corpus claims a failure behaviour in its header: the log drops records
// and counts them, the filesystem refuses a superblock it cannot verify, the audit trail
// detects a changed byte. Those claims were reviewed, not driven. This test drives the three
// whose failure would be silent — a lost log line, a mounted filesystem with a bad superblock,
// an audit record that verifies after being edited — because silent failure is the class that
// costs a real incident rather than a demo.
//
// The rest of the matrix lives in the tests named in FAILURE_MATRIX.md; this file only exists
// to close the cells that had no test at all.

import fs.fs;
import storage.storage;
import logd.logd;
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
    say("t74 failure paths\n");

    // ---------------------------------------------------------------------------------
    // 1. logd: a full ring must count the loss, and an error must still get out
    // ---------------------------------------------------------------------------------
    logd_init();
    var i: i64 = 0;
    var accepted: i64 = 0;
    while i < 200 {
        if log_info("t74", "flood record") { accepted = accepted + 1; }
        i = i + 1;
    }
    let st = loss_stats();
    check("the ring accepted records", accepted > 0 && accepted <= 64);
    check("the flood was refused, not silently absorbed", st.full > 0);
    check("every refusal is counted", accepted + st.full == 200);

    // An error record flushes, and the flush drains the ring, so it must be accepted even
    // after the flood. If this fails, the priority policy is a comment, not a behaviour.
    check("an error is accepted after the ring filled", log_error("t74", "still matters"));
    check("the error is not counted as dropped", loss_stats().full == st.full);

    // A message too long for one slot is refused and counted separately: truncating it
    // would produce a log line that says something the service never said.
    var long_buf: u8[>..] = [];
    var k: i64 = 0;
    while k < 400 { long_buf.push('x'); k = k + 1; }
    let before_long = loss_stats().long;
    let long_ok = log_info("t74", long_buf[..]);
    check("an overlong record is refused", !long_ok);
    check("and counted as long, not as full", loss_stats().long == before_long + 1);

    // Below the minimum level: refused, counted, and never formatted.
    let before_level = loss_stats().level;
    let dbg = log(LVL_DEBUG, "t74", "debug noise");
    check("a debug record below the level is refused", !dbg);
    check("and counted as level", loss_stats().level == before_level + 1);

    // ---------------------------------------------------------------------------------
    // 2. the filesystem: a superblock that cannot be verified must not mount
    // ---------------------------------------------------------------------------------
    check("format a disk", fs_format(64) == CODE_OK);
    check("umount before corrupting", fs_umount() == CODE_OK);

    // Bad magic. A mount that accepts this would read a free-block count from whatever the
    // block happened to contain, and then write over live data with a straight face.
    var blk: u8[..512] = [0; 512];
    var b: i64 = 0;
    while b < 512 { blk[b] = 0xAA; b = b + 1; }
    check("writing garbage over the superblock", storage_write(0, blk) == CODE_OK);
    check("a superblock with no magic refuses to mount", fs_mount() == E_INVAL);

    // Bad CRC with a good magic: the corruption a bit flip actually produces. This is the
    // case a magic check alone would pass, which is why the CRC exists.
    check("reformat", fs_format(64) == CODE_OK);
    check("umount before flipping a covered byte", fs_umount() == CODE_OK);
    check("read the good superblock", storage_read(0, blk) == CODE_OK);
    var saved: u8 = blk[36];          // low byte of the free-block count
    blk[36] = (saved + 1) as u8;      // one bit's worth of change, still a plausible count
    check("write the flipped superblock", storage_write(0, blk) == CODE_OK);
    check("a superblock whose CRC fails refuses to mount", fs_mount() == E_VERIFY);
    check("reformat after the corruption", fs_format(64) == CODE_OK);

    // ---------------------------------------------------------------------------------
    // 3. the audit trail: a changed byte must break the chain
    // ---------------------------------------------------------------------------------
    let a1 = audit_write(1, 7, 1000, "boot start");
    let a2 = audit_write(2, 7, 1001, "service up");
    check("two records written", a1 != AUD_NO_REC && a2 != AUD_NO_REC);

    let good_ok, good_seq = audit_verify();
    check("the trail verifies as written", good_ok == 2 && good_seq == 0);

    var copy: u8[..4096] = [0; 4096];
    let used = audit_used();
    check("the trail has bytes", used > 0);
    var c: i64 = 0;
    while c < used && c < 4096 {
        copy[c] = audit_bytes()[c];
        c = c + 1;
    }
    check("a copy verifies the same", audit_verify_buf(copy[0..used]) == 2);

    // Flip one byte of the first record's body. The digest covers the body, so the chain
    // must stop at record 1 -- reporting "one record verified" is the useful answer; the
    // dangerous answer is "two".
    var flipped: u8[..4096] = [0; 4096];
    c = 0;
    while c < used && c < 4096 {
        flipped[c] = copy[c];
        c = c + 1;
    }
    let body_at: i64 = 42;            // the body starts right after the 42-byte head
    flipped[body_at] = (flipped[body_at] + 1) as u8;
    let tampered_ok, tampered_seq = audit_verify_buf(flipped[0..used]);
    check("a tampered record does not verify", tampered_ok < 2);
    check("the verifier names the record it stopped at", tampered_seq >= 1);

    // A truncated trail: the last record's bytes are gone. Verification must not read past
    // the end and must not claim the record it cannot see.
    let short_ok, _short_seq = audit_verify_buf(copy[0..(used / 2)]);
    check("a truncated trail verifies fewer records", short_ok < 2);

    say("t74 done  pass=");
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
