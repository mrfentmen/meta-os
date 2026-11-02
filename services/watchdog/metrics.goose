// services/watchdog/metrics.goose
//
// B-L1-124 — Health metrics: the standard counters and gauges every service reports.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// FOUR NUMBERS, EVERY SERVICE
// ---------------------------
//   calls     counter, monotonic: work requested
//   errors    counter, monotonic: work that returned a non-OK code
//   uptime_ms gauge: how long since the service reported itself started
//   queue     gauge: items waiting (0 for a service with no queue)
//
// That is the whole standard. The temptation is a metric per feature; the result is a health
// line nobody reads. A service that needs another number registers a NAMED gauge, and the
// registration is what makes it appear in the line -- nothing is reported that was not
// declared, so a typo in a metric name is a missing column rather than a silent zero.
//
// WHY THESE ARE NOT RSS/HEAP NUMBERS
// ----------------------------------
// There is no allocator and no per-service memory accounting at this layer, so a "memory"
// column would be invented. Counters of work, and a queue depth, are what this layer can
// honestly measure -- and queue depth is the number that predicts a stall.
//
// REGISTRY IS FIXED-SIZE AND REFUSES
// ----------------------------------
// Sixteen metrics per service. A service that needs more has a design problem upstream; the
// failure here is a refusal (E_NOROOM) at registration, which is visible at start-up, rather
// than a metric that quietly stops updating at the sixteenth.

import common.err.err;
import common.fmt.fmt;

let MET_MAX: i64 = 16;

let MET_CALLS: i64 = 0;
let MET_ERRORS: i64 = 1;
let MET_UPTIME: i64 = 2;
let MET_QUEUE: i64 = 3;

let MK_COUNTER: i64 = 0;          // monotonic; only ever added to
let MK_GAUGE: i64 = 1;            // set to a value

struct Metric {
    id: i64,
    name: u8[..16] = [0; 16],
    name_len: i64,
    kind: i64,
    value: i64,
    active: bool,
}

struct Metrics {
    slots: Metric[..16] = [Metric { .. }; 16],
    count: i64,
    next_id: i64,
}

// Keep the name table short but stable: these four tokens are what every health line prints,
// and a log parser somewhere will key on them.
let MET_NAMES: const u8[:] = "calls errors uptime_ms queue";

fn met_new() -> Metrics {
    var m: Metrics = Metrics { slots: [], count: 0, next_id: 0 };
    var i: i64 = 0;
    while i < MET_MAX {
        m.slots[i] = Metric { id: 0, name: met_zero_name(), name_len: 0, kind: MK_GAUGE, value: 0, active: false };
        i = i + 1;
    }
    m.count = 0;
    m.next_id = 1;
    return m;
}

fn met_zero_name() -> u8[..16] {
    var n: u8[..16] = [0; 16];
    var i: i64 = 0;
    while i < 16 { n[i] = 0; i = i + 1; }
    return n;
}

fn met_standard_name(which: i64) -> const u8[:] {
    if which == MET_CALLS { return "calls"; }
    if which == MET_ERRORS { return "errors"; }
    if which == MET_UPTIME { return "uptime_ms"; }
    if which == MET_QUEUE { return "queue"; }
    return "";
}

// Register the four standard metrics. Returns CODE_OK, or E_NOROOM if the table is somehow
// too small -- which cannot happen with MET_MAX == 16 and four metrics, and is checked anyway
// because "cannot happen" is how a fixed table gets resized later without anyone noticing.
fn met_standard(m: Metrics&, now_ms: i64) -> i64 {
    var i: i64 = 0;
    while i < 4 {
        var kind = MK_COUNTER;
        if i == MET_UPTIME || i == MET_QUEUE { kind = MK_GAUGE; }
        let code = met_register(m, met_standard_name(i), kind);
        if code != CODE_OK { return code; }
        i = i + 1;
    }
    met_set(m, MET_UPTIME, now_ms);      // uptime is reported as "since", see met_uptime
    met_set(m, MET_QUEUE, 0);
    return CODE_OK;
}

// Register a named metric. Returns the id, or -1 when full or the name is empty/too long.
// A duplicate name is refused with -1 as well: two metrics sharing a name is a report where
// one column overwrites the other, which is worse than a refusal at start-up.
fn met_register(m: Metrics&, name: const u8[:], kind: i64) -> i64 {
    if name.len == 0 || name.len > 15 { return -1; }
    var slot: i64 = -1;
    var i: i64 = 0;
    while i < MET_MAX {
        if m.slots[i].active && met_name_eq(m.slots[i], name) { return -1; }
        if !m.slots[i].active && slot < 0 { slot = i; }
        i = i + 1;
    }
    if slot < 0 { return -1; }

    var mm: Metric = Metric { id: 0, name: [0; 16], name_len: 0, kind: 0, value: 0, active: false };
    mm.id = m.next_id;
    m.next_id = m.next_id + 1;
    mm.name = met_zero_name();
    var k: i64 = 0;
    while k < name.len {
        mm.name[k] = name[k];
        k = k + 1;
    }
    mm.name_len = name.len;
    mm.kind = kind;
    mm.value = 0;
    mm.active = true;
    m.slots[slot] = mm;
    m.count = m.count + 1;
    return mm.id;
}

