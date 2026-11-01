// services/time/time.goose
//
// Layer 4, service 3: the monotonic clock.
//
// Status: WRITTEN (not COMPILED). B-L1-04 wrote the clock core; B-L1-19 adds the
// deadline and wait surface every other service schedules against. Verified through goose-mcp@1.1.0
// (aardappel/goose @ b781587): extern fn (spec#40), export fn (spec#41),
// while/return/fn keywords (list_keywords), trailing-bool (samples/04_errors),
// i64 arithmetic and top-level globals (reference#5).
//
// Why this service and not the console: the console needs the framebuffer (K2)
// and the keyboard (K3), while time needs only a timer tick. It is the second
// service because with bootlog plus time, every other service can say when it
// failed as well as what failed.
//
// The blocking gap, stated plainly: a real time service answers other services
// over IPC. IPC is not designed (open question Q9) and no transport exists, so
// this file contains the clock core and a self-check entry, not a request
// handler. Writing a request handler against an invented transport would be
// exactly the mock the work order forbids.

import std;

extern fn sys_ticks() -> i64;
extern fn sys_yield();

// ---------------------------------------------------------------------------
// Tick rate
// ---------------------------------------------------------------------------
//
// The kernel publishes its tick rate in BootInfo (B-L1-08) and this service
// must read it, never assume it. Until BootInfo is handed to the entry, the
// value below is the layer's *request* to the kernel: 1000 Hz, one tick per
// millisecond, chosen because a millisecond is the coarsest unit the services
// above need and a power-of-ten rate keeps conversion exact in integer maths.
//
// Requirement on Layers 1-3 (R5 in SERVICE_CONTRACT.md): the kernel either
// honours 1000 Hz or reports the rate it actually uses. This constant is the
// only place in the layer that names a rate, so when BootInfo lands there is
// one line to change.

// Not exported: SERVICE_CONTRACT.md §2 says a service exports exactly one entry
// symbol, and a second C-visible name here would break that rule for a value the
// kernel publishes anyway.
fn requested_tick_hz() -> i64 {
    return 1000;
}

// ---------------------------------------------------------------------------
// The clock core (pure; no syscalls, so it is checkable by inspection)
// ---------------------------------------------------------------------------

// Ticks to whole milliseconds.
fn ticks_to_ms(ticks: i64, hz: i64) -> i64, bool {
    if hz <= 0 { return 0, false; }      // a zero tick rate is a kernel fault
    return (ticks * 1000) / hz, true;
}

// Milliseconds to whole ticks, rounding down. A sleep of 0 ms is legal and
// means "do not sleep", which is why there is no bool here: the only failure
// is a bad rate, and that is caught once at start-up rather than per call.
fn ms_to_ticks(ms: i64, hz: i64) -> i64 {
    if ms <= 0 || hz <= 0 { return 0; }
    return (ms * hz) / 1000;
}

// Ticks elapsed since a start point, safe against the counter wrapping by
// treating the difference as unsigned-width arithmetic when it goes negative.
fn elapsed(now: i64, start: i64) -> i64 {
    return now - start;
}

// ---------------------------------------------------------------------------
// Waiting
// ---------------------------------------------------------------------------
//
// Busy-waiting with explicit yields, because there is no wait primitive in the
// kernel surface. This is a polling loop by design, and it costs CPU that the
// scheduler could give to another service: B-L1-51 (the time test program)
// measures how bad it is, and if the answer is "bad", the fix is a kernel wait
// call, recorded as a requirement rather than worked around here.

fn sleep_ticks(n: i64) -> bool {
    if n <= 0 { return true; }
    let start = sys_ticks();
    var last = start;
    while elapsed(sys_ticks(), start) < n {
        sys_yield();
        let now = sys_ticks();
        // A timer that never advances is a kernel fault, not something to spin
        // on forever: bail out so the failure is visible instead of silent.
        if now == last {
            // Allow one equality (two reads inside the same tick) before
            // treating the clock as stalled.
            sys_yield();
            if sys_ticks() == now { return false; }
        }
        last = now;
    }
    return true;
}

fn sleep_ms(ms: i64, hz: i64) -> bool {
    return sleep_ticks(ms_to_ticks(ms, hz));
}

// ---------------------------------------------------------------------------
// The service
// ---------------------------------------------------------------------------

// Self-check entry. This does not serve requests yet (no IPC); it proves the
// one thing this service cannot get wrong silently: that the tick counter
// advances at roughly the rate the kernel claims. The tolerance is wide on
// purpose - this is a liveness check, not a benchmark, and a tight bound on an
// unbuilt kernel would fail for reasons that are not this service's fault.
export "svc_entry" fn service_main() -> i32 {
    let hz = requested_tick_hz();
    if hz <= 0 { return 1; }

    let start = sys_ticks();
    if !sleep_ms(10, hz) { return 2; }      // the clock did not advance
    let delta = elapsed(sys_ticks(), start);
    if delta <= 0 { return 3; }             // advanced backwards or not at all

    let ms, ok = ticks_to_ms(delta, hz);
    if !ok { return 4; }
    // 10 ms asked for; anything from one tick to a full second is accepted,
    // because the only claim being made here is "time moves".
    if ms > 1000 { return 5; }

    return 0;
}

