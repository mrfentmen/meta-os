// services/net/tcp.goose
//
// B-L1-99/100 — TCP: connection state machine, header build/parse, retransmit timers.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT IS HERE AND WHAT IS NOT
// ----------------------------
// Here: the header, the flag set, sequence arithmetic that survives wrapping, the state
// machine's transitions, and the retransmit decision with exponential backoff and a cap.
//
// Not here: the send/receive buffers, congestion control (window is echoed, not adapted),
// and timestamps/SACK. The state machine is not decoration for those: every one of them is
// a decision made *inside* a state, and the states are the part worth getting right first.
//
// SEQUENCE ARITHMETIC IS THE BUG CLASS
// ------------------------------------
// Sequence numbers wrap at 2^32. `a < b` on raw numbers is wrong across the wrap, and the
// wrongness appears once every 4 GB -- which is to say, in production and never in a test
// that does not look for it. `seq_lt`/`seq_le` compare in modulo space, and `t67` checks
// them across the wrap on purpose.

import common.err.err;

let TCP_HDR_MIN: i64 = 20;
let SEQ_MOD: i64 = 4294967296;          // 2^32

let FIN: i64 = 0x01;
let SYN: i64 = 0x02;
let RST: i64 = 0x04;
let PSH: i64 = 0x08;
let ACK: i64 = 0x10;

let TS_CLOSED: i64 = 0;
let TS_LISTEN: i64 = 1;
let TS_SYN_SENT: i64 = 2;
let TS_SYN_RECEIVED: i64 = 3;
let TS_ESTABLISHED: i64 = 4;
let TS_FIN_WAIT_1: i64 = 5;
let TS_FIN_WAIT_2: i64 = 6;
let TS_CLOSE_WAIT: i64 = 7;
let TS_LAST_ACK: i64 = 8;
let TS_CLOSING: i64 = 9;
let TS_TIME_WAIT: i64 = 10;

let RTO_MIN_MS: i64 = 200;
let RTO_MAX_MS: i64 = 30000;            // capped: an unbounded backoff is a dead socket
let RTO_TRIES: i64 = 8;                 // then the connection is declared failed

struct TcpHeader {
    src_port: i64,
    dst_port: i64,
    seq: i64,
    ack: i64,
    flags: i64,
    window: i64,
    payload_off: i64,
    payload_len: i64,
}

// Modulo-space comparisons. The difference is taken in signed 32-bit space: a difference in
// (-2^31, 2^31) is unambiguous, which is exactly the window TCP allows.
fn seq_diff(a: i64, b: i64) -> i64 {
    var d = (a - b) % SEQ_MOD;
    if d < 0 { d = d + SEQ_MOD; }
    if d >= SEQ_MOD / 2 { d = d - SEQ_MOD; }
    return d;
}

fn seq_lt(a: i64, b: i64) -> bool {
    return seq_diff(a, b) < 0;
}

fn seq_le(a: i64, b: i64) -> bool {
    return seq_diff(a, b) <= 0;
}

fn seq_advance(seq: i64, n: i64) -> i64 {
    var s = (seq + n) % SEQ_MOD;
    if s < 0 { s = s + SEQ_MOD; }
    return s;
}

fn seq_before_window(seq: i64, base: i64, window: i64) -> bool {
    if window < 0 { return false; }
    return seq_le(seq, seq_advance(base, window));
}

// ---------------------------------------------------------------------------
// Header
// ---------------------------------------------------------------------------

fn tcp_sum16(buf: u8[..1500]&, off: i64, len: i64) -> i64 {
    var sum: i64 = 0;
    var i = off;
    while i + 1 < off + len {
        sum = sum + (((buf[i] as i64) << 8) | (buf[i + 1] as i64));
        i = i + 2;
    }
    if (len % 2) != 0 { sum = sum + ((buf[off + len - 1] as i64) << 8); }
    while sum > 0xffff { sum = (sum & 0xffff) + (sum >> 16); }
    return sum;
}

