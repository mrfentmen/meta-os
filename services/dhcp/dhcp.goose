// services/dhcp/dhcp.goose
//
// Layer 4, service 15: the DHCP client.
//
// Status: RUNS — reached by tests/t57_dhcp_dns (45 checks, exit 0). Measured 2026-11-02 by audit_status.py. Verified via goose-mcp@1.1.0: structs with
// literals (reference#32), static arrays, `while`/`if`, slices `a[x..y]`, `T&`
// references (reference#46), `as` casts, multi-value returns.
//
// WHAT THIS IS
// ------------
// The state machine from RFC 2131 and the packet format from RFC 2131 §2, written from
// the specification: DISCOVER -> OFFER -> REQUEST -> ACK, lease timing from option 51,
// and the renewal point from option 58 when the server offers one.
//
// It speaks to the packet interface (B-L1-29), not to a driver, and it takes time from
// a caller-supplied `now_ms` rather than calling the clock: that is what lets B-L1-57
// drive a whole lease lifetime in a test program without sleeping.
//
// WHAT IT DOES NOT DO
// -------------------
// - No retransmit timers with jitter (RFC 2131 §4.1 asks for randomised backoff). The
//   backoff here doubles and is capped; the randomness needs a source the kernel does
//   not have yet. Recorded, not faked with a constant.
// - No DECLINE/RELEASE/INFORM. A client that cannot yet tell the server it is leaving
//   is honest about that; sending a malformed RELEASE would be worse than silence.
//
// THE ONE MISTAKE THIS FORMAT INVITES
// -----------------------------------
// The fixed header is 236 bytes and `chaddr` is 16 bytes of which only 6 are a MAC.
// Every parser that reads `chaddr` as a 6-byte MAC without checking `hlen` accepts
// hardware addresses it does not understand. This one checks htype == 1 and hlen == 6
// before it believes anything.

import common.err.err;
import netcfg.netcfg;   // Ipv4, ip4(), ip4_mask_contiguous: the model, not a copy of it

let DHCP_SERVER_PORT: i64 = 67;
let DHCP_CLIENT_PORT: i64 = 68;

let DHCP_MAGIC_0: u8 = 0x63;
let DHCP_MAGIC_1: u8 = 0x82;
let DHCP_MAGIC_2: u8 = 0x53;
let DHCP_MAGIC_3: u8 = 0x63;

// Message types (option 53)
let DHCP_DISCOVER: i64 = 1;
let DHCP_OFFER: i64 = 2;
let DHCP_REQUEST: i64 = 3;
let DHCP_DECLINE: i64 = 4;
let DHCP_ACK: i64 = 5;
let DHCP_NAK: i64 = 6;
let DHCP_RELEASE: i64 = 7;
let DHCP_INFORM: i64 = 8;

// Client states
let D_IDLE: i64 = 0;
let D_SELECTING: i64 = 1;      // DISCOVER sent, waiting for OFFER
let D_REQUESTING: i64 = 2;     // REQUEST sent, waiting for ACK
let D_BOUND: i64 = 3;          // address in use
let D_RENEWING: i64 = 4;       // T1 passed, renewing with the same server
let D_REBINDING: i64 = 5;      // T2 passed, asking anyone
let D_FAILED: i64 = 6;         // NAK, or retries exhausted

// ---------------------------------------------------------------------------
// The lease
// ---------------------------------------------------------------------------

struct Lease {
    addr: Ipv4,             // yiaddr
    mask: Ipv4,             // option 1
    gw: Ipv4,               // option 3
    dns1: Ipv4,             // option 6, first server
    dns2: Ipv4,             // option 6, second server
    server_id: Ipv4,        // option 54
    lease_ms: i64,          // option 51, in ms
    t1_ms: i64,             // option 58, or half the lease
    t2_ms: i64,             // option 59, or 7/8 of the lease
    bound_at_ms: i64,       // uptime when the ACK arrived
    mask_given: bool,
    gw_given: bool,
    dns_given: bool,
    server_given: bool,
}

