// services/watchdog/watchdog.goose
//
// Layer 4, service 7: the health watchdog. Who has gone quiet, and who decides
// what happens next.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: struct with
// fixed-size fields and struct literals (reference#32, tutorial#9), fixed arrays
// `T[..k]` (stdlib#13), `while` and `if` chains (list_keywords), trailing-bool and
// trailing-code returns (samples/04_errors.goose), references `T&` for modification
// (reference#32 `fn tick(e: Entity&)`).
//
// WHAT THIS IS
// ------------
// A heartbeat table and a decision. Services call wd_beat with their handle; the
// watchdog asks "is anyone overdue?" and hands back the handle of whoever is. It
// does NOT restart anything: restarting is the supervisor's policy decision
// (B-L1-21), and a watchdog that also restarts would be a second authority over the
// same service -- two controllers, two opinions, one process.
//
// WHY THE DEADLINE IS ABSOLUTE AND STORED
// ---------------------------------------
// "Has it been 5 seconds?" needs a start time, and the naive version recomputes one
// on every check, which silently extends the deadline forever if the check is late.
// Each service stores the absolute uptime its next beat is due by; a beat pushes it
// forward, a check only compares.
//
// WHY MISSES ARE COUNTED, NOT JUST DETECTED
// -----------------------------------------
// One late beat is a scheduling hiccup, not a failure. Restarting on the first miss
// turns a busy machine into a restart storm. The watchdog tolerates `miss_allow`
// missed deadlines and reports only after that, which is also the number the health
// line (B-L1-124) quotes.

import common.err.err;

// ---------------------------------------------------------------------------
// Table
// ---------------------------------------------------------------------------

let WD_MAX: i64 = 32;          // mirrors the supervisor's MAX_SERVICES
let WD_NEVER: i64 = -1;        // deadline that has not been armed yet

struct Watch {
    handle: i64,        // opaque supervisor handle (B-L1-22); 0 = free slot
    period_ms: i64,     // how often a beat is expected
    deadline_ms: i64,   // absolute uptime this beat was due by
    grace_ms: i64,      // extra time before a miss counts
    miss_allow: i64,    // consecutive misses tolerated before reporting
    misses: i64,        // consecutive misses so far
    reported: bool,     // already escalated; do not report the same death twice
}

var watches: Watch[..32];

// ---------------------------------------------------------------------------
// Registration
// ---------------------------------------------------------------------------

// Start watching a handle. `period_ms` must be positive: a zero period would mean
// "beat constantly", which no service can satisfy and every watchdog would report.
fn wd_watch(handle: i64, period_ms: i64, grace_ms: i64, miss_allow: i64, now_ms: i64) -> i64 {
    if handle <= 0 { return E_INVAL; }
    if period_ms <= 0 || grace_ms < 0 || miss_allow < 0 { return E_INVAL; }
    if now_ms < 0 { return E_INVAL; }

    if wd_find(handle) >= 0 { return E_STATE; }   // already watched; re-arming is a bug

    var i: i64 = 0;
    while i < WD_MAX {
        if watches[i].handle == 0 {
            watches[i].handle = handle;
            watches[i].period_ms = period_ms;
            watches[i].deadline_ms = now_ms + period_ms + grace_ms;
            watches[i].grace_ms = grace_ms;
            watches[i].miss_allow = miss_allow;
            watches[i].misses = 0;
            watches[i].reported = false;
            return CODE_OK;
        }
        i++;
    }
    return E_NOROOM;
}

// Stop watching. Called on a clean stop, so a service that exited on purpose does
// not spend its retry budget being reported as dead.
fn wd_unwatch(handle: i64) -> i64 {
    let slot = wd_find(handle);
    if slot < 0 { return E_NOTFOUND; }
    wd_clear(slot);
    return CODE_OK;
}

fn wd_clear(slot: i64) {
    if slot >= 0 && slot < WD_MAX {
        watches[slot].handle = 0;
        watches[slot].period_ms = 0;
        watches[slot].deadline_ms = WD_NEVER;
        watches[slot].grace_ms = 0;
        watches[slot].miss_allow = 0;
        watches[slot].misses = 0;
        watches[slot].reported = false;
    }
}

fn wd_find(handle: i64) -> i64 {
    var i: i64 = 0;
    while i < WD_MAX {
        if watches[i].handle == handle { return i; }
        i++;
    }
    return -1;
}

// ---------------------------------------------------------------------------
// Beats and checks
// ---------------------------------------------------------------------------

