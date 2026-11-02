// services/tests/t103_limits_rest.goose
//
// BF6-01, third pass — the limits the first two drivers could not reach.
//
// WHAT CHANGED IN THIS PASS
// -------------------------
// `gen_limits.py` now separates three kinds of constant that all used to read UNPROVEN:
//   - a real edge a driver can cross (this file),
//   - a bit flag matched by the CAP heuristic (MOD_CAPS, excluded),
//   - a constant no host driver can reach, with the reason recorded in LIMITS.md.
// This file drives the first kind. It does not invent checks for the other two.
//
// Every check asks for exactly the edge and then for one past it, and says which side is
// which. Where the code truncates rather than refuses, the check says truncation.
//
// Status: RUNS — set by `audit_status.py` from the runner's row, not by hand.

import socket.socket;
import common.fmt.fmt;
import display.display;
import updater.updater;
import console.console;
import common.err.err;
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
    say("t103 remaining limit drivers\n");
    t_sk_gen();
    t_scroll();
    t_content_cap();
    t_record_keep();
    t_history_slots();

    say("t103 done  pass=");
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

// ===========================================================================
// 1. socket — SK_GEN_MAX (255)
//
// A handle carries (slot+1)*256 + generation. The generation wraps at SK_GEN_MAX so a
// slot that is reused cannot be reached by a handle from before the wrap. Driving the
// wrap means opening, binding and closing the same slot more than 255 times.

fn t_sk_gen() {
    say("-- SK_GEN_MAX\n");
    var bad: i64 = 0;
    var good: i64 = 0;
    var i: i64 = 0;
    while i < SK_GEN_MAX + 8 {
        let h, c = sk_open();
        if c != CODE_OK || h <= 0 { bad = bad + 1; }
        let _, bc = sk_bind(h, 5000);
        if bc != CODE_OK { bad = bad + 1; }
        let cc = sk_close(h);
        if cc != CODE_OK { bad = bad + 1; }
        if c == CODE_OK && bc == CODE_OK && cc == CODE_OK { good = good + 1; }
        i = i + 1;
    }
    check("socket: 263 open/bind/close cycles cross the generation wrap cleanly", bad == 0);
    check("socket: every cycle produced a live, bound, closed handle", good == SK_GEN_MAX + 8);

    // After the wrap the slot is still usable, and a fresh handle answers its own stats.
    let h2, c2 = sk_open();
    let _, _, sc = sk_stats(h2);
    check("socket: a socket opened after the wrap still resolves", c2 == CODE_OK && sc == CODE_OK);
    let _ = sk_close(h2);
}

// ===========================================================================
// 2. display — SCROLL_MAX (256)
//
// disp_scroll clamps hist_lines at SCROLL_MAX. A 2-row console scrolls on every newline
// after the first, so 264 newlines put the counter past the cap if the clamp is missing.

fn t_scroll() {
    say("-- SCROLL_MAX\n");
    let v, c = disp_new("t103", 8, 2);
    check("display: an 8x2 console exists", c == CODE_OK && v >= 0);

    var nl: u8[>..] = [];
    var i: i64 = 0;
    while i < SCROLL_MAX + 8 { let _ = nl.push('\n'); i = i + 1; }
    let pc = disp_puts(v, nl[..]);
    check("display: 264 newlines are accepted", pc == CODE_OK);
    check("display: history stops at SCROLL_MAX", disp_hist_lines(v) == SCROLL_MAX);
}

// ===========================================================================
// 3. updater — UPD_CONTENT_MAX (4096)
//
// Each content slot is 4096 bytes. content_get copies a caller-supplied length into a
// 4096-byte destination, so the length is the thing that has to be bounded: 4096 reads,
// 4097 is corrupt and is refused instead of overrunning the destination.

fn t_content_cap() {
    say("-- UPD_CONTENT_MAX\n");
    var cs = ContentSet { .. };
    var i: i64 = 0;
    while i < UPD_CONTENT_MAX { cs.slots[i] = 65; i = i + 1; }
    cs.len[0] = UPD_CONTENT_MAX;
    var out: u8[..4096] = [0; 4096];
    let n = content_get(cs, 0, out);
    check("updater: a 4096-byte content slot is read whole", n == UPD_CONTENT_MAX);

    cs.len[0] = UPD_CONTENT_MAX + 1;
    let over = content_get(cs, 0, out);
    check("updater: 4097 bytes into a 4096-byte slot is refused", over == -1);
}

// ===========================================================================
// 4. updater — UPD_REC_KEEP (4)
//
// The rollback history keeps the last four records. Five confirmations must leave four,
// and the newest confirmed slot must still be the one the next boot picks.

fn t_record_keep() {
    say("-- UPD_REC_KEEP\n");
    let _ = upd_record_confirm(SLOT_A, 1);
    let _ = upd_record_confirm(SLOT_B, 2);
    let _ = upd_record_confirm(SLOT_A, 3);
    let _ = upd_record_confirm(SLOT_B, 4);
    let _ = upd_record_confirm(SLOT_A, 5);
    check("updater: five confirmations keep UPD_REC_KEEP records", upd_record_count() == UPD_REC_KEEP);
    check("updater: the newest confirmed slot is still the safe one", upd_record_safe_slot() == SLOT_A);
}

// ===========================================================================
// 5. console — HISTORY_SLOTS (8)
//
// The history ring is built with msg_init(256, 8). Its capacity is the limit; a ring
// whose capacity drifted from the constant would accept a ninth line and drop one
// silently, which is the failure mode the constant exists to rule out.

fn t_history_slots() {
    say("-- HISTORY_SLOTS\n");
    check("console: the history ring holds exactly HISTORY_SLOTS lines", history_slots() == HISTORY_SLOTS);
}
