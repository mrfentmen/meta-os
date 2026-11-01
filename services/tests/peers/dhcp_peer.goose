// services/tests/peers/dhcp_peer.goose
//
// B-L1-102 — DHCP test peer.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT THIS IS
// ------------
// A server-side packet builder, not a server. It takes the bytes a client sent and
// answers with the bytes a real server would answer with, so the client state machine in
// services/dhcp/dhcp.goose can be driven end to end with no network and no clock.
//
// The peer does NOT decide policy (which pool, who gets what). The caller passes the
// address it wants offered. A test that needs a refusal code writes the refusal bytes
// itself -- teaching this peer to be subtle would make the peer the thing under test.
//
// WHY THE REPLY ECHOES THE XID BY COPYING BYTES
// ---------------------------------------------
// `dhcp_get_u32`/`dhcp_put_u32` exist, but the reply's job is to be *the same transaction*
// as the request. Copying the four bytes cannot get sign extension or endianness wrong at
// all; repacking through i64 can, and that bug would look like "client ignores the offer".

import common.err.err;
import netcfg.netcfg;
import dhcp.dhcp;

let PEER_MAX: i64 = 576;

// Build an OFFER (answers DISCOVER) or an ACK (answers REQUEST).
//
// Returns (length, code). On a request that is not DHCP, or not a DISCOVER/REQUEST, it
// returns (0, E_INVAL): a peer that answered anything with anything would let a client
// bug pass unnoticed.
fn dhcp_peer_reply(request: const u8[:], out: u8[..576]&, offer: Ipv4&, server: Ipv4&,
                   mask: Ipv4&, lease_secs: i64) -> i64, i64 {
    let mt = dhcp_message_type(request);
    var reply_type: i64 = 0;
    if mt == DHCP_DISCOVER { reply_type = DHCP_OFFER; }
    else if mt == DHCP_REQUEST { reply_type = DHCP_ACK; }
    else { return 0, E_INVAL; }
    if lease_secs <= 0 { return 0, E_INVAL; }

    // Header through the magic cookie, zeroed so no stale bytes from a previous packet
    // in the same buffer leak into the reply.
    var i: i64 = 0;
    while i < 240 {
        out[i] = 0;
        i++;
    }

    out[0] = 2;                       // op = BOOTREPLY
    out[1] = request[1];              // htype echoed ("Ethernet" on every real network)
    out[2] = request[2];              // hlen echoed
    out[3] = 0;                       // hops

    // xid: copied, not recomputed. See the note at the top of the file.
    dhcp_peer_copy(request, 4, out, 4, 4);
    // secs and flags stay zero, matching what the client sends.

    // yiaddr (16-20): the address being handed out.
    out[16] = offer.a; out[17] = offer.b; out[18] = offer.c; out[19] = offer.d;
    // siaddr (20-24): the server's own address.
    out[20] = server.a; out[21] = server.b; out[22] = server.c; out[23] = server.d;
    // chaddr (28-34): echoed so the client can tell its own reply from another's.
    dhcp_peer_copy(request, 28, out, 28, 6);

    out[236] = DHCP_MAGIC_0;
    out[237] = DHCP_MAGIC_1;
    out[238] = DHCP_MAGIC_2;
    out[239] = DHCP_MAGIC_3;

    var at: i64 = 240;
    at = dhcp_peer_opt_u8(out, at, 53, reply_type);        // message type
    if at < 0 { return 0, E_NOROOM; }
    at = dhcp_peer_opt_ip(out, at, 1, mask);               // subnet mask
    if at < 0 { return 0, E_NOROOM; }
    at = dhcp_peer_opt_ip(out, at, 54, server);            // server identifier
    if at < 0 { return 0, E_NOROOM; }
    at = dhcp_peer_opt_u32(out, at, 51, lease_secs);       // lease time, seconds
    if at < 0 { return 0, E_NOROOM; }

    if at + 1 > PEER_MAX { return 0, E_NOROOM; }
    out[at] = 255;                                         // end
    at++;
    return at, CODE_OK;
}

fn dhcp_peer_copy(src: const u8[:], src_at: i64, dst: u8[..576]&, dst_at: i64, n: i64) {
    var i: i64 = 0;
    while i < n {
        dst[dst_at + i] = src[src_at + i];
        i++;
    }
}

fn dhcp_peer_opt_u8(out: u8[..576]&, at: i64, code: i64, v: i64) -> i64 {
    if at + 3 > PEER_MAX { return -1; }
    out[at] = code as u8;
    out[at + 1] = 1;
    out[at + 2] = v as u8;
    return at + 3;
}

fn dhcp_peer_opt_ip(out: u8[..576]&, at: i64, code: i64, v: Ipv4&) -> i64 {
    if at + 6 > PEER_MAX { return -1; }
    out[at] = code as u8;
    out[at + 1] = 4;
    out[at + 2] = v.a;
    out[at + 3] = v.b;
    out[at + 4] = v.c;
    out[at + 5] = v.d;
    return at + 6;
}

fn dhcp_peer_opt_u32(out: u8[..576]&, at: i64, code: i64, v: i64) -> i64 {
    if at + 6 > PEER_MAX { return -1; }
    out[at] = code as u8;
    out[at + 1] = 4;
    out[at + 2] = ((v >> 24) & 0xFF) as u8;
    out[at + 3] = ((v >> 16) & 0xFF) as u8;
    out[at + 4] = ((v >> 8) & 0xFF) as u8;
    out[at + 5] = (v & 0xFF) as u8;
    return at + 6;
}
