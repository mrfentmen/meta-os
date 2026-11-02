// services/common/ring/ring.goose
//
// Ring buffers over caller storage: the queue under the log service, the
// history ring under the console, and the record ring under the audit writer.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0:
// - growable `u8[>..]` arrays, `push`, `append`, `.len` .... samples/03_strings.goose
// - whole-element assignment `a[i] = v` ..................... stdlib#13 (slot_pool)
// - bounds checks abort, so indices are always computed mod cap  reference#82
// - trailing-bool convention ............................... samples/04_errors.goose
//
// THE STORAGE RULE
// ----------------
// A ring never owns its bytes. The caller hands in a buffer that is at least
// `cap` long, and the ring only ever indexes `0 .. cap-1`. Two consequences
// worth stating: a ring cannot grow (there is no heap), and a ring whose buffer
// is shorter than `cap` is a caller bug that aborts on the first wrapped write
// rather than corrupting anything.
//
// WHY THE INDICES STAY SMALL
// --------------------------
// `head` and `tail` are positions in `0 .. cap-1`, not free-running counters.
// A free-running counter would need wrap handling on every read and would
// overflow after 2^63 operations; modulo positions with an explicit `count` are
// simpler to reason about and to test (B-L1-46).

struct Ring {
    head: i64,      // next byte to read
    tail: i64,      // next byte to write
    count: i64,     // bytes currently held
    cap: i64,       // storage the caller promised
}

fn ring_init(cap: i64) -> Ring {
    return Ring { head: 0, tail: 0, count: 0, cap: cap };
}

fn ring_len(r: Ring&) -> i64 {
    return r.count;
}

fn ring_cap(r: Ring&) -> i64 {
    return r.cap;
}

fn ring_is_empty(r: Ring&) -> bool {
    return r.count == 0;
}

fn ring_is_full(r: Ring&) -> bool {
    return r.count >= r.cap;
}

// Bytes free. Useful for a writer deciding whether to flush now or keep going.
fn ring_space(r: Ring&) -> i64 {
    if r.count >= r.cap { return 0; }
    return r.cap - r.count;
}

fn ring_clear(r: Ring&) {
    r.head = 0;
    r.tail = 0;
    r.count = 0;
}

// Push one byte. Returns false when full; it does NOT overwrite, because a log
// ring that silently eats its oldest record is a log ring that lies about what
// happened. Callers that do want overwrite use ring_push_over.
fn ring_push(r: Ring&, buf: u8[>..]&, b: u8) -> bool {
    if r.cap <= 0 || r.count >= r.cap { return false; }
    buf[r.tail] = b;
    r.tail = r.tail + 1;
    if r.tail >= r.cap { r.tail = 0; }
    r.count = r.count + 1;
    return true;
}

// Push, dropping the oldest byte when full. Returns true when something was
// dropped, so the caller can count lost records instead of wondering.
fn ring_push_over(r: Ring&, buf: u8[>..]&, b: u8) -> bool {
    var dropped = false;
    if r.cap <= 0 { return false; }
    if r.count >= r.cap {
        // Advance the read position instead of refusing the write.
        r.head = r.head + 1;
        if r.head >= r.cap { r.head = 0; }
        r.count = r.count - 1;
        dropped = true;
    }
    buf[r.tail] = b;
    r.tail = r.tail + 1;
    if r.tail >= r.cap { r.tail = 0; }
    r.count = r.count + 1;
    return dropped;
}

fn ring_peek(r: Ring&, buf: u8[>..]&) -> u8, bool {
    if r.count <= 0 { return 0, false; }
    return buf[r.head], true;
}

fn ring_pop(r: Ring&, buf: u8[>..]&) -> u8, bool {
    if r.count <= 0 { return 0, false; }
    let b = buf[r.head];
    r.head = r.head + 1;
    if r.head >= r.cap { r.head = 0; }
    r.count = r.count - 1;
    return b, true;
}

