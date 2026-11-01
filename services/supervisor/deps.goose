// services/supervisor/deps.goose
//
// B-L1-109 — Supervisor dependency ordering: start and stop in the B-L1-64 graph order.
//
// Status: WRITTEN (not COMPILED, not RUN).
//
// WHAT THIS FILE ADDS TO bootorder.goose
// --------------------------------------
// bootorder.goose is the *table*: ids, dependency masks, which failures are fatal, and the
// static order. It answers questions ("is this ready?") but keeps no state.
//
// This file is the *runner*: the four facts a supervisor actually holds -- running, failed,
// stopped, and how far through the order it has got -- plus the two transitions that matter
// (start one, fail one) and the stop path, which must run the order backwards.
//
// WHY THE RUNNER KEEPS A MASK AND NOT A LIST
// ------------------------------------------
// The graph is a bitmask table. A mask makes "all dependencies running" a single AND, cannot
// hold a duplicate, and cannot hold an id the table does not have. A list would need the same
// three operations with more ways to get them wrong.
//
// THE THREE HONEST OUTCOMES OF A START ATTEMPT
// --------------------------------------------
//   1. started            -- dependencies running, id marked running
//   2. waiting            -- dependencies not ready (E_BUSY); the caller should retry after
//                            the services it is waiting on have reported
//   3. impossible         -- a dependency FAILED and cannot recover in this boot (E_STATE);
//                            retrying forever turns a dead service into a hung supervisor
// Outcome 3 is the whole reason this runner tracks `failed` at all: without it, "not ready
// yet" and "never going to be ready" look identical and the boot hangs with no line saying
// which service is missing.

import common.err.err;
import common.fmt.fmt;
import supervisor.bootorder;

let DEP_MAX: i64 = 24;

struct DepRunner {
    running: i64,        // mask of services RUNNING
    failed: i64,         // mask of services that failed and cascaded
    stopped: i64,        // mask of services deliberately stopped
    started_count: i64,
    failed_count: i64,
    started: bool,
}

fn deps_new() -> DepRunner {
    return DepRunner { running: 0, failed: 0, stopped: 0, started_count: 0, failed_count: 0, started: false };
}

// ---------------------------------------------------------------------------
// Start
// ---------------------------------------------------------------------------

// Walk the order and start the first service whose dependencies are all running.
// Returns (id, code): id 0 with CODE_OK means "nothing ready right now, try again";
// id 0 with E_STATE means "no service can ever become ready" (a dependency failed);
// id 0 with E_STOPPED-ish CODE_OK when the whole order is done -- callers distinguish
// "done" from "waiting" with deps_complete().
fn deps_step(r: DepRunner&) -> i64, i64 {
    var pos: i64 = 1;
    var waiting: bool = false;
    while pos <= bo_count() {
        let id = bo_at(pos);
        if id != 0 && (r.running & (1 << id)) == 0 && (r.failed & (1 << id)) == 0 {
            if (r.failed & bo_needs(id)) != 0 {
                // A dependency has already failed. If that dependency was fatal the cascade
                // has marked us failed too and we never get here; reaching this line means a
                // non-fatal dependency is down, which is a degradation, not a dead end.
                waiting = true;
            } else if bo_ready(id, r.running) {
                r.running = r.running | (1 << id);
                r.started_count = r.started_count + 1;
                r.started = true;
                return id, CODE_OK;
            } else {
                waiting = true;
            }
        }
        pos++;
    }

    if deps_complete(r) { return 0, CODE_OK; }
    if waiting { return 0, E_BUSY; }
    return 0, E_STATE;
}

// Everything that will ever start, has.
fn deps_complete(r: DepRunner&) -> bool {
    let live = ~(r.failed | r.stopped);
    var pos: i64 = 1;
    while pos <= bo_count() {
        let id = bo_at(pos);
        if id != 0 && (live & (1 << id)) != 0 && (r.running & (1 << id)) == 0 { return false; }
        pos++;
    }
    return true;
}

fn deps_is_running(r: DepRunner&, id: i64) -> bool {
    return (r.running & (1 << id)) != 0;
}

