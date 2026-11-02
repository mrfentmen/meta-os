// services/timesync/timesync.goose
//
// Layer 4, service 19: the wall-clock offset. What time it is, as opposed to how long
// the machine has been up.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs, static
// arrays, `while`/`if`, slices, `T&` references (reference#46), `as` casts,
// multi-value returns.
//
// THE RULE THIS SERVICE EXISTS TO KEEP
// ------------------------------------
// The monotonic clock (services/time, B-L1-19) is never moved. It answers "how long has
// this been running" and a hundred deadlines depend on it; an NTP correction applied to it
// would make every timeout in the layer either fire early or wait longer, and the ones
// that fired early would do so in the middle of an update.
//
// So wall-clock correction is an OFFSET held here, applied only when something asks what
// date it is. `now = monotonic_ms + offset_ms`.
//
// WHY THE OFFSET IS SMEARED
// -------------------------
// Applying a 2-second correction instantly makes time appear to repeat: a log written
// after the step can carry an earlier timestamp than one written before it, and anything
// that sorts by timestamp now sorts wrongly. The offset moves toward the target at a
// bounded rate instead, so time is always increasing -- at the cost of the correction
// taking a while, which nobody can perceive.
//
// WHAT THIS DOES NOT DO
// ---------------------
// No packet is sent from here. Building and parsing the NTP message is below, but the
// exchange (send, wait, receive) needs the socket layer and a timeout, and the caller owns
// both. Every function here is pure apart from the offset it holds.

import common.err.err;

let NTP_PACKET: i64 = 48;
let NTP_MODE_CLIENT: i64 = 3;
let NTP_MODE_SERVER: i64 = 4;
let NTP_VERSION: i64 = 4;

// Seconds between 1900-01-01 (NTP epoch) and 1970-01-01 (Unix epoch). The NTP timestamp is
// 64-bit fixed point: 32 bits of seconds, 32 bits of fraction, both since 1900.
let NTP_UNIX_DELTA: i64 = 2208988800;

// A server claiming an offset larger than a day is not a clock correction, it is a
// server with a different idea of the date or a stale response. Refused, not applied.
let NTP_MAX_OFFSET_MS: i64 = 86400000;

// Smear rate: at most 1 ms of correction applied per ms of real time (never behind), and
// at most 10% of the remaining error per step, so a large correction takes many steps
// rather than one visible jump.
let NTP_SMEAR_DIVISOR: i64 = 10;
let NTP_SMEAR_MIN_MS: i64 = 1;

struct SyncState {
    offset_ms: i64,          // applied: monotonic + offset = wall clock
    target_offset_ms: i64,   // where the last measurement says it should be
    last_sync_ms: i64,       // monotonic uptime of the last accepted measurement
    last_roundtrip_ms: i64,
    syncs: i64,
    rejects: i64,
}

var sync_state: SyncState = SyncState {
    offset_ms: 0,
    target_offset_ms: 0,
    last_sync_ms: 0,
    last_roundtrip_ms: 0,
    syncs: 0,
    rejects: 0,
};

// ---------------------------------------------------------------------------
// Wall clock
// ---------------------------------------------------------------------------

fn ts_now_ms(mono_ms: i64) -> i64 {
    return mono_ms + sync_state.offset_ms;
}

// Move the offset toward the target by at most one step. Called from whatever loop owns
// time; it is a no-op when the offset is already there.
fn ts_smear_step(mono_ms: i64) -> i64 {
    let error = sync_state.target_offset_ms - sync_state.offset_ms;
    if error == 0 { return 0; }
    var step = error / NTP_SMEAR_DIVISOR;
    if step == 0 {
        // Never zero for a non-zero error, or the last few milliseconds would never close.
        if error > 0 { step = NTP_SMEAR_MIN_MS; } else { step = -NTP_SMEAR_MIN_MS; }
    }
    // Never overshoot the target: overshoot is a second visible jump in the other
    // direction, which is worse than a slower correction.
    if step > error { step = error; }
    if step < error && error < 0 { step = error; }
    sync_state.offset_ms = sync_state.offset_ms + step;
    let _ = mono_ms;         // time is not needed here, but the signature keeps call sites uniform
    return step;
}

fn ts_pending_ms() -> i64 {
    return sync_state.target_offset_ms - sync_state.offset_ms;
}

// ---------------------------------------------------------------------------
// NTP message
// ---------------------------------------------------------------------------

// Build a client request. `client_ms` is the monotonic clock, stamped into transmit time
// so the reply can be paired with this request.
//
// Returns bytes written (48) or -1.
fn ntp_build_request(out: u8[..48]&, client_ms: i64) -> i64 {
    if out.len < NTP_PACKET { return -1; }
    var i: i64 = 0;
    while i < NTP_PACKET {
        out[i] = 0;
        i = i + 1;
    }
    // LI = 0, VN = 4, Mode = 3 (client)
    out[0] = ((NTP_VERSION << 3) | NTP_MODE_CLIENT) as u8;
    // Everything else zero: stratum and identifiers are the server's to fill.
    ntp_put_time(out, 40, ts_now_ms(client_ms));
    return NTP_PACKET;
}