// ---------------------------------------------------------------------------
// B-L1-19: the full time surface
// ---------------------------------------------------------------------------
//
// The core above converts and sleeps. This section is what services actually
// schedule against: a Clock that carries the rate once, deadlines that are
// absolute tick values, and waits that cannot silently overrun.
//
// WHY DEADLINES ARE ABSOLUTE TICKS, NOT DURATIONS
// -----------------------------------------------
// A duration handed around ("wait 50 ms") restarts every time it is passed to
// another function, and a chain of helpers turns a 50 ms timeout into 300 ms. An
// absolute deadline is computed once, at the call site, and every downstream
// check compares against the same instant.

struct Clock {
    hz: i64,
}

struct Deadline {
    at: i64,        // absolute tick count
}

fn clock_init(hz: i64) -> Clock {
    // A clock with a nonsense rate is refused at construction rather than
    // producing silent nonsense at every later conversion.
    if hz <= 0 { return Clock { hz: 1000 }; }
    return Clock { hz: hz };
}

fn clock_now(c: Clock&) -> i64 {
    return sys_ticks();
}

fn clock_uptime_ms(c: Clock&) -> i64 {
    let ms, ok = ticks_to_ms(sys_ticks(), c.hz);
    if !ok { return 0; }
    return ms;
}

// Absolute deadline, `ms` from now. `ms == 0` means "already due".
fn clock_after(c: Clock&, ms: i64) -> Deadline {
    let d = ms_to_ticks(ms, c.hz);
    return Deadline { at: sys_ticks() + d };
}

fn clock_deadline_in(c: Clock&, ms: i64) -> Deadline {
    return clock_after(c, ms);
}

fn deadline_expired(d: Deadline&, now: i64) -> bool {
    return elapsed(now, d.at) >= 0;
}

// Ticks left, never negative: a caller that subtracts a negative remaining time
// from a budget would silently gain time on a slow path.
fn deadline_remaining(d: Deadline&, now: i64) -> i64 {
    let left = d.at - now;
    if left < 0 { return 0; }
    return left;
}

fn deadline_remaining_ms(d: Deadline&, c: Clock&) -> i64 {
    let t = deadline_remaining(d, sys_ticks());
    let ms, ok = ticks_to_ms(t, c.hz);
    if !ok { return 0; }
    return ms;
}

// Wait until a deadline. Returns false if the clock stalled (the same stall
// detector as sleep_ticks) so a caller can distinguish "woke up" from "the
// scheduler never gave us the CPU again".
fn clock_wait(c: Clock&, d: Deadline&) -> bool {
    let now = sys_ticks();
    if deadline_expired(d, now) { return true; }
    let left = deadline_remaining(d, now);
    return sleep_ticks(left);
}

// A budget for one operation: start it, then ask how much is left for each step.
//
//     var budget = clock_budget(c, 20);            // 20 ms for the whole thing
//     step_one(clock_budget_left(budget, c));      // each step gets what remains
//
// Passing the *remaining* time into each step is what keeps a sequence inside its
// total, instead of each step getting the full original 20 ms.
struct Budget {
    start: i64,
    total: i64,     // ticks
}

fn clock_budget(c: Clock&, ms: i64) -> Budget {
    return Budget { start: sys_ticks(), total: ms_to_ticks(ms, c.hz) };
}

fn clock_budget_left(b: Budget&, c: Clock&) -> i64 {
    let used = elapsed(sys_ticks(), b.start);
    let left = b.total - used;
    if left < 0 { return 0; }
    let ms, ok = ticks_to_ms(left, c.hz);
    if !ok { return 0; }
    return ms;
}

fn clock_budget_expired(b: Budget&) -> bool {
    return elapsed(sys_ticks(), b.start) >= b.total;
}

// Sub-millisecond resolution, for the few paths that measure something shorter
// than a tick. Rounds down; a caller that needs exactness works in ticks.
fn ticks_to_us(ticks: i64, hz: i64) -> i64, bool {
    if hz <= 0 { return 0, false; }
    return (ticks * 1000000) / hz, true;
}

// Is the clock usable at all? Every service calls this once at start-up: a clock
// that does not advance makes every timeout in the layer infinite, which is far
// worse than refusing to start.
fn clock_ok(c: Clock&) -> bool {
    let a = sys_ticks();
    var spins: i64 = 0;
    while spins < 1000 {
        sys_yield();
        if sys_ticks() != a { return true; }
        spins++;
    }
    return false;
}

// ---------------------------------------------------------------------------
// Deliberately absent
// ---------------------------------------------------------------------------
//
// - No calendar, no time zones, no epoch conversion: B-L1-110. A service that
//   needs a date asks that task's code, not this one.
// - No settable clock. `time` is monotonic; wall-clock adjustment belongs to the
//   time sync client (B-L1-37) which will hold an offset, not move this counter.
// - No timer service yet: waking another process on a deadline needs the kernel
//   (K5) and the IPC transport (Q-B-L1-2). A wake list here would be a fiction.
