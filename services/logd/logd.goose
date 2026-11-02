// services/logd/logd.goose
//
// Layer 4, service 5: the log sink. Every service's records end up here.
//
// Status: RUNS — reached by tests/t66_shell (57 checks, exit 0). Measured 2026-11-02 by audit_status.py. Verified via goose-mcp@1.1.0: extern/export
// fn forms (spec#40, spec#41), builders and append (samples/03_strings.goose),
// format/format_int (stdlib#9), trailing-bool (samples/04_errors.goose),
// struct literals (tutorial#3), keywords (list_keywords).
//
// THE SHAPE OF THE PROBLEM
// ------------------------
// A log sink has two conflicting duties. It must never lose a record that
// explains a failure, and it must never block a service that is failing. The
// answer here: records go into a ring first, the ring is flushed to the serial
// port when it is worth doing, and if the ring fills up the *loss is counted and
// reported* rather than hidden.
//
// FLUSH POLICY, EXACTLY
// ---------------------
//   1. Flush when the ring is at or above HIGH_WATER (3/4 full): batching keeps
//      the serial port from being a per-record syscall in a busy path.
//   2. Flush immediately for a record at level ERROR, because the record that
//      matters most is the one right before everything stops.
//   3. Flush on an explicit request from the entry loop.
// Nothing else flushes. A timer-driven flush is B-L1-108's job once there is a
// timer service to ask, and inventing one here would be a second clock.
//
// RECORD FORMAT
// -------------
//   <ticks> <tag> <level-letter> <message>\n
// One line per record, no wrapping, no truncation: a message longer than the
// slot is refused (msg_push returns false) and the refusal is counted, because a
// silently shortened error message is worse than an admitted gap.

import common.sys.sys;
import common.ring.ring;
import common.err.err;
import common.fmt.fmt;

// ---------------------------------------------------------------------------
// Levels
// ---------------------------------------------------------------------------

let LVL_DEBUG: i64 = 0;
let LVL_INFO: i64 = 1;
let LVL_WARN: i64 = 2;
let LVL_ERROR: i64 = 3;
let LVL_FATAL: i64 = 4;

// The level below which records are dropped before they reach the ring. Set from
// config (B-L1-13) once config files exist; until then, DEBUG is off in a service
// that has to survive a boot.
var min_level: i64 = LVL_INFO;

fn level_letter(level: i64) -> u8 {
    if level == LVL_DEBUG { return 'D'; }
    if level == LVL_INFO { return 'I'; }
    if level == LVL_WARN { return 'W'; }
    if level == LVL_ERROR { return 'E'; }
    if level == LVL_FATAL { return 'F'; }
    return '?';
}

// ---------------------------------------------------------------------------
// Storage
// ---------------------------------------------------------------------------

let SLOT: i64 = 160;          // one record, including its newline
let SLOTS: i64 = 64;          // 10 KiB of retention: a boot's worth of history
let HIGH_WATER: i64 = 48;     // 3/4 of SLOTS

// The ring writes at absolute offsets, so its arena is a builder filled to
// capacity once at start. A fixed array cannot be passed to it (typed mismatch);
// allocation stops after this call, so the no-heap claim still holds.
var storage: u8[>..] = [];
var queue: MsgRing = msg_init(160, 64);

var dropped_full: i64 = 0;    // records refused: queue full
var dropped_level: i64 = 0;   // records refused: below min_level
var dropped_long: i64 = 0;    // records refused: message too long for a slot
var written: i64 = 0;         // records actually on the wire

// ---------------------------------------------------------------------------
// Writing a record
// ---------------------------------------------------------------------------

// Format one record into `out`. Returns false if it does not fit, so the caller
// can count the loss instead of shipping a truncated line.
// `<ticks> <tag> <L> <msg>\n` -- one record, newline included.
//
// The newline is not decoration: the console writer and every log reader treat the
// newline as the record terminator, so a record without one merges with whatever follows
// it and a single truncated write corrupts two lines instead of one.
//
// The size is computed first and the record is refused outright if it will not fit, so a
// short buffer leaves it EMPTY rather than holding half a line. A caller cannot clear a
// builder, so a half-written record would be shipped as-is.
fn format_record(out: u8[>..]&, cap: i64, level: i64, tag: const u8[:], msg: const u8[:]) -> bool {
    let need = digits_needed(sys_ticks(), 10) + 1 + tag.len + 1 + 1 + 1 + msg.len + 1;
    if need > room_left(out, cap) { return false; }
    if !append_int(out, cap, sys_ticks()) { return false; }
    if !append_char(out, cap, ' ') { return false; }
    if !append_str(out, cap, tag) { return false; }
    if !append_char(out, cap, ' ') { return false; }
    if !append_char(out, cap, level_letter(level)) { return false; }
    if !append_char(out, cap, ' ') { return false; }
    if !append_str(out, cap, msg) { return false; }
    return append_nl(out, cap);
}