// 64-bit NTP timestamp: seconds since 1900 in the high word, fraction in the low word.
fn ntp_put_time(out: u8[..48]&, at: i64, unix_ms: i64) {
    var secs = unix_ms / 1000;
    var ms = unix_ms % 1000;
    if ms < 0 { ms = 0; }
    if secs < 0 { secs = 0; }
    secs = secs + NTP_UNIX_DELTA;
    let frac = (ms * 4294967) / 1000;        // ms -> 2^32 fraction, integer maths
    put_u32_in48(out, at, secs);
    put_u32_in48(out, at + 4, frac);
}

fn put_u32_in48(out: u8[..48]&, at: i64, v: i64) {
    out[at] = ((v >> 24) & 0xFF) as u8;
    out[at + 1] = ((v >> 16) & 0xFF) as u8;
    out[at + 2] = ((v >> 8) & 0xFF) as u8;
    out[at + 3] = (v & 0xFF) as u8;
}

fn get_u32(pkt: const u8[:], at: i64) -> i64 {
    return (pkt[at] as i64 * 16777216) + (pkt[at + 1] as i64 * 65536) + (pkt[at + 2] as i64 * 256) + (pkt[at + 3] as i64);
}

// NTP timestamp -> unix ms. The fraction is converted back with the same integer maths
// used to write it, so a request/reply pair round-trips without drift from float.
fn ntp_read_time(pkt: const u8[:], at: i64) -> i64 {
    let secs = get_u32(pkt, at);
    let frac = get_u32(pkt, at + 4);
    if secs == 0 && frac == 0 { return 0; }              // "not set" is not 1900
    let ms = (frac / 4294967);
    return (secs - NTP_UNIX_DELTA) * 1000 + ms;
}

// ---------------------------------------------------------------------------
// The measurement
// ---------------------------------------------------------------------------

// Apply a server reply.
//
// Inputs are monotonic uptimes: `t1` when the request left, `t2` when it arrived here.
// The packet carries the server's receive (t2') and transmit (t3') times. With them:
//
//     offset = ((t2' - t1) + (t3' - t2)) / 2
//     delay  =  (t2 - t1) - (t3' - t2')
//
// This is RFC 5905's own arithmetic, not an approximation: the two halves are the error
// on each leg, and averaging them cancels the asymmetry a one-way measurement cannot see.
//
// Refusals, each of which would otherwise corrupt the clock:
//   - mode is not 4 (server): not a reply;
//   - stratum 0: a KoD ("kiss-o'-death") packet, whose whole purpose is "stop asking";
//   - leap indicator 3: the server itself is unsynchronised, so its time is a guess;
//   - transmit time zero: the server did not fill it;
//   - |offset| beyond a day: a wrong server, not a wrong clock;
//   - negative delay: the timestamps are impossible, so one of them is a lie.
fn ntp_apply_reply(pkt: const u8[:], t1_mono: i64, t2_mono: i64) -> i64 {
    if pkt.len < NTP_PACKET { return E_CORRUPT; }
    let li = (pkt[0] >> 6) & 0x3;
    let mode = pkt[0] & 0x7;
    let stratum = pkt[1] as i64;
    if mode != NTP_MODE_SERVER { return E_CORRUPT; }
    if stratum == 0 { return E_REFUSED; }                // kiss-o'-death (or unsynchronised)
    if li == 3 { return E_UNSUPPORTED; }

    let server_recv = ntp_read_time(pkt, 32);
    let server_send = ntp_read_time(pkt, 40);
    if server_send == 0 { return E_CORRUPT; }

    let offset_a = server_recv - ts_now_ms(t1_mono);
    let offset_b = server_send - ts_now_ms(t2_mono);
    let offset = (offset_a + offset_b) / 2;

    let delay = (t2_mono - t1_mono) - (server_send - server_recv);
    if delay < 0 { return E_CORRUPT; }
    if offset > NTP_MAX_OFFSET_MS || offset < -NTP_MAX_OFFSET_MS {
        sync_state.rejects = sync_state.rejects + 1;
        return E_INVAL;
    }

    sync_state.target_offset_ms = offset;
    sync_state.last_sync_ms = t2_mono;
    sync_state.last_roundtrip_ms = delay;
    sync_state.syncs = sync_state.syncs + 1;
    // The applied offset is NOT touched: the smear closes the gap over the next steps.
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Deliberately absent
// ---------------------------------------------------------------------------
//
// - No DNS. An NTP server is named in config, and resolving it is the resolver's job
//   (B-L1-32), called by whoever owns the exchange.
// - No retry schedule. The caller owns timeouts, as with DHCP and the resolver.
// - No drift estimation: a real client models the local oscillator and asks the server
//   less often as it learns. With no long-running measurement data yet, an estimator would
//   be fitted to noise.