// Copy up to `max` bytes out of the ring into `out`, stopping early if the ring
// empties. Returns how many were copied. `out` must have room for `max`; the
// caller's format library cap rule applies here too.
fn ring_drain(r: Ring&, buf: u8[>..]&, out: u8[>..]&, max: i64) -> i64 {
    var n: i64 = 0;
    while n < max && r.count > 0 {
        let b, ok = ring_pop(r, buf);
        if !ok { break; }
        out.push(b);
        n = n + 1;
    }
    return n;
}

// Copy ring contents out without consuming them. Used by a debug dump and by the
// console's history recall, which must not destroy the history it shows.
fn ring_snapshot(r: Ring&, buf: u8[>..]&, out: u8[>..]&) -> i64 {
    var i: i64 = 0;
    var pos = r.head;
    while i < r.count {
        out.push(buf[pos]);
        pos = pos + 1;
        if pos >= r.cap { pos = 0; }
        i = i + 1;
    }
    return i;
}

// ---------------------------------------------------------------------------
// Message ring: fixed-size slots over the same byte ring
// ---------------------------------------------------------------------------
//
// The log, audit and IPC paths all queue fixed-size records. Storing them as
// length-prefixed slot-pairs keeps one implementation and one set of tests: the
// slot size is the record's maximum, and a record shorter than its slot occupies
// the whole slot anyway, because a variable-length record in a byte ring needs a
// header scan on every pop and can desynchronise after a single lost byte.

struct MsgRing {
    ring: Ring,
    slot: i64,      // bytes per message, including its one-byte length prefix
}

fn msg_init(slot: i64, count: i64) -> MsgRing {
    return MsgRing { ring: ring_init(count * slot), slot: slot };
}

fn msg_capacity(m: MsgRing&) -> i64 {
    return m.ring.cap / m.slot;
}

fn msg_len(m: MsgRing&) -> i64 {
    return m.ring.count / m.slot;
}

// Queue one message. A message longer than slot-1 is refused rather than
// truncated: a half-written record in an audit trail is worse than no record.
fn msg_push(m: MsgRing&, buf: u8[>..]&, msg: const u8[:]) -> bool {
    if m.slot < 2 { return false; }
    let limit = m.slot - 1;                 // one byte for the length
    if msg.len > limit { return false; }
    if ring_space(m.ring) < m.slot { return false; }

    var i: i64 = 0;
    if !ring_push(m.ring, buf, msg.len as u8) { return false; }
    while i < m.slot - 1 {
        var b: u8 = 0;
        if i < msg.len { b = msg[i]; }
        if !ring_push(m.ring, buf, b) { return false; }
        i = i + 1;
    }
    // ring_push advanced tail through the whole slot, so the slot is aligned by
    // construction as long as slot divides cap -- msg_init guarantees that.
    return true;
}

// Dequeue one message into `out`, which must have room for slot-1 bytes.
fn msg_pop(m: MsgRing&, buf: u8[>..]&, out: u8[>..]&) -> bool {
    if m.slot < 2 || m.ring.count < m.slot { return false; }
    let n, ok = ring_pop(m.ring, buf);
    if !ok { return false; }
    let len = n as i64;
    if len > m.slot - 1 { return false; }   // a corrupt slot is refused, not read
    var i: i64 = 0;
    while i < m.slot - 1 {
        let b, got = ring_pop(m.ring, buf);
        if !got { return false; }
        if i < len { out.push(b); }
        i = i + 1;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Not provided, on purpose
// ---------------------------------------------------------------------------
//
// - No blocking pop. There is no wait primitive (Q-B-L1-1); a service that wants
//   to wait polls ring_is_empty and yields.
// - No resize. There is no heap, and a ring that reallocates is a ring whose
//   buffer address moves under whoever holds a reference to it.
// - No thread safety. Goose threads share nothing (tutorial#21), so a ring is
//   either owned by one service or reached through IPC, never shared.
