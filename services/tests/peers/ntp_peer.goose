// services/tests/peers/ntp_peer.goose
//
// B-L1-103 — NTP test peer (the second peer in the pack; the clock is the surface that
// every other service's timeouts depend on, so it gets a peer of its own).
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT THIS IS
// ------------
// A 48-byte SNTPv4 server: it reads a mode-3 request and writes a mode-4 reply. It is
// deliberately a *peer*, not a clock: `now_ms` is passed in, so a test that wants a reply
// from a server 90 seconds fast says 90 seconds fast, and nothing has to be faked in the
// system clock.
//
// THE ARITHMETIC IS HERE, TWICE, ON PURPOSE
// -----------------------------------------
// Both the peer and the client need the same four-timestamp offset/delay computation. It
// lives here once as `ntp_offset_delay`, and the client imports it -- a second copy in the
// client would be a second place for the sign of the offset to be wrong. The formula
// follows RFC 5905 section 8:
//
//     offset = ((t2 - t1) + (t3 - t4)) / 2
//     delay  =  (t4 - t1) - (t3 - t2)
//
// TIME IS MILLISECONDS SINCE THE UNIX EPOCH ON THIS SIDE OF THE WIRE. The 1900 epoch and
// the 32.32 fixed point stay strictly inside ntp_ts_write / ntp_ts_read. Mixing the two
// epochs in calling code is how a clock ends up 1900 years off and nobody notices for a
// release.

import common.err.err;

let NTP_PKT: i64 = 48;
let NTP_MODE_CLIENT: i64 = 3;
let NTP_MODE_SERVER: i64 = 4;
let NTP_UNIX_TO_1900: i64 = 2208988800;      // seconds, unsigned in the wire format
let NTP_FRAC: i64 = 4294967296;              // 2^32

// (length, code). Mode 3, version 4, transmit timestamp set -- the rest zero, which is
// what a client with no prior samples legitimately sends.
fn ntp_build_request(out: u8[..48]&, transmit_ms: i64) -> i64, i64 {
    if transmit_ms < 0 { return 0, E_INVAL; }
    var i: i64 = 0;
    while i < NTP_PKT { out[i] = 0; i++; }
    out[0] = 0x23;                 // LI 0, VN 4, mode 3 (client)
    out[1] = 0;                    // stratum 0: unspecified, as a client should say
    out[2] = 6;                    // poll: 64 s, the RFC default
    out[3] = 0xEC;                 // precision: -20
    ntp_ts_write(out, 40, transmit_ms);
    return NTP_PKT, CODE_OK;
}

// Reply to `request`. Returns (length, code); E_INVAL when the request is short, or is not
// a version-3/4 client request. A peer that answered malformed input is a peer that hides
// a client that builds malformed input.
fn ntp_build_reply(request: const u8[:], out: u8[..48]&, now_ms: i64) -> i64, i64 {
    if request.len < NTP_PKT { return 0, E_INVAL; }
    if now_ms < 0 { return 0, E_INVAL; }
    let version = (request[0] >> 3) & 7;
    let mode = request[0] & 7;
    if mode != NTP_MODE_CLIENT { return 0, E_INVAL; }
    if version != 3 && version != 4 { return 0, E_INVAL; }

    var i: i64 = 0;
    while i < NTP_PKT { out[i] = 0; i++; }
    out[0] = 0x24;                 // LI 0, VN 4, mode 4 (server)
    out[1] = 2;                    // stratum 2: a secondary server
    out[2] = request[2];           // poll echoed
    out[3] = 0xEC;                 // precision -20
    // root delay (4-8) and root dispersion (8-12) stay zero: this peer has no upstream,
    // and inventing a dispersion would make a client's sanity check pass on fiction.
    out[12] = 'L'; out[13] = 'O'; out[14] = 'C'; out[15] = 'L';

    // originate (24-32) = the client's transmit, echoed byte for byte. The client's whole
    // spoof check rests on this field, so the peer copies rather than recomputes.
    var k: i64 = 0;
    while k < 8 { out[24 + k] = request[40 + k]; k++; }

    // receive (32-40) and transmit (40-48). A real server's two stamps differ by its own
    // processing time; here they are equal, and the client's delay figure is therefore a
    // lower bound -- fine for a peer, and stated in the README.
    ntp_ts_write(out, 32, now_ms);
    ntp_ts_write(out, 40, now_ms);
    return NTP_PKT, CODE_OK;
}

// Unix milliseconds into a 32.32 NTP timestamp at `at`.
fn ntp_ts_write(out: u8[..48]&, at: i64, unix_ms: i64) {
    let secs = (unix_ms / 1000) + NTP_UNIX_TO_1900;
    let rem_ms = unix_ms - (unix_ms / 1000) * 1000;
    let frac = (rem_ms * NTP_FRAC) / 1000;
    ntp_put32(out, at, secs);
    ntp_put32(out, at + 4, frac);
}

fn ntp_put32(out: u8[..48]&, at: i64, v: i64) {
    out[at] = ((v >> 24) & 0xFF) as u8;
    out[at + 1] = ((v >> 16) & 0xFF) as u8;
    out[at + 2] = ((v >> 8) & 0xFF) as u8;
    out[at + 3] = (v & 0xFF) as u8;
}

// 32.32 NTP timestamp at `at` back to Unix milliseconds. A zero field is read as 0, not as
// 1900 -- several servers leave the transmit field of an unsynchronised reply zero, and a
// client that took that literally would compute an offset of minus a century.
fn ntp_ts_read(pkt: const u8[:], at: i64) -> i64 {
    if pkt.len < at + 8 { return 0; }
    let secs = ntp_get32(pkt, at);
    let frac = ntp_get32(pkt, at + 4);
    if secs == 0 && frac == 0 { return 0; }
    let unix_s = secs - NTP_UNIX_TO_1900;
    let ms = (frac * 1000) / NTP_FRAC;
    return (unix_s * 1000) + ms;
}

fn ntp_get32(pkt: const u8[:], at: i64) -> i64 {
    return (pkt[at] as i64 * 16777216) + (pkt[at + 1] as i64 * 65536)
         + (pkt[at + 2] as i64 * 256) + (pkt[at + 3] as i64);
}

// RFC 5905 section 8, in integer milliseconds.
//   t1 = client transmit, t2 = server receive, t3 = server transmit, t4 = client receive.
// Signed offset: add it to the local clock to agree with the server.
fn ntp_offset_delay(t1: i64, t2: i64, t3: i64, t4: i64) -> i64, i64 {
    let offset = ((t2 - t1) + (t3 - t4)) / 2;
    var delay = (t4 - t1) - (t3 - t2);
    if delay < 0 { delay = 0; }        // negative round-trip means the stamps lie
    return offset, delay;
}
