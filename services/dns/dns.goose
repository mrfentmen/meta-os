// services/dns/dns.goose
//
// Layer 4, service 16: the DNS resolver client.
//
// Status: RUNS — reached by tests/t57_dhcp_dns (45 checks, exit 0). Measured 2026-11-02 by audit_status.py. Verified via goose-mcp@1.1.0: structs, static
// arrays, `while`/`if`, slices, `T&`, `as` casts, multi-value returns.
//
// WHAT THIS IS
// ------------
// Query construction (RFC 1035 §4.1.2), and response parsing including **compression
// pointers** (§4.1.4) with a loop guard. One A-record lookup, because that is what the
// layer needs to reach a name; AAAA and everything else are deliberately not attempted
// until IPv6 exists anywhere in this stack.
//
// THE COMPRESSION POINTER IS THE WHOLE PROBLEM
// --------------------------------------------
// A name may be encoded as a pointer to a sequence of bytes anywhere earlier in the
// packet. That makes a naive parser trivially crashable and makes a careless one
// infinitely loopable:
//
//   - a pointer into itself, or two pointers pointing at each other, is a valid-looking
//     encoding that never terminates;
//   - a pointer that points forward, outside the packet, or into the middle of a header
//     reads data that is not a name.
//
// So: every pointer must point strictly backwards (a forward or same-offset pointer is
// refused), the number of jumps is capped, and the total name length is capped at the
// 255 bytes the format allows. Three guards, because one of them will be the one that
// matters.
//
// WHAT IT WILL NOT DO
// -------------------
// - No cache. A cache needs an eviction policy and a clock; both exist elsewhere, and a
//   resolver with a half-built cache returns stale addresses with confidence.
// - No retry/backoff. The caller (B-L1-57's harness, or the socket layer) owns timeouts.
//   This file is pure: bytes in, bytes out.

import common.err.err;
import netcfg.netcfg;

let DNS_PORT: i64 = 53;
let DNS_NAME_MAX: i64 = 255;        // the format's own limit, not a choice
let DNS_LABEL_MAX: i64 = 63;
let DNS_QUERY_MAX: i64 = 512;       // classic UDP DNS without EDNS
let DNS_MAX_JUMPS: i64 = 32;        // pointer chain depth

let T_A: i64 = 1;
let C_IN: i64 = 1;

let RCODE_OK: i64 = 0;
let RCODE_FORMAT: i64 = 1;
let RCODE_SERVFAIL: i64 = 2;
let RCODE_NXDOMAIN: i64 = 3;
let RCODE_NOTIMP: i64 = 4;
let RCODE_REFUSED: i64 = 5;

// ---------------------------------------------------------------------------
// Building a query
// ---------------------------------------------------------------------------

// Build a recursive A query for `name` into `out`. Returns the length, or -1 when the
// name cannot be encoded.
//
// The name is encoded label by label: a length byte then that many bytes. A trailing dot
// is accepted and not double-encoded; an empty label (a `..` in the name) is refused
// rather than emitted, because a zero-length label is the root terminator and a query
// containing one in the middle is malformed by construction.
fn dns_build_a_query(out: u8[..512]&, name: const u8[:], id: i64) -> i64 {
    if name.len == 0 || name.len > DNS_NAME_MAX { return -1; }
    if out.len < 12 { return -1; }

    var i: i64 = 0;
    while i < 12 {
        out[i] = 0;
        i = i + 1;
    }
    // id, big-endian: the server echoes it and the caller checks it, so a reply that
    // belongs to somebody else's question cannot be accepted as ours.
    out[0] = ((id >> 8) & 0xFF) as u8;
    out[1] = (id & 0xFF) as u8;
    out[2] = 0x01;              // RD = 1 (recursion desired)
    out[3] = 0x00;              // opcode 0, no flags
    out[4] = 0;                 // QDCOUNT = 1
    out[5] = 1;
    out[6] = 0;                 // ANCOUNT
    out[7] = 0;
    out[8] = 0;                 // NSCOUNT
    out[9] = 0;
    out[10] = 0;                // ARCOUNT
    out[11] = 0;

    var at: i64 = 12;
    var label_start: i64 = 0;
    var in_label: i64 = 0;

    // `i` is still 12 from the header loop; the name starts at byte 0 of `name`. Without
    // this reset the first twelve characters of every hostname are silently dropped and
    // the query asks for a name nobody typed.
    i = 0;
    while i < name.len {
        let ch = name[i];
        if ch == 0x2E {                                  // .
            // A dot at the very start, or two in a row, is an empty label.
            if in_label == 0 { return -1; }       // leading or doubled dot: empty label
            if at + 1 + in_label > DNS_QUERY_MAX { return -1; }
            out[at] = in_label as u8;
            at = at + 1;
            var k: i64 = 0;
            while k < in_label {
                out[at] = name[label_start + k];
                at = at + 1;
                k = k + 1;
            }
            in_label = 0;
            label_start = i + 1;
        } else {
            // A label longer than 63 bytes cannot be encoded: the length byte's top two
            // bits are the compression marker, so 64..191 are not lengths at all.
            if in_label >= DNS_LABEL_MAX { return -1; }
            in_label = in_label + 1;
        }
        i = i + 1;
    }
    // Trailing label (a name without a final dot is the normal case).
    if in_label > 0 {
        if at + 1 + in_label > DNS_QUERY_MAX { return -1; }
        out[at] = in_label as u8;
        at = at + 1;
        var k2: i64 = 0;
        while k2 < in_label {
            out[at] = name[label_start + k2];
            at = at + 1;
            k2 = k2 + 1;
        }
    }
    // Root terminator.
    if at + 5 > DNS_QUERY_MAX { return -1; }
    out[at] = 0;
    at = at + 1;
    out[at] = 0;                // QTYPE = A
    at = at + 1;
    out[at] = 1;
    at = at + 1;
    out[at] = 0;                // QCLASS = IN
    at = at + 1;
    out[at] = 1;
    at = at + 1;
    return at;
}