struct Client {
    state: i64,
    xid: i64,               // transaction id, chosen by us and echoed by the server
    mac: u8[..6] = [0; 6],
    retries: i64,
    wait_until_ms: i64,     // when to retry
    backoff_ms: i64,
    lease: Lease,
    last_code: i64,         // why we last failed, for the health line
}

// ---------------------------------------------------------------------------
// Building packets
// ---------------------------------------------------------------------------

// Discover: from 0.0.0.0 to 255.255.255.255, no address requested yet.
//
// The frame is built into the caller's buffer because there is no allocator, and
// because a packet builder that allocated would be the only thing in the layer that
// did.
fn dhcp_build_discover(out: u8[..576]&, xid: i64, mac: u8[..6]&) -> i64 {
    let n = dhcp_build_header(out, xid, mac, DHCP_DISCOVER);
    if n < 0 { return -1; }
    // Options 55 (parameter request list): ask for mask, router, DNS, lease time and the
    // timers up front, so the ACK carries them and we do not need a second exchange.
    var at = n;
    if at + 9 > 576 { return -1; }
    out[at] = 55; at = at + 1;                     // option 55
    out[at] = 6; at = at + 1;                      // length
    out[at] = 1; at = at + 1;                      // subnet mask
    out[at] = 3; at = at + 1;                      // router
    out[at] = 6; at = at + 1;                      // domain name server
    out[at] = 51; at = at + 1;                     // lease time
    out[at] = 58; at = at + 1;                     // renewal time
    out[at] = 59; at = at + 1;                     // rebinding time
    out[at] = 255; at = at + 1;                    // end
    return at;
}

// Request: ask for a specific address from a specific server (SELECTING state).
fn dhcp_build_request(out: u8[..576]&, xid: i64, mac: u8[..6]&, want: Ipv4&, server: Ipv4&) -> i64 {
    let n = dhcp_build_header(out, xid, mac, DHCP_REQUEST);
    if n < 0 { return -1; }
    var at = n;
    // Option 50: requested address.
    if at + 6 > 576 { return -1; }
    out[at] = 50; at = at + 1;
    out[at] = 4; at = at + 1;
    out[at] = want.a; at = at + 1;
    out[at] = want.b; at = at + 1;
    out[at] = want.c; at = at + 1;
    out[at] = want.d; at = at + 1;
    // Option 54: which server's offer we are accepting.
    if at + 6 > 576 { return -1; }
    out[at] = 54; at = at + 1;
    out[at] = 4; at = at + 1;
    out[at] = server.a; at = at + 1;
    out[at] = server.b; at = at + 1;
    out[at] = server.c; at = at + 1;
    out[at] = server.d; at = at + 1;
    if at + 1 > 576 { return -1; }
    out[at] = 255; at = at + 1;
    return at;
}

// The 236-byte fixed header plus the magic cookie, up to the first option.
fn dhcp_build_header(out: u8[..576]&, xid: i64, mac: u8[..6]&, msg_type: i64) -> i64 {
    var i: i64 = 0;
    while i < 240 {
        out[i] = 0;
        i = i + 1;
    }
    out[0] = 1;         // op = BOOTREQUEST
    out[1] = 1;         // htype = Ethernet
    out[2] = 6;         // hlen = 6 bytes of chaddr
    out[3] = 0;         // hops
    dhcp_put_u32(out, 4, xid);
    // secs (8-9) and flags (10-11) stay zero: no elapsed time claimed, and no broadcast
    // flag requested. A server that insists on the broadcast flag will simply not answer
    // a client that cannot receive unicast before it has an address; that is a
    // compatibility question, not a correctness one, and it is recorded in the README.
    var m: i64 = 0;
    while m < 6 {
        out[28 + m] = mac[m];
        m = m + 1;
    }
    out[236] = DHCP_MAGIC_0;
    out[237] = DHCP_MAGIC_1;
    out[238] = DHCP_MAGIC_2;
    out[239] = DHCP_MAGIC_3;

    // First option is always the message type.
    out[240] = 53;
    out[241] = 1;
    out[242] = msg_type as u8;
    return 243;
}