// A beat. It also clears the miss count, because the question the count answers is
// "how long has it been silent", not "how often has it ever been late".
fn wd_beat(handle: i64, now_ms: i64) -> i64 {
    let slot = wd_find(handle);
    if slot < 0 { return E_NOTFOUND; }
    watches[slot].deadline_ms = now_ms + watches[slot].period_ms + watches[slot].grace_ms;
    watches[slot].misses = 0;
    watches[slot].reported = false;
    return CODE_OK;
}

// Check one entry. Returns (state, misses) where state is WD_FINE / WD_SILENT /
// WD_DEAD. Side effect: a NEW miss is counted and, once past miss_allow, the entry
// is marked reported so a second check does not escalate twice.
//
// A clock that went backwards (now < previous deadline) is not a miss: that is a
// wall-clock adjustment or a wrap, and counting it would report every service at
// once. The deadline is simply pushed forward from now.
let WD_FINE: i64 = 0;
let WD_SILENT: i64 = 1;    // late, still inside the allowance
let WD_DEAD: i64 = 2;      // past the allowance, and THIS check is the escalation
let WD_STILL_DEAD: i64 = 3; // already escalated; still dead, nothing to do about it
//
// The split between WD_DEAD and WD_STILL_DEAD is the whole "escalate once" rule made
// visible in the return value. Returning WD_DEAD on every later check (which this file did
// first) told the caller nothing about whether it had already acted, and wd_next_dead would
// hand back the same service forever -- a restart loop with extra steps.

fn wd_check_one(slot: i64, now_ms: i64) -> i64, i64 {
    if slot < 0 || slot >= WD_MAX { return WD_FINE, 0; }
    if watches[slot].handle == 0 { return WD_FINE, 0; }

    let due = watches[slot].deadline_ms;
    if now_ms < due { return WD_FINE, watches[slot].misses; }

    // How many whole periods late is it? Counting periods (rather than one miss per
    // check) means a check that runs rarely still reports the truth.
    let late = now_ms - due;
    let period = watches[slot].period_ms + watches[slot].grace_ms;
    if period <= 0 { return WD_FINE, watches[slot].misses; }
    let late_periods = (late / period) + 1;

    watches[slot].misses = watches[slot].misses + late_periods;
    // Push the deadline forward to the next expected beat so the same lateness is
    // not counted again on the next check.
    watches[slot].deadline_ms = now_ms + period;

    if watches[slot].misses <= watches[slot].miss_allow { return WD_SILENT, watches[slot].misses; }
    if watches[slot].reported { return WD_STILL_DEAD, watches[slot].misses; }
    watches[slot].reported = true;
    return WD_DEAD, watches[slot].misses;
}

// Scan for the first service that needs escalating. The supervisor's loop calls this
// once per tick; the handle comes back so the caller can pass it to sup_on_exit with
// exited_clean = false.
//
// One per call, deliberately: escalating several at once would restart a whole layer
// because one slow check batched them together, and the log would not say which one
// was first.
fn wd_next_dead(now_ms: i64) -> i64, i64 {
    var i: i64 = 0;
    while i < WD_MAX {
        if watches[i].handle != 0 {
            let state, misses = wd_check_one(i, now_ms);
            if state == WD_DEAD { return watches[i].handle, misses; }
        }
        i++;
    }
    return 0, E_NOTFOUND;
}

// The numbers a health line reports (B-L1-124).
fn wd_count(now_ms: i64) -> i64, i64, i64 {
    var healthy: i64 = 0;
    var bad: i64 = 0;
    var lateness: i64 = 0;      // total missed beats, the number that means "sluggish"
    var i: i64 = 0;
    while i < WD_MAX {
        if watches[i].handle != 0 {
            let s, misses = wd_check_one(i, now_ms);
            if s == WD_DEAD || s == WD_STILL_DEAD { bad++; } else { healthy++; }
            lateness = lateness + misses;
        }
        i++;
    }
    return healthy, bad, lateness;
}

// ---------------------------------------------------------------------------
// Deliberately absent
// ---------------------------------------------------------------------------
//
// - No kill. The watchdog reports; the supervisor decides and acts. A watchdog with
//   a kill call is a second scheduler.
// - No per-service threads. One check loop over 32 entries is cheaper than 32
//   wakeups, and Goose threads share nothing, so a per-service watchdog could not
//   even see the table it was watching.
// - No history beyond the current miss count: that is the audit service's job
//   (B-L1-41), and two histories would disagree.