// ---------------------------------------------------------------------------
// Parsing a response
// ---------------------------------------------------------------------------

struct Answer {
    addr: Ipv4,
    ttl: i64,               // seconds as the server wrote them; the caller converts
    rcode: i64,
}

// Read a name at `at`, following compression pointers, appending into `out`.
//
// Returns (next_offset, name_length, ok). `next_offset` is where parsing continues in
// the *original* position, not where the pointer led: a caller that continued at the
// pointed-to offset would re-read records already consumed.
fn dns_read_name(pkt: const u8[:], at_start: i64, out: u8[..256]&) -> i64, i64, bool {
    var at = at_start;
    var out_len: i64 = 0;
    var jumps: i64 = 0;
    var next = -1;              // where to continue, set at the first pointer
    var seen: i64 = 0;

    while seen < 512 {
        seen = seen + 1;
        if at < 0 || at >= pkt.len { return 0, 0, false; }
        let b = pkt[at];
        if (b & 0xC0) == 0xC0 {                       // compression pointer
            if at + 1 >= pkt.len { return 0, 0, false; }
            let target = ((b & 0x3F) as i64) * 256 + (pkt[at + 1] as i64);
            if next < 0 { next = at + 2; }
            jumps = jumps + 1;
            if jumps > DNS_MAX_JUMPS { return 0, 0, false; }
            // Strictly backwards, always. A forward pointer can loop forever and can read
            // sections the packet has not finished writing; a same-offset pointer is a
            // one-instruction infinite loop. Both are refused here, not later.
            if target >= at { return 0, 0, false; }
            at = target;
            continue;
        }
        if (b & 0xC0) != 0 { return 0, 0, false; }    // reserved label type
        let len = b as i64;
        if len == 0 {                                  // root: end of name
            if next < 0 { next = at + 1; }
            return next, out_len, true;
        }
        if at + 1 + len > pkt.len { return 0, 0, false; }
        if out_len + len + 1 > DNS_NAME_MAX { return 0, 0, false; }
        if out_len > 0 {
            out[out_len] = 0x2E;                       // join labels with dots
            out_len = out_len + 1;
        }
        var k: i64 = 0;
        while k < len {
            out[out_len] = pkt[at + 1 + k];
            out_len = out_len + 1;
            k = k + 1;
        }
        at = at + 1 + len;
    }
    return 0, 0, false;                                // guard exhausted
}

