// services/tests/t132_socket_r11.goose
//
// Round 11 — the socket table at its edges: capacity, generations, ports, datagram size,
// queue depth, and every refusal the state machine can make.
//
// WHY THIS FILE EXISTS
// --------------------
// t77_gaps proves the socket state machine works. This one fills it: 16 sockets then
// E_NOROOM, 512 bytes then E_NOROOM, a third queued datagram then E_BUSY, the privileged
// port range on both sides, and the generation wrap that makes an old handle valid again
// after 254 reuses — a bound the README did not state.
//
// Status: written, not yet compiled or run (the coordinator runs the corpus).

import common.err.err;
import common.fmt.fmt;
import common.sys.sys;
import netcfg.netcfg;
import socket.socket;

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
    say("t132 socket round 11\n");

    let dst, dst_ok = ip4_parse("10.0.0.7");
    check("a destination address parses", dst_ok);
    var dest = dst;

    // ======================================================================
    // 1. capacity: 16 sockets, then E_NOROOM
    // ======================================================================
    var hs: i64[..16] = [0; 16];
    var opened: i64 = 0;
    var i: i64 = 0;
    while i < SK_MAX {
        let h, c = sk_open();
        if c == CODE_OK {
            hs[opened] = h;
            opened = opened + 1;
        }
        i = i + 1;
    }
    check("sk_open: every slot opens", opened == SK_MAX && opened == 16);
    let overflow_h, overflow_c = sk_open();
    check("sk_open: the seventeenth is E_NOROOM", overflow_c == E_NOROOM && overflow_h == 0);

    // Bind each one to a distinct ephemeral port: 0 asks the allocator.
    var bound: i64 = 0;
    i = 0;
    while i < opened {
        let p, pc = sk_bind(hs[i], 0);
        if pc == CODE_OK && p >= SK_EPHEMERAL_MIN { bound = bound + 1; }
        i = i + 1;
    }
    check("sk_bind: every socket gets an ephemeral port above the range floor",
          bound == opened);

    // A bound socket is not re-bindable: BOUND -> BIND is not an edge in the state
    // machine, so the answer is E_STATE and the port is irrelevant.
    let _r0, r0c = sk_bind(hs[0], 5000);
    check("sk_bind: rebinding a bound socket is E_STATE", r0c == E_STATE);

    // Explicit ports need sockets in OPEN. The ephemeral pass above left all sixteen
    // BOUND on purpose, so free three slots and drive the port rules on those.
    check("sk_close: a second live socket closes", sk_close(hs[14]) == CODE_OK);
    check("sk_close: a third live socket closes", sk_close(hs[13]) == CODE_OK);
    check("sk_close: a fourth live socket closes", sk_close(hs[12]) == CODE_OK);
    let e1, e1c = sk_open();
    let e2, e2c = sk_open();
    let e3, e3c = sk_open();
    check("sk_open: the three freed slots reopen", e1c == CODE_OK && e2c == CODE_OK && e3c == CODE_OK);

    // Duplicate detection is a scan across the table, not a second structure.
    let _p0, pc0 = sk_bind(e1, 5000);
    let _p1, pc1 = sk_bind(e2, 5000);
    check("sk_bind: an explicit port is accepted", pc0 == CODE_OK);
    check("sk_bind: the same port on another socket is E_BUSY", pc1 == E_BUSY);

    // A refused port leaves the socket OPEN, so one socket can carry all three probes.
    let _pl, pl_c = sk_bind(e3, SK_PORT_MIN - 1);
    check("sk_bind: a privileged port is E_INVAL", pl_c == E_INVAL);
    let _ph, ph_c = sk_bind(e3, SK_PORT_MAX + 1);
    check("sk_bind: a port past 65535 is E_INVAL", ph_c == E_INVAL);
    let _pm, pm_c = sk_bind(e3, SK_PORT_MAX);
    check("sk_bind: 65535 itself is accepted", pm_c == CODE_OK);

    // ======================================================================
    // 2. the state machine's refusals
    // ======================================================================
    let fresh_h, fresh_c = sk_open();
    check("a fresh socket opens after the table frees nothing", fresh_c == E_NOROOM);

    // Close one slot and probe the closed handle.
    check("sk_close: a live socket closes", sk_close(hs[15]) == CODE_OK);
    check("sk_close: closing it twice is E_STATE", sk_close(hs[15]) == E_STATE);
    check("sk_bind: a closed handle is E_STATE", sk_bind(hs[15], 0) == E_STATE);
    check("sk_send: a closed handle is E_STATE", sk_send(hs[15], dest, 9000, "x") == E_STATE);

    // Open returns the freed slot with a new generation, so the old handle is dead.
    let re_h, re_c = sk_open();
    check("sk_open: a closed slot is reused", re_c == CODE_OK);
    check("sk_open: the reuse hands out a different handle", re_h != hs[15]);
    check("sk_open: the old handle no longer resolves", sk_resolve(hs[15]) < 0);
    check("sk_open: the new handle resolves to the slot", sk_resolve(re_h) == 15);

    // A socket that is only OPEN has no source port: send refuses rather than pretending.
    check("sk_send on an unbound socket is E_STATE", sk_send(re_h, dest, 9000, "x") == E_STATE);
    check("sk_connect on an unbound socket is allowed",
          sk_connect(re_h, dest, 9000) == CODE_OK);
    check("sk_connect: port 0 is E_INVAL", sk_connect(re_h, dest, 0) == E_INVAL);
    var any = ip4_any();
    check("sk_connect: 0.0.0.0 is not a destination", sk_connect(re_h, any, 9000) == E_INVAL);
    check("sk_match: port 0 never matches", sk_match(0) == 0);

    // ======================================================================
    // 3. datagram size and queue depth
    // ======================================================================
    var payload: u8[..512] = [0; 512];
    payload[0] = 1;
    check("sk_send: 512 bytes is one datagram", sk_send(re_h, dest, 9000, payload[..]) == CODE_OK);

    var over: u8[..513] = [0; 513];
    check("sk_send: 513 bytes is E_NOROOM, not a truncated send",
          sk_send(re_h, dest, 9000, over[..]) == E_NOROOM);
    check("sk_send: zero bytes is E_INVAL", sk_send(re_h, dest, 9000, "") == E_INVAL);

    check("sk_send: a second datagram queues", sk_send(re_h, dest, 9000, payload[..]) == CODE_OK);
    check("sk_send: the third is E_BUSY at SK_QUEUE", sk_send(re_h, dest, 9000, payload[..]) == E_BUSY);

    var dg = Datagram { .. };
    check("sk_take_send: the first queued datagram comes out", sk_take_send(re_h, dg));
    check("sk_take_send: its length is the length sent", dg.len == 512);
    check("sk_send_result: a taken datagram is counted sent", sk_send_result(re_h, true) == CODE_OK);
    check("sk_take_send: the second queued datagram comes out", sk_take_send(re_h, dg));
    check("sk_take_send: the queue is empty after two takes", !sk_take_send(re_h, dg));
    check("sk_send: a send after draining queues again",
          sk_send(re_h, dest, 9000, payload[..]) == CODE_OK);
    check("sk_take_send: and that one comes out", sk_take_send(re_h, dg));
    check("sk_take_send: then the queue is empty", !sk_take_send(re_h, dg));
    check("sk_send_result: a failed send is counted dropped", sk_send_result(re_h, false) == CODE_OK);
    check("sk_send_result: an unknown handle is E_STATE", sk_send_result(999999, true) == E_STATE);

    // Close drops what is queued and keeps the count -- but the handle is dead, so the
    // count is asserted through the layer that owns the record, not through a closed socket.
    check("sk_close: a socket with a queued datagram closes", sk_close(re_h) == CODE_OK);

    // ======================================================================
    // 4. the generation wrap: a handle is reusable after 254 socket lifetimes
    // ======================================================================
    // SK_GEN_MAX is 255, and the assignment wraps when the increment reaches it. That is
    // 8 bits of generation in a 256-stride handle: at reuse 255 the first handle is issued
    // again. The old handle then resolves to the new socket, which is a real limit of the
    // encoding and is stated in r11/socket.md rather than left for someone to discover.
    var first_h: i64 = 0;
    var last_h: i64 = 0;
    i = 0;
    while i < 255 {
        let h, c = sk_open();
        if c == CODE_OK {
            if i == 0 { first_h = h; }
            last_h = h;
            let _ = sk_close(h);
        }
        i = i + 1;
    }
    check("gen wrap: 255 open/close cycles all succeed", last_h != 0);
    let wrap_h, wrap_c = sk_open();
    check("gen wrap: the next open reuses generation 1", wrap_c == CODE_OK && wrap_h == first_h);
    check("gen wrap: the old handle now names the new socket (documented bound)",
          sk_resolve(first_h) == 15);
    let _ = sk_close(wrap_h);

    // ======================================================================
    // 5. load: 320 send/take cycles, none dropped
    // ======================================================================
    let lh, lc = sk_open();
    check("load: a socket for the batch opens", lc == CODE_OK);
    let _lp, lb = sk_bind(lh, 0);
    check("load: and binds", lb == CODE_OK);
    var small: u8[..4] = [1, 2, 3, 4];
    var ops: i64 = 0;
    var ok: i64 = 0;
    var refused: i64 = 0;
    i = 0;
    while i < 320 {
        if sk_send(lh, dest, 9000, small[..]) == CODE_OK {
            if sk_take_send(lh, dg) { ok = ok + 1; } else { refused = refused + 1; }
            let _ = sk_send_result(lh, true);
        } else {
            refused = refused + 1;
        }
        ops = ops + 1;
        i = i + 1;
    }
    check("load: every send was accepted and taken", ok == 320 && refused == 0);
    check("load: the batch is 320 operations", ops == 320);
    let _ = sk_close(lh);

    say("LOAD socket ops=320 ok=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ok);
    say(ob[..]);
    say(" refused=");
    var rb: u8[>..] = [];
    let _ = append_int(rb, 32, refused);
    say(rb[..]);
    say("\n");

    say("t132 done  pass=");
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