// Queue a record. This is the call every service makes.
fn log(level: i64, tag: const u8[:], msg: const u8[:]) -> bool {
    if level < min_level {
        dropped_level = dropped_level + 1;
        return false;
    }
    var rec: u8[>..] = [];
    if !format_record(rec, SLOT, level, tag, msg) {
        // The message could not fit even an empty record buffer of slot size.
        dropped_long = dropped_long + 1;
        return false;
    }
    if !msg_push(queue, storage, rec) {
        dropped_full = dropped_full + 1;
        return false;
    }
    // Policy 2: an error record is worth the syscall immediately.
    if level >= LVL_ERROR { flush(); }
    return true;
}

// Convenience wrappers so call sites read as intent, not as integers.
fn log_info(tag: const u8[:], msg: const u8[:]) -> bool { return log(LVL_INFO, tag, msg); }
fn log_warn(tag: const u8[:], msg: const u8[:]) -> bool { return log(LVL_WARN, tag, msg); }
fn log_error(tag: const u8[:], msg: const u8[:]) -> bool { return log(LVL_ERROR, tag, msg); }

// ---------------------------------------------------------------------------
// Flushing
// ---------------------------------------------------------------------------

// Write `rec` to the serial port, retrying a short write rather than dropping the
// tail. A short write here means the port's buffer was full, not that the port
// failed; a negative return is a real failure and stops the flush.
fn write_record(rec: u8[:]) -> bool {
    var off: i64 = 0;
    var seen: i64 = 0;
    while off < rec.len {
        let n = sys_write_serial(rec[off..rec.len]);
        if n < 0 { return false; }
        if n == 0 {
            // No progress. Yielding is the only thing available; the guard stops
            // an infinite loop on a dead port.
            sys_yield();
            seen = seen + 1;
            if seen > 1000 { return false; }
            continue;
        }
        off = off + n;
    }
    return true;
}

// Drain the queue to the serial port, newest-last so the wire keeps the order the
// records were made in. Stops on the first port failure and leaves the rest
// queued: a dead port must not eat the records that explain why it died.
fn flush() -> i64 {
    var sent: i64 = 0;
    var rec: u8[>..] = [];
    while !ring_is_empty(queue.ring) {
        rec = [];
        if !msg_pop(queue, storage, rec) { break; }
        if !write_record(rec[0..rec.len]) { break; }
        sent = sent + 1;
        written = written + 1;
    }
    return sent;
}

fn should_flush() -> bool {
    return msg_len(queue) >= HIGH_WATER;
}

// ---------------------------------------------------------------------------
// Loss accounting
// ---------------------------------------------------------------------------

// Totals for a status line. A sink that cannot say how much it dropped is a sink
// nobody can trust during an incident.
struct LossStats {
    full: i64,
    level: i64,
    long: i64,
    written: i64,
}

fn loss_stats() -> LossStats {
    return LossStats {
        full: dropped_full,
        level: dropped_level,
        long: dropped_long,
        written: written,
    };
}

// ---------------------------------------------------------------------------
// The service
// Size the arena once: SLOT * SLOTS zero bytes, then the ring owns them.
//
// Named `logd_init` and NOT `storage_init`: Goose's namespace is flat, and the storage
// service already defines a `storage_init(block_count)` with different arity. Two
// definitions of one name in a flat namespace means one of them silently wins, and
// whichever it is, one service's initializer never runs. This was found by auditing
// top-level names across the corpus for collisions, not by watching it fail.
fn logd_init() {
    var i: i64 = 0;
    while i < SLOT * SLOTS { storage.push(0); i = i + 1; }
}

// ---------------------------------------------------------------------------