fn deps_is_failed(r: DepRunner&, id: i64) -> bool {
    return (r.failed & (1 << id)) != 0;
}

// ---------------------------------------------------------------------------
// Failure
// ---------------------------------------------------------------------------

// Record a failure. Returns (cascade_mask, code): the mask is every service this failure
// took down, including the failing one.
//
// A failed service is removed from `running` first: the cascade computation asks "who needs
// this id", and a service that is still marked running would keep its dependents startable.
fn deps_fail(r: DepRunner&, id: i64) -> i64, i64 {
    if id < 1 || id > bo_count() { return 0, E_INVAL; }
    if (r.running & (1 << id)) == 0 && (r.failed & (1 << id)) != 0 { return 0, E_STATE; }

    r.running = r.running & ~(1 << id);
    let cascade = bo_cascade(id);
    r.failed = r.failed | cascade;
    r.running = r.running & ~cascade;
    r.failed_count = r.failed_count + 1;
    return cascade, CODE_OK;
}

// A service that failed and was restarted by the supervisor's policy: clear the bit so the
// order can start it again. Only for a service with no failed dependencies -- otherwise the
// restart is a loop that fails at the same assertion every time.
fn deps_retry(r: DepRunner&, id: i64) -> bool {
    if (r.failed & (1 << id)) == 0 { return false; }
    if (r.failed & bo_needs(id)) != 0 { return false; }
    r.failed = r.failed & ~(1 << id);
    return true;
}

// ---------------------------------------------------------------------------
// Stop
// ---------------------------------------------------------------------------

// Fill `out` with the ids to stop, in reverse start order, and mark them stopped.
// Returns the count. Reverse order is not a preference: stopping a dependency before its
// dependents hands them errors they have no handler for, and those errors land in the log
// as failures rather than as shutdowns.
fn deps_stop_plan(r: DepRunner&, out: i64[..24]&, cap: i64) -> i64 {
    var n: i64 = 0;
    var pos = bo_count();
    while pos >= 1 {
        let id = bo_at(pos);
        if id != 0 && (r.running & (1 << id)) != 0 {
            if n < cap && n < DEP_MAX {
                out[n] = id;
                n++;
            }
            r.running = r.running & ~(1 << id);
            r.stopped = r.stopped | (1 << id);
        }
        pos--;
    }
    return n;
}

// ---------------------------------------------------------------------------
// Explaining a wait
// ---------------------------------------------------------------------------

// Render "waiting for netcfg, dns" into the caller's buffer. The supervisor's health line
// uses this instead of "not ready": a boot that says which service it is waiting on is a
// boot someone can fix from the log alone.
fn deps_wait_reason(r: DepRunner&, id: i64, out: u8[>..]&, cap: i64) -> bool {
    let needs = bo_needs(id);
    if needs == 0 { return fmt.append_str(out, cap, "no dependencies"); }
    if !fmt.append_str(out, cap, "waiting for ") { return false; }

    var first = true;
    var bit: i64 = 1;
    while bit <= bo_count() {
        if (needs & (1 << bit)) != 0 && (r.running & (1 << bit)) == 0 {
            if !first { if !fmt.append_str(out, cap, ", ") { return false; } }
            if !bo_name(bit, out, cap) { return false; }
            first = false;
        }
        bit++;
    }
    if first { return fmt.append_str(out, cap, "nothing (ready)"); }
    return true;
}

// The health line: how far the boot got, in the two numbers that decide whether the machine
// is usable. "started 12/22 failed 1" tells a reader more than "degraded".
fn deps_health(r: DepRunner&, out: u8[>..]&, cap: i64) -> bool {
    if !fmt.append_str(out, cap, "started ") { return false; }
    if !fmt.append_int(out, cap, r.started_count) { return false; }
    if !fmt.append_str(out, cap, "/") { return false; }
    if !fmt.append_int(out, cap, bo_count()) { return false; }
    if !fmt.append_str(out, cap, " failed ") { return false; }
    return fmt.append_int(out, cap, r.failed_count);
}