fn dhcp_put_u32(out: u8[..576]&, at: i64, v: i64) {
    out[at] = ((v >> 24) & 0xFF) as u8;
    out[at + 1] = ((v >> 16) & 0xFF) as u8;
    out[at + 2] = ((v >> 8) & 0xFF) as u8;
    out[at + 3] = (v & 0xFF) as u8;
}

fn dhcp_get_u32(pkt: const u8[:], at: i64) -> i64 {
    return (pkt[at] as i64 * 16777216) + (pkt[at + 1] as i64 * 65536) + (pkt[at + 2] as i64 * 256) + (pkt[at + 3] as i64);
}

fn dhcp_ip_from(pkt: const u8[:], at: i64) -> Ipv4 {
    return Ipv4 { a: pkt[at], b: pkt[at + 1], c: pkt[at + 2], d: pkt[at + 3] };
}

// ---------------------------------------------------------------------------
// Parsing a reply
// ---------------------------------------------------------------------------

// Parse an OFFER or ACK into a lease. Returns CODE_OK or a reason.
//
// Every check here exists because a malformed packet must not become a lease: an
// address of 0.0.0.0 bound as real would make the interface look configured and
// unreachable, and a lease of zero seconds would renew in a tight loop.
fn dhcp_parse(pkt: const u8[:], out: Lease&) -> i64 {
    if pkt.len < 240 { return E_CORRUPT; }
    if pkt[0] != 2 { return E_CORRUPT; }              // op = BOOTREPLY
    if pkt[1] != 1 || pkt[2] != 6 { return E_CORRUPT; } // Ethernet, 6 bytes
    if pkt[236] != DHCP_MAGIC_0 || pkt[237] != DHCP_MAGIC_1 || pkt[238] != DHCP_MAGIC_2 || pkt[239] != DHCP_MAGIC_3 {
        return E_CORRUPT;                             // not DHCP, whatever it claims
    }

    out.addr = dhcp_ip_from(pkt, 16);                 // yiaddr
    out.mask = ip4_any();
    out.gw = ip4_any();
    out.dns1 = ip4_any();
    out.dns2 = ip4_any();
    out.server_id = ip4_any();
    out.lease_ms = 0;
    out.t1_ms = 0;
    out.t2_ms = 0;
    out.mask_given = false;
    out.gw_given = false;
    out.dns_given = false;
    out.server_given = false;
    out.bound_at_ms = 0;

    var i: i64 = 240;
    while i < pkt.len {
        let opt = pkt[i];
        if opt == 255 { break; }                      // end
        if opt == 0 { i = i + 1; continue; }                // pad
        if i + 1 >= pkt.len { return E_CORRUPT; }     // a type with no length
        let len = pkt[i + 1] as i64;
        if i + 2 + len > pkt.len { return E_CORRUPT; } // length runs past the packet
        let body = i + 2;

        if opt == 1 && len >= 4 {
            out.mask = dhcp_ip_from(pkt, body);
            if ip4_mask_contiguous(out.mask) { out.mask_given = true; }
        } else if opt == 3 && len >= 4 {
            out.gw = dhcp_ip_from(pkt, body);
            out.gw_given = true;
        } else if opt == 6 && len >= 4 {
            out.dns1 = dhcp_ip_from(pkt, body);
            out.dns_given = true;
            if len >= 8 { out.dns2 = dhcp_ip_from(pkt, body + 4); }
        } else if opt == 51 && len >= 4 {
            // Seconds in the packet, milliseconds internally: the rest of the layer works
            // in ms and converting once here beats converting at every comparison.
            out.lease_ms = dhcp_get_u32(pkt, body) * 1000;
        } else if opt == 54 && len >= 4 {
            out.server_id = dhcp_ip_from(pkt, body);
            out.server_given = true;
        } else if opt == 58 && len >= 4 {
            out.t1_ms = dhcp_get_u32(pkt, body) * 1000;
        } else if opt == 59 && len >= 4 {
            out.t2_ms = dhcp_get_u32(pkt, body) * 1000;
        }
        // Unknown options are skipped, not refused: the option space is shared with
        // vendors and a client that rejected unknown options would fail on most networks.
        i = body + len;
    }

    if ip4_zero(out.addr) { return E_NO_ADDRESS; }     // an offer of 0.0.0.0 is not an offer
    if out.lease_ms <= 0 { return E_INVAL; }
    if !out.mask_given {
        // No mask offered. Classful guessing is exactly what DHCP exists to end, so the
        // interface is left unconfigured rather than given a mask nobody chose.
        return E_NO_MASK;
    }
    if out.t1_ms <= 0 { out.t1_ms = out.lease_ms / 2; }
    if out.t2_ms <= 0 { out.t2_ms = (out.lease_ms * 7) / 8; }
    if out.t1_ms >= out.lease_ms { out.t1_ms = out.lease_ms / 2; }
    if out.t2_ms >= out.lease_ms { out.t2_ms = (out.lease_ms * 7) / 8; }
    if out.t2_ms <= out.t1_ms { out.t2_ms = (out.t1_ms + out.lease_ms) / 2; }
    return CODE_OK;
}