fn tcp_build(out: u8[..1500]&, sport: i64, dport: i64, seq: i64, ack: i64, flags: i64, window: i64, payload: const u8[:], src_ip: Ipv4, dst_ip: Ipv4) -> i64, i64 {
    let total = TCP_HDR_MIN + payload.len;
    if total > 1460 + TCP_HDR_MIN { return 0, E_NOROOM; }
    var i: i64 = 0;
    while i < TCP_HDR_MIN { out[i] = 0; i++; }
    out[0] = ((sport >> 8) & 0xff) as u8; out[1] = (sport & 0xff) as u8;
    out[2] = ((dport >> 8) & 0xff) as u8; out[3] = (dport & 0xff) as u8;
    out[4] = ((seq >> 24) & 0xff) as u8; out[5] = ((seq >> 16) & 0xff) as u8;
    out[6] = ((seq >> 8) & 0xff) as u8; out[7] = (seq & 0xff) as u8;
    out[8] = ((ack >> 24) & 0xff) as u8; out[9] = ((ack >> 16) & 0xff) as u8;
    out[10] = ((ack >> 8) & 0xff) as u8; out[11] = (ack & 0xff) as u8;
    out[12] = 0x50;                                     // data offset 5 words, no options
    out[13] = (flags & 0xff) as u8;
    out[14] = ((window >> 8) & 0xff) as u8; out[15] = (window & 0xff) as u8;
    out[16] = 0; out[17] = 0;                           // checksum placeholder
    out[18] = 0; out[19] = 0;                           // urgent pointer
    i = 0;
    while i < payload.len { out[TCP_HDR_MIN + i] = payload[i]; i++; }

    var sum: i64 = 0;
    sum = sum + ((src_ip.a << 8) | src_ip.b);
    sum = sum + ((src_ip.c << 8) | src_ip.d);
    sum = sum + ((dst_ip.a << 8) | dst_ip.b);
    sum = sum + ((dst_ip.c << 8) | dst_ip.d);
    sum = sum + IP_PROTO_TCP;
    sum = sum + total;
    sum = sum + tcp_sum16(out, 0, total);
    while sum > 0xffff { sum = (sum & 0xffff) + (sum >> 16); }
    let csum = (~sum) & 0xffff;
    out[16] = ((csum >> 8) & 0xff) as u8;
    out[17] = (csum & 0xff) as u8;
    return total, CODE_OK;
}

fn tcp_parse(seg: u8[..1500]&, len: i64) -> TcpHeader, i64 {
    var none = TcpHeader { src_port: 0, dst_port: 0, seq: 0, ack: 0, flags: 0, window: 0, payload_off: 0, payload_len: 0 };
    if len < TCP_HDR_MIN { return none, E_CORRUPT; }
    let words = (seg[12] as i64) >> 4;
    if words < 5 { return none, E_CORRUPT; }
    let hdr = words * 4;
    if hdr > len { return none, E_CORRUPT; }
    return TcpHeader {
        src_port: (((seg[0] as i64) << 8) | (seg[1] as i64)),
        dst_port: (((seg[2] as i64) << 8) | (seg[3] as i64)),
        seq: (((seg[4] as i64) << 24) | ((seg[5] as i64) << 16) | ((seg[6] as i64) << 8) | (seg[7] as i64)),
        ack: (((seg[8] as i64) << 24) | ((seg[9] as i64) << 16) | ((seg[10] as i64) << 8) | (seg[11] as i64)),
        flags: seg[13] as i64,
        window: (((seg[14] as i64) << 8) | (seg[15] as i64)),
        payload_off: hdr,
        payload_len: len - hdr,
    }, CODE_OK;
}

// ---------------------------------------------------------------------------
// State machine
// ---------------------------------------------------------------------------

fn tcp_state_name(s: i64) -> const u8[:] {
    if s == TS_CLOSED { return "CLOSED"; }
    if s == TS_LISTEN { return "LISTEN"; }
    if s == TS_SYN_SENT { return "SYN_SENT"; }
    if s == TS_SYN_RECEIVED { return "SYN_RECEIVED"; }
    if s == TS_ESTABLISHED { return "ESTABLISHED"; }
    if s == TS_FIN_WAIT_1 { return "FIN_WAIT_1"; }
    if s == TS_FIN_WAIT_2 { return "FIN_WAIT_2"; }
    if s == TS_CLOSE_WAIT { return "CLOSE_WAIT"; }
    if s == TS_LAST_ACK { return "LAST_ACK"; }
    if s == TS_CLOSING { return "CLOSING"; }
    if s == TS_TIME_WAIT { return "TIME_WAIT"; }
    return "UNKNOWN";
}

