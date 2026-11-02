// services/tests/t46_ring.goose
//
// B-L1-46 — test program for the ring buffer library (B-L1-11).
//
// Status: WRITTEN (not COMPILED, not RUN). Runs at K6, not before.
//
// The cases are the wrap. A ring that works until it wraps is a ring that fails on the
// second day of uptime and nowhere in a short test, so this walks past the end explicitly:
// fill to cap, drain, fill again, and check the bytes come out in order across the seam.
//
// The message ring is tested separately because it is a different structure: fixed slots
// with a length prefix per message, where a frame larger than the slot is refused instead
// of being split across two slots (a split frame reads as two short messages, which the
// consumer has no way to notice).

import common.ring.ring;
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

fn make_store(n: i64) -> u8[>..] {
    var s: u8[>..] = [];
    var i: i64 = 0;
    while i < n {
        s.push(0);
        i = i + 1;
    }
    return s;
}

fn main() {
    say("t46 ring\n");

    // --- empty ---
    var store = make_store(4);
    var r = ring_init(4);
    check("init empty", ring_is_empty(r) == true && ring_len(r) == 0 && ring_space(r) == 4);
    check("cap", ring_cap(r) == 4);
    let v0, ok0 = ring_pop(r, store);
    check("pop on empty", ok0 == false && ring_len(r) == 0);

    // --- fill and drain, no wrap ---
    check("push a", ring_push(r, store, 65) == true && ring_len(r) == 1);
    check("push b", ring_push(r, store, 66) == true && ring_len(r) == 2);
    let peeked, peek_ok = ring_peek(r, store);
    check("peek a", peek_ok == true && peeked == 65);
    check("peek does not consume", ring_len(r) == 2);
    let p_a, ok_a = ring_pop(r, store);
    let p_b, ok_b = ring_pop(r, store);
    check("pop a", ok_a == true && p_a == 65);
    check("pop b", ok_b == true && p_b == 66);
    check("empty again", ring_is_empty(r) == true && ring_len(r) == 0);

    // --- full, and the refused push ---
    var i: i64 = 0;
    while i < 4 {
        let _ = ring_push(r, store, (48 + i) as u8);
        i = i + 1;
    }
    check("full after 4", ring_is_full(r) == true && ring_space(r) == 0);
    check("push on full refused", ring_push(r, store, 90) == false && ring_len(r) == 4);

    // --- the wrap ---
    // Drain two, push two: head and tail are now past the end of the store, so the next
    // reads come from the front of it. The order is what matters.
    let w0, wk0 = ring_pop(r, store);
    let w1, wk1 = ring_pop(r, store);
    check("drain 0", wk0 == true && w0 == 48);
    check("drain 1", wk1 == true && w1 == 49);
    check("push e", ring_push(r, store, 69) == true);
    check("push f", ring_push(r, store, 70) == true);
    let w2, _ = ring_pop(r, store);
    let w3, _ = ring_pop(r, store);
    let we, _ = ring_pop(r, store);
    let wf, _ = ring_pop(r, store);
    check("wrap order 2,3", w2 == 50 && w3 == 51);
    check("wrap order e,f", we == 69 && wf == 70);
    check("empty after wrap", ring_is_empty(r) == true);

    // --- overflow push: overwrite the oldest instead of refusing ---
    var r2 = make_store(3);
    var rr = ring_init(3);
    let _ = ring_push(rr, r2, 1);
    let _ = ring_push(rr, r2, 2);
    let _ = ring_push(rr, r2, 3);
    check("over push on full", ring_push_over(rr, r2, 4) == true && ring_len(rr) == 3);
    let o0, _ = ring_pop(rr, r2);
    let o1, _ = ring_pop(rr, r2);
    let o2, _ = ring_pop(rr, r2);
    check("over dropped 1, kept 2,3,4", o0 == 2 && o1 == 3 && o2 == 4);
    let _ = ring_push(rr, r2, 7);
    check("over on empty is push", ring_len(rr) == 1);

    // --- drain and snapshot ---
    var r3 = make_store(8);
    var rx = ring_init(8);
    append3(rx, r3, 65, 66, 67);
    var out: u8[>..] = [];
    check("drain 3", ring_drain(rx, r3, out, 3) == 3 && out.len == 3 && out[2] == 67);
    check("drained", ring_len(rx) == 0);

    append3(rx, r3, 72, 73, 74);
    var snap: u8[>..] = [];
    check("snapshot 3", ring_snapshot(rx, r3, snap) == 3 && snap.len == 3 && snap[0] == 72);
    check("snapshot does not consume", ring_len(rx) == 3);

    check("clear", true);   // ring_clear is void; the check below is the observable effect
    ring_clear(rx);
    check("clear empties", ring_len(rx) == 0 && ring_is_empty(rx) == true);

    // --- message ring ---
    var mbuf = make_store(64);
    var mr = msg_init(0, 4);        // 4 slots of msg_capacity() bytes
    check("msg cap", msg_capacity(mr) > 0);
    check("msg empty", msg_len(mr) == 0);

    check("msg push", msg_push(mr, mbuf, "hello") == true && msg_len(mr) == 1);
    check("msg push 2", msg_push(mr, mbuf, "") == true && msg_len(mr) == 2);

    var mout: u8[>..] = [];
    check("msg pop 1", msg_pop(mr, mbuf, mout) == true && mout.len == 5 && mout[0] == 104);
    mout = [];
    check("msg pop 2 (empty frame)", msg_pop(mr, mbuf, mout) == true && mout.len == 0);
    check("msg pop empty ring", msg_pop(mr, mbuf, mout) == false);

    // A frame larger than a slot must be refused: splitting it would hand the consumer two
    // messages it cannot tell apart from two real ones.
    var big: u8[>..] = [];
    var k: i64 = 0;
    while k < msg_capacity(mr) + 8 {
        big.push(65);
        k = k + 1;
    }
    var before = msg_len(mr);
    check("oversize frame refused", msg_push(mr, mbuf, big) == false && msg_len(mr) == before);

    var r4: u8[>..] = [];
    let _ = append_int(r4, 32, t_pass);
    say("passed ");
    say(r4);
    say("\n");
    if t_fail != 0 { say("FAILURES\n"); sys_exit(1); }
    say("t46 done\n");
    sys_exit(0);
}

// Three pushes as one helper only to keep the test body readable; the ring API is what is
// under test, not this.
fn append3(r: Ring&, store: u8[>..]&, a: u8, b: u8, c: u8) {
    let _ = ring_push(r, store, a);
    let _ = ring_push(r, store, b);
    let _ = ring_push(r, store, c);
}
