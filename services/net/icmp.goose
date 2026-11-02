// services/net/icmp.goose
//
// B-L1-97 — ICMP echo: ping out, ping answer.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT IS IMPLEMENTED IS ECHO AND ONLY ECHO
// -----------------------------------------
// Type 8 (request) and type 0 (reply). Destination-unreachable, time-exceeded and redirects
// are parsed only far enough to be *reported* -- `icmp_classify` names them and nothing
// else. A stack that reacts to a redirect it has not authenticated is a stack an attacker
// moves the default route of.
//
// THE PAYLOAD IS COPIED BACK VERBATIM
// -----------------------------------
// An echo reply must return the exact bytes it was sent, including any pattern the sender
// chose to detect corruption. So this file copies bytes and never "helpfully" regenerates
// them.

import common.err.err;
import net.ip;

let ICMP_ECHO_REPLY: i64 = 0;
let ICMP_DEST_UNREACH: i64 = 3;
let ICMP_ECHO_REQUEST: i64 = 8;
let ICMP_TIME_EXCEEDED: i64 = 11;
let ICMP_HDR: i64 = 8;              // type, code, checksum, id, seq

struct IcmpView {
    kind: i64,
    code: i64,
    id: i64,
    seq: i64,
    payload_off: i64,
    payload_len: i64,
}

fn icmp_sum16(b: u8[..1500]&, len: i64) -> i64 {
    var sum: i64 = 0;
    var i: i64 = 0;
    while i + 1 < len {
        sum = sum + (((b[i] as i64) << 8) | (b[i + 1] as i64));
        i = i + 2;
    }
    if (len % 2) != 0 { sum = sum + ((b[len - 1] as i64) << 8); }
    while sum > 0xffff { sum = (sum & 0xffff) + (sum >> 16); }
    return (~sum) & 0xffff;
}

fn icmp_build_echo(out: u8[..1500]&, kind: i64, id: i64, seq: i64, payload: const u8[:]) -> i64, i64 {
    let len = ICMP_HDR + payload.len;
    if len > 1472 { return 0, E_NOROOM; }         // 1500 - 20 IP - 8 ICMP
    out[0] = (kind & 0xff) as u8;
    out[1] = 0;                                    // code
    out[2] = 0; out[3] = 0;                        // checksum placeholder
    out[4] = ((id >> 8) & 0xff) as u8;
    out[5] = (id & 0xff) as u8;
    out[6] = ((seq >> 8) & 0xff) as u8;
    out[7] = (seq & 0xff) as u8;
    var i: i64 = 0;
    while i < payload.len { out[ICMP_HDR + i] = payload[i]; i = i + 1; }
    let sum = icmp_sum16(out, len);
    out[2] = ((sum >> 8) & 0xff) as u8;
    out[3] = (sum & 0xff) as u8;
    return len, CODE_OK;
}

fn icmp_parse(msg: u8[..1500]&, len: i64) -> IcmpView, i64 {
    var none = IcmpView { kind: -1, code: 0, id: 0, seq: 0, payload_off: 0, payload_len: 0 };
    if len < ICMP_HDR { return none, E_CORRUPT; }
    let stored = (((msg[2] as i64) << 8) | (msg[3] as i64));
    msg[2] = 0; msg[3] = 0;
    let want = icmp_sum16(msg, len);
    msg[2] = ((stored >> 8) & 0xff) as u8;
    msg[3] = (stored & 0xff) as u8;
    if stored != want { return none, E_CORRUPT; }
    return IcmpView {
        kind: msg[0] as i64,
        code: msg[1] as i64,
        id: (((msg[4] as i64) << 8) | (msg[5] as i64)),
        seq: (((msg[6] as i64) << 8) | (msg[7] as i64)),
        payload_off: ICMP_HDR,
        payload_len: len - ICMP_HDR,
    }, CODE_OK;
}

// Is this a reply to OUR request? Both id and seq, not just the type: a reply with the right
// type and the wrong sequence is another ping's answer, and counting it as ours makes loss
// statistics fiction.
fn icmp_is_reply_to(v: IcmpView&, id: i64, seq: i64) -> bool {
    return v.kind == ICMP_ECHO_REPLY && v.id == id && v.seq == seq;
}

fn icmp_classify(v: IcmpView&) -> const u8[:] {
    if v.kind == ICMP_ECHO_REQUEST { return "echo-request"; }
    if v.kind == ICMP_ECHO_REPLY { return "echo-reply"; }
    if v.kind == ICMP_DEST_UNREACH { return "dest-unreachable"; }
    if v.kind == ICMP_TIME_EXCEEDED { return "time-exceeded"; }
    return "other";
}

// Does the returned payload match what was sent? Byte for byte, length first.
fn icmp_payload_matches(msg: u8[..1500]&, v: IcmpView&, sent: const u8[:]) -> bool {
    if v.payload_len != sent.len { return false; }
    var i: i64 = 0;
    while i < sent.len {
        if msg[v.payload_off + i] != sent[i] { return false; }
        i = i + 1;
    }
    return true;
}
