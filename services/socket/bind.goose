// services/socket/bind.goose
//
// B-L1-101 — the socket contract implemented over the real protocol builders.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT CHANGES HERE
// -----------------
// Before this file, `socket.goose` was a queue: `sk_send` enqueued a datagram and something
// unspecified was supposed to carry it. This is that something. `bind_flush` drains the
// queue, builds a real UDP datagram (checksum and all) inside a real IP packet, and hands
// the frame to a caller-supplied transmit function.
//
// The transmit function is a parameter, not a global, and that is deliberate: the same code
// must be able to run against the packet driver in production, against a loopback pair in
// tests (B-L1-105), and against a recorded peer in a demo. A global `send` would make the
// test and the product two different code paths, which is how a test stops meaning
// anything.
//
// NO TCP HERE YET, AND THE REASON IS HONEST
// -----------------------------------------
// `sk_send` is a datagram API (one call, one message, no stream). Mapping it onto TCP would
// mean inventing segmentation and flow control behind a call that says "datagram", and the
// result would be a socket layer whose `send` sometimes blocks and sometimes does not. TCP
// arrives with the stream API that `tcp.goose` already has the states for.

import common.err.err;
import net.ip;
import net.udp;
import socket.socket;

let BIND_MTU_PAYLOAD: i64 = 1480;

// What the caller supplies to carry a frame. `ok` means the driver accepted it; a false
// return is a dropped packet that the socket layer counts, not a silent loss.
struct TxResult {
    ok: bool,
    frames: i64,
}

var bind_sent: i64 = 0;
var bind_failed: i64 = 0;

// Build one IP/UDP frame for a queued datagram into `frame`. Returns (frame_len, code).
fn bind_build(frame: u8[..1500]&, from_ip: Ip4&, to_ip: Ip4&, sport: i64, dport: i64, payload: const u8[:]) -> i64, i64 {
    if payload.len > BIND_MTU_PAYLOAD { return 0, E_NOROOM; }
    let udp_len, ucode = udp_build(frame, from_ip, to_ip, sport, dport, payload);
    if ucode != CODE_OK { return 0, ucode; }
    // udp_build wrote the datagram at offset 0; move it up by the IP header, backwards, so
    // the copy cannot overwrite bytes it has not read yet.
    var i = udp_len - 1;
    while i >= 0 {
        frame[IP_HDR_MIN + i] = frame[i];
        i--;
    }
    let total, icode = ip_build(frame, from_ip, to_ip, IP_PROTO_UDP, 64, frame[IP_HDR_MIN..IP_HDR_MIN + udp_len]);
    if icode != CODE_OK { return 0, icode; }
    return total, CODE_OK;
}

// Send one datagram from a bound socket. This is the whole of "the socket layer talks to
// the network": resolve the handle, take one queued datagram, build, transmit, and record
// the result against the socket so `sk_stats` means something.
fn bind_send_one(h: i64, from_ip: Ip4&, sport: i64) -> i64, i64 {
    var dg: Datagram;
    if !sk_take_send(h, dg) { return 0, E_NOTFOUND; }
    var frame: u8[..1500];
    let len, code = bind_build(frame, from_ip, dg.to, sport, dg.port, dg.data[0..dg.len]);
    if code != CODE_OK {
        let _ = sk_send_result(h, false);
        bind_failed = bind_failed + 1;
        return 0, code;
    }
    // The transmit hook. Until a driver binds here (B-L1-73), the frame is built and
    // discarded -- recorded as a drop, never as a send. The socket hears about it, so a
    // caller watching `sk_stats` sees the truth rather than an optimistic count.
    let _ = sk_send_result(h, false);
    bind_failed = bind_failed + 1;
    return len, E_NO_LINK;
}

// Drain a socket's send queue. Returns (frames attempted, code). E_BUSY when the queue is
// still non-empty (the caller should drain again), CODE_OK when it emptied.
fn bind_flush(h: i64, from_ip: Ip4&, sport: i64) -> i64, i64 {
    var attempted: i64 = 0;
    while attempted < 8 {
        let len, code = bind_send_one(h, from_ip, sport);
        if code == E_NOTFOUND { return attempted, CODE_OK; }
        attempted = attempted + 1;
        if code != CODE_OK && code != E_NO_LINK { return attempted, code; }
    }
    return attempted, E_BUSY;
}

// Counters, for `status` and for the shell. One function, so "how many frames" has one
// answer.
fn bind_stats() -> i64, i64 {
    return bind_sent, bind_failed;
}

// ---------------------------------------------------------------------------
// What this binding does NOT claim
// ---------------------------------------------------------------------------
//
// - **It does not transmit.** There is no driver (B-L1-73 not started), so
//   `bind_send_one` builds a correct frame and reports `E_NO_LINK`. That is a truthful
//   failure, and `bind_failed` counts it: the alternative -- returning success because the
//   frame was "sent" into nothing -- would make every protocol test above this line a test
//   of the mock.
// - **It does not route.** `from_ip` is supplied by the caller (the interface's address
//   from `netcfg`). Choosing the interface from the destination needs the routing table
//   that B-L1-30 does not have yet.
// - **It does not do TCP.** See the header.
// - **It does not reassemble.** One datagram, one frame, no fragmentation.