fn met_name_eq(a: Metric&, name: const u8[:]) -> bool {
    if a.name_len != name.len { return false; }
    var i: i64 = 0;
    while i < name.len {
        if a.name[i] != name[i] { return false; }
        i = i + 1;
    }
    return true;
}

// ---------------------------------------------------------------------------
// Updating
// ---------------------------------------------------------------------------

// Count one call. Returns the new value, or -1 for an unknown id.
fn met_call(m: Metrics&, id: i64) -> i64 {
    return met_bump(m, id, 1);
}

// Count one errored call. Also bumps `calls`: an error is a call that failed, and a health
// line where errors > calls is a line that will be distrusted on sight.
fn met_error(m: Metrics&, id_errors: i64, id_calls: i64) -> i64 {
    let _ = met_bump(m, id_calls, 1);
    return met_bump(m, id_errors, 1);
}

fn met_bump(m: Metrics&, id: i64, n: i64) -> i64 {
    let slot = met_slot_of(m, id);
    if slot < 0 { return -1; }
    if m.slots[slot].kind != MK_COUNTER { return -1; }    // a gauge is set, not added
    if n < 0 { return -1; }
    m.slots[slot].value = m.slots[slot].value + n;
    return m.slots[slot].value;
}

fn met_set(m: Metrics&, id: i64, v: i64) -> i64 {
    let slot = met_slot_of(m, id);
    if slot < 0 { return -1; }
    if m.slots[slot].kind != MK_GAUGE { return -1; }      // a counter is never set backwards
    m.slots[slot].value = v;
    return v;
}

fn met_get(m: Metrics&, id: i64) -> i64, bool {
    let slot = met_slot_of(m, id);
    if slot < 0 { return 0, false; }
    return m.slots[slot].value, true;
}

// Uptime as a duration, given "now". The metric stores the start time, not a value that would
// need a tick to stay true: a service that stops ticking must not report a frozen uptime.
fn met_uptime(m: Metrics&, now_ms: i64) -> i64, bool {
    let start, ok = met_get(m, met_id_of(m, "uptime_ms"));
    if !ok { return 0, false; }
    if now_ms < start { return 0, true; }
    return now_ms - start, true;
}

// ---------------------------------------------------------------------------
// Reporting
// ---------------------------------------------------------------------------

// "calls=1204 errors=3 uptime_ms=45000 queue=0", in registration order, standard four first.
// The watchdog logs this verbatim; it is the line that ends up in a support bundle.
fn met_render(m: Metrics&, out: u8[>..]&, cap: i64) -> bool {
    var first = true;
    var i: i64 = 0;
    while i < MET_MAX {
        if m.slots[i].active {
            if !first { if !append_char(out, cap, ' ') { return false; } }
            var k: i64 = 0;
            while k < m.slots[i].name_len {
                if !append_char(out, cap, m.slots[i].name[k]) { return false; }
                k = k + 1;
            }
            if !append_char(out, cap, '=') { return false; }
            if !append_int(out, cap, m.slots[i].value) { return false; }
            first = false;
        }
        i = i + 1;
    }
    return true;
}

// A watchdog decision: is this service healthy by its own numbers?
//
// Deliberately simple -- errors greater than zero does NOT mean unhealthy, because a service
// that handled a refused request is working. The one condition that is always bad is a queue
// that has not drained, which the caller expresses by passing the last known depth.
fn met_looks_stuck(m: Metrics&, queue_stuck: bool) -> bool {
    if queue_stuck { return true; }
    let _, ok = met_get(m, met_id_of(m, "calls"));
    return !ok;                 // a service with no call metric was never registered
}

// ---------------------------------------------------------------------------
// Internals
// ---------------------------------------------------------------------------

fn met_slot_of(m: Metrics&, id: i64) -> i64 {
    var i: i64 = 0;
    while i < MET_MAX {
        if m.slots[i].active && m.slots[i].id == id { return i; }
        i = i + 1;
    }
    return -1;
}

// Look an id up by name, for the standard four whose ids the caller does not want to carry.
// Returns -1 when absent, and every caller must handle that: a metric that was never
// registered reads as -1 rather than as a comfortable zero.
fn met_id_of(m: Metrics&, name: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < MET_MAX {
        if m.slots[i].active && met_name_eq(m.slots[i], name) { return m.slots[i].id; }
        i = i + 1;
    }
    return -1;
}

// (metrics, counters, gauges) for the watchdog's own line.
fn met_totals(m: Metrics&) -> i64, i64, i64 {
    var counters: i64 = 0;
    var gauges: i64 = 0;
    var i: i64 = 0;
    while i < MET_MAX {
        if m.slots[i].active {
            if m.slots[i].kind == MK_COUNTER { counters = counters + 1; } else { gauges = gauges + 1; }
        }
        i = i + 1;
    }
    return m.count, counters, gauges;
}