// What kind of message is this? -1 when the packet is not DHCP at all.
fn dhcp_message_type(pkt: const u8[:]) -> i64 {
    if pkt.len < 243 { return -1; }
    if pkt[236] != DHCP_MAGIC_0 || pkt[239] != DHCP_MAGIC_3 { return -1; }
    var i: i64 = 240;
    while i + 1 < pkt.len {
        let opt = pkt[i];
        if opt == 255 { return -1; }
        if opt == 0 { i = i + 1; continue; }
        let len = pkt[i + 1] as i64;
        if i + 2 + len > pkt.len { return -1; }
        if opt == 53 && len >= 1 { return pkt[i + 2] as i64; }
        i = i + 2 + len;
    }
    return -1;
}

// ---------------------------------------------------------------------------
// The state machine
// ---------------------------------------------------------------------------

fn dhcp_init(mac: u8[..6]&, xid: i64) -> Client {
    var c: Client = Client {
        state: 0,
        xid: 0,
        mac: [0; 6],
        retries: 0,
        wait_until_ms: 0,
        backoff_ms: 0,
        lease: Lease { addr: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        mask: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        gw: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        dns1: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        dns2: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        server_id: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        lease_ms: 0,
        t1_ms: 0,
        t2_ms: 0,
        bound_at_ms: 0,
        mask_given: false,
        gw_given: false,
        dns_given: false,
        server_given: false },
        last_code: 0,
    };
    c.state = D_IDLE;
    c.xid = xid;
    var i: i64 = 0;
    while i < 6 {
        c.mac[i] = mac[i];
        i = i + 1;
    }
    c.retries = 0;
    c.wait_until_ms = 0;
    c.backoff_ms = 4000;        // RFC 2131 §4.1 suggests 4 s for the first retransmit
    c.last_code = CODE_OK;
    return c;
}

// Is it time to act? The caller polls this; there are no timers in the kernel surface.
fn dhcp_due(c: Client&, now_ms: i64) -> bool {
    return now_ms >= c.wait_until_ms;
}