// Parse a reply for the question `id` and return the first A record.
//
// Refusals matter more than successes here: a resolver that accepted a mismatched id
// would be answering somebody else's question, and one that accepted a truncated packet
// would resolve names to addresses assembled from adjacent memory.
fn dns_parse_a(pkt: const u8[:], id: i64, out: Answer&) -> i64 {
    out.addr = ip4_any();
    out.ttl = 0;
    out.rcode = RCODE_OK;

    if pkt.len < 12 { return E_CORRUPT; }
    let rid = (pkt[0] as i64 * 256) + (pkt[1] as i64);
    if rid != id { return E_STATE; }                 // not our transaction
    let flags = pkt[2];
    if (flags & 0x80) == 0 { return E_CORRUPT; }     // not a response
    out.rcode = (pkt[3] & 0x0F) as i64;
    // A non-zero rcode is a real ANSWER from a working server, not a parse failure:
    // NXDOMAIN means the name does not exist and says so definitively. Returning an
    // error here threw that away -- the caller could not tell "no such name" from "the
    // wire ate my packet", and would retry a name that will never resolve. The rcode is
    // reported and the caller decides what it means.
    if out.rcode != RCODE_OK {
        if out.rcode == RCODE_NXDOMAIN { return CODE_OK; }
        return E_RESOLVE;
    }

    let qd = (pkt[4] as i64 * 256) + (pkt[5] as i64);
    let an = (pkt[6] as i64 * 256) + (pkt[7] as i64);
    if qd != 1 { return E_CORRUPT; }
    if an < 1 { return E_RESOLVE; }                  // no records: name does not resolve

    // Skip the question section.
    var namebuf: u8[..256] = [0; 256];
    let q_end, q_len, q_ok = dns_read_name(pkt, 12, namebuf);
    if !q_ok { return E_CORRUPT; }
    if q_end + 4 > pkt.len { return E_CORRUPT; }     // QTYPE + QCLASS
    var at = q_end + 4;

    var i: i64 = 0;
    while i < an {
        let owner, olen, ok2 = dns_read_name(pkt, at, namebuf);
        if !ok2 { return E_CORRUPT; }
        at = owner;
        if at + 10 > pkt.len { return E_CORRUPT; }   // type, class, ttl, rdlength
        let rtype = (pkt[at] as i64 * 256) + (pkt[at + 1] as i64);
        let rclass = (pkt[at + 2] as i64 * 256) + (pkt[at + 3] as i64);
        let ttl = (pkt[at + 4] as i64 * 16777216) + (pkt[at + 5] as i64 * 65536) + (pkt[at + 6] as i64 * 256) + (pkt[at + 7] as i64);
        let rdlen = (pkt[at + 8] as i64 * 256) + (pkt[at + 9] as i64);
        at = at + 10;
        if at + rdlen > pkt.len { return E_CORRUPT; }

        if rtype == T_A && rclass == C_IN {
            // An A record must be exactly 4 bytes. A longer one is either a different
            // record pretending to be A or a malformed packet; both are refused.
            if rdlen != 4 { return E_CORRUPT; }
            out.addr = Ipv4 { a: pkt[at], b: pkt[at + 1], c: pkt[at + 2], d: pkt[at + 3] };
            out.ttl = ttl;
            return CODE_OK;
        }
        at = at + rdlen;                             // not an A record: skip it properly
        i = i + 1;
    }
    return E_RESOLVE;
}

// ---------------------------------------------------------------------------
// One exchange, expressed as a sequence a caller (or a test) drives
// ---------------------------------------------------------------------------

let Q_IDLE: i64 = 0;
let Q_SENT: i64 = 1;
let Q_DONE: i64 = 2;
let Q_FAILED: i64 = 3;

struct Query {
    id: i64,
    state: i64,
    sent_at_ms: i64,
    timeout_ms: i64,
    attempts: i64,
    result: Answer,
}

fn dns_query_init(id: i64, timeout_ms: i64) -> Query {
    var q: Query = Query {
        id: 0,
        state: 0,
        sent_at_ms: 0,
        timeout_ms: 0,
        attempts: 0,
        result: Answer { addr: Ipv4 { a: 0,
        b: 0,
        c: 0,
        d: 0 },
        ttl: 0,
        rcode: 0 },
    };
    q.id = id;
    q.state = Q_IDLE;
    q.sent_at_ms = 0;
    q.timeout_ms = timeout_ms;
    q.attempts = 0;
    return q;
}

// Has the attempt timed out? Expressed as a question, not a sleep, for the same reason
// DHCP's timing is: a test drives it.
fn dns_query_expired(q: Query&, now_ms: i64) -> bool {
    if q.state != Q_SENT { return false; }
    let elapsed = now_ms - q.sent_at_ms;
    if elapsed < 0 { return true; }             // a clock that went backwards is not a pass
    return elapsed >= q.timeout_ms;
}

fn dns_query_sent(q: Query&, now_ms: i64) {
    q.state = Q_SENT;
    q.sent_at_ms = now_ms;
    q.attempts = q.attempts + 1;
}

// Feed a received packet to the query. A packet that is not our transaction leaves the
// query exactly as it was: on a busy network, most arriving packets are somebody else's.
fn dns_query_feed(q: Query&, pkt: const u8[:]) -> i64 {
    if q.state != Q_SENT { return E_STATE; }
    var a: Answer = Answer { addr: Ipv4 { a: 0, b: 0, c: 0, d: 0 }, ttl: 0, rcode: 0 };
    let code = dns_parse_a(pkt, q.id, a);
    if code == E_STATE { return E_STATE; }      // not ours; keep waiting
    if code != CODE_OK {
        q.state = Q_FAILED;
        return code;
    }
    q.result = a;
    q.state = Q_DONE;
    return CODE_OK;
}