// The transition table, as a function. `flags` may set several bits at once (SYN|ACK is one
// segment, not two), so the order of the tests is part of the contract and is checked by
// the test program.
//
// Active open: CLOSED -SYN-> SYN_SENT. Passive: CLOSED -listen-> LISTEN. Closing is the
// four-way handshake; TIME_WAIT is entered rather than skipped, because a socket that
// forgets a connection immediately will accept a late duplicate segment as a new one.
fn tcp_next(state: i64, flags: i64) -> i64 {
    let has_syn = (flags & SYN) != 0;
    let has_ack = (flags & ACK) != 0;
    let has_fin = (flags & FIN) != 0;
    let has_rst = (flags & RST) != 0;

    if has_rst { return TS_CLOSED; }

    if state == TS_CLOSED { return TS_CLOSED; }         // only an open() or listen() moves it
    if state == TS_LISTEN {
        if has_syn { return TS_SYN_RECEIVED; }
        return TS_LISTEN;
    }
    if state == TS_SYN_SENT {
        if has_syn && has_ack { return TS_ESTABLISHED; }
        if has_syn { return TS_SYN_RECEIVED; }          // simultaneous open
        return TS_SYN_SENT;
    }
    if state == TS_SYN_RECEIVED {
        if has_ack { return TS_ESTABLISHED; }
        return TS_SYN_RECEIVED;
    }
    if state == TS_ESTABLISHED {
        if has_fin { return TS_CLOSE_WAIT; }
        return TS_ESTABLISHED;
    }
    if state == TS_FIN_WAIT_1 {
        if has_fin && has_ack { return TS_TIME_WAIT; }  // both sides closed at once
        if has_fin { return TS_CLOSING; }
        if has_ack { return TS_FIN_WAIT_2; }
        return TS_FIN_WAIT_1;
    }
    if state == TS_FIN_WAIT_2 {
        if has_fin { return TS_TIME_WAIT; }
        return TS_FIN_WAIT_2;
    }
    if state == TS_CLOSING {
        if has_ack { return TS_TIME_WAIT; }
        return TS_CLOSING;
    }
    if state == TS_CLOSE_WAIT {
        // Waiting for the application to close. Only an explicit local FIN moves it, which
        // this function expresses as the caller passing FIN.
        if has_fin { return TS_LAST_ACK; }
        return TS_CLOSE_WAIT;
    }
    if state == TS_LAST_ACK {
        if has_ack { return TS_CLOSED; }
        return TS_LAST_ACK;
    }
    if state == TS_TIME_WAIT {
        return TS_TIME_WAIT;                            // the caller's timer closes it
    }
    return TS_CLOSED;
}

// Local open and local close, the two transitions that are not driven by a segment.
fn tcp_open_active(state: i64) -> i64 {
    if state == TS_CLOSED { return TS_SYN_SENT; }
    return state;
}

fn tcp_open_passive(state: i64) -> i64 {
    if state == TS_CLOSED { return TS_LISTEN; }
    return state;
}

fn tcp_close_local(state: i64) -> i64 {
    if state == TS_ESTABLISHED { return TS_FIN_WAIT_1; }
    if state == TS_CLOSE_WAIT { return TS_LAST_ACK; }
    return state;
}

fn tcp_is_established(s: i64) -> bool {
    return s == TS_ESTABLISHED;
}

fn tcp_is_closed(s: i64) -> bool {
    return s == TS_CLOSED;
}

// ---------------------------------------------------------------------------
// Retransmit (B-L1-100)
// ---------------------------------------------------------------------------

struct TcpTimer {
    rto_ms: i64,
    tries: i64,
    last_sent_ms: i64,
    started: bool,
}

fn tcp_timer_init(now_ms: i64) -> TcpTimer {
    return TcpTimer { rto_ms: RTO_MIN_MS, tries: 0, last_sent_ms: now_ms, started: false };
}

fn tcp_timer_arm(t: TcpTimer&, now_ms: i64) {
    t.started = true;
    t.last_sent_ms = now_ms;
}

// Double on every expiry, capped. Unbounded doubling reaches a year in 25 retries; the cap
// is what turns "the peer is gone" into a failure a user can be told about.
fn tcp_timer_expire(t: TcpTimer&, now_ms: i64) -> bool {
    t.tries = t.tries + 1;
    t.rto_ms = t.rto_ms * 2;
    if t.rto_ms > RTO_MAX_MS { t.rto_ms = RTO_MAX_MS; }
    t.last_sent_ms = now_ms;
    if t.tries >= RTO_TRIES {
        t.started = false;
        return false;                                   // give up: the connection has failed
    }
    return true;                                        // retransmit
}

// On a valid ack, reset to the floor. A connection that keeps a backoff after the peer
// answered takes seconds to notice the next loss.
fn tcp_timer_ack(t: TcpTimer&, now_ms: i64) {
    t.rto_ms = RTO_MIN_MS;
    t.tries = 0;
    t.last_sent_ms = now_ms;
    t.started = false;
}

fn tcp_timer_due(t: TcpTimer&, now_ms: i64) -> bool {
    if !t.started { return false; }
    return now_ms - t.last_sent_ms >= t.rto_ms;
}

fn tcp_timer_given_up(t: TcpTimer&) -> bool {
    return !t.started && t.tries >= RTO_TRIES;
}