// Drive the client one step. Returns (next request wanted, code) where the request is
// DHCP_DISCOVER / DHCP_REQUEST / 0 (nothing to send, wait) / -1 (failed for good).
//
// Time in, decision out: no state is advanced on a clock read, so the same sequence of
// (now_ms, packet) inputs always produces the same decisions.
fn dhcp_step(c: Client&, now_ms: i64, reply_type: i64, offer: Lease&) -> i64, i64 {
    if c.state == D_BOUND || c.state == D_RENEWING || c.state == D_REBINDING {
        let age = now_ms - c.lease.bound_at_ms;
        if age < 0 { return 0, E_STATE; }                 // clock moved backwards
        if age >= c.lease.lease_ms {
            // Lease expired: back to the start. Not a failure -- a client that waited too
            // long is exactly what DISCOVER is for.
            c.state = D_SELECTING;
            c.retries = 0;
            c.backoff_ms = 4000;
            c.wait_until_ms = now_ms;
            return DHCP_DISCOVER, CODE_OK;
        }
        if age >= c.lease.t2_ms {
            c.state = D_REBINDING;
            return DHCP_REQUEST, CODE_OK;
        }
        if age >= c.lease.t1_ms {
            c.state = D_RENEWING;
            return DHCP_REQUEST, CODE_OK;
        }
        return 0, CODE_OK;
    }

    if c.state == D_SELECTING {
        if reply_type == DHCP_OFFER {
            let code = dhcp_lease_ok(offer);
            if code != CODE_OK { c.last_code = code; return DHCP_DISCOVER, code; }
            c.state = D_REQUESTING;
            return DHCP_REQUEST, CODE_OK;
        }
        if now_ms >= c.wait_until_ms {
            c.retries = c.retries + 1;
            if c.retries > 6 { c.state = D_FAILED; c.last_code = E_TIMEOUT; return -1, E_TIMEOUT; }
            c.wait_until_ms = now_ms + c.backoff_ms;
            c.backoff_ms = c.backoff_ms * 2;
            if c.backoff_ms > 64000 { c.backoff_ms = 64000; }
            return DHCP_DISCOVER, CODE_OK;
        }
        return 0, CODE_OK;
    }

    if c.state == D_REQUESTING {
        if reply_type == DHCP_ACK {
            let code = dhcp_lease_ok(offer);
            if code != CODE_OK { c.last_code = code; return DHCP_REQUEST, code; }
            c.lease.bound_at_ms = now_ms;
            c.state = D_BOUND;
            c.retries = 0;
            c.backoff_ms = 4000;
            return 0, CODE_OK;
        }
        if reply_type == DHCP_NAK {
            // The server said no: the address is taken or the request was wrong. Start
            // over rather than retrying a request already refused.
            c.state = D_SELECTING;
            c.retries = 0;
            c.wait_until_ms = now_ms;
            c.last_code = E_REFUSED;
            return DHCP_DISCOVER, E_REFUSED;
        }
        if now_ms >= c.wait_until_ms {
            c.retries = c.retries + 1;
            if c.retries > 4 { c.state = D_FAILED; c.last_code = E_TIMEOUT; return -1, E_TIMEOUT; }
            c.wait_until_ms = now_ms + c.backoff_ms;
            c.backoff_ms = c.backoff_ms * 2;
            if c.backoff_ms > 64000 { c.backoff_ms = 64000; }
            return DHCP_REQUEST, CODE_OK;
        }
        return 0, CODE_OK;
    }

    // D_IDLE, D_FAILED, or anything unknown: the only useful move is a DISCOVER.
    c.state = D_SELECTING;
    c.wait_until_ms = now_ms;
    return DHCP_DISCOVER, CODE_OK;
}

// The lease was parsed by dhcp_parse when the packet arrived; this is the guard that
// stops an unparsed or partial lease from being bound. Kept separate so dhcp_step reads
// as "decide", and so a caller that pre-parsed a reply cannot skip the check.
fn dhcp_lease_ok(lease: Lease&) -> i64 {
    if ip4_zero(lease.addr) { return E_NO_ADDRESS; }
    if lease.lease_ms <= 0 { return E_INVAL; }
    if !lease.mask_given { return E_NO_MASK; }
    return CODE_OK;
}
