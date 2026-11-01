// services/supervisor/supervisor.goose
//
// Layer 4, service 6: the service table and its state machine. Who is running,
// what state it is in, and whether a transition is legal at all.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs with
// fixed-size string fields (tutorial#3, samples/03_strings.goose), fixed arrays
// (stdlib#13), extern/export fn (spec#40, spec#41), trailing-bool and trailing-code
// returns (samples/04_errors.goose), keywords (list_keywords).
//
// WHAT THIS FILE IS, AND WHAT IT IS NOT
// -------------------------------------
// It is the table and the rules: which states exist, which transitions are legal,
// who may move a service, and what happens on an illegal move (nothing, plus a
// record -- a supervisor that "fixes" a bad transition is a supervisor nobody can
// audit).
//
// It is NOT the process launcher. Starting a process needs the kernel (K6: a spawn
// call with an image, an address space and a priority), and that call does not
// exist. The start/stop points below are declared as the supervisor's *request* to
// the kernel, in the same way sys.goose declares the other six. This is
// interface-first work, which the work order allows explicitly (B-L1-07's note):
// an interface written against a documented contract is real work; a fake process
// would be a mock.
//
// B-L1-21 adds restart policy. This task is the table and the transitions only, so
// that "what states exist" is settled before "how many times may it crash".

import common.err.err;
import common.ring.ring;

// ---------------------------------------------------------------------------
// States
// ---------------------------------------------------------------------------

let ST_STOPPED: i64 = 0;      // not running, and not coming back on its own
let ST_STARTING: i64 = 1;     // spawned, has not reported ready
let ST_RUNNING: i64 = 2;      // reported ready
let ST_STOPPING: i64 = 3;     // asked to stop, still finishing
let ST_FAILED: i64 = 4;       // exited badly; policy decides what next
let ST_RESTARTING: i64 = 5;   // waiting out a backoff before another try

fn state_name(s: i64) -> const u8[:] {
    if s == ST_STOPPED { return "stopped"; }
    if s == ST_STARTING { return "starting"; }
    if s == ST_RUNNING { return "running"; }
    if s == ST_STOPPING { return "stopping"; }
    if s == ST_FAILED { return "failed"; }
    if s == ST_RESTARTING { return "restarting"; }
    return "unknown";
}

// ---------------------------------------------------------------------------
// The table
// ---------------------------------------------------------------------------

let NAME_MAX: i64 = 32;
let MAX_SERVICES: i64 = 32;

// B-L1-21: restart policy lives in the entry, not in a parallel array. A second
// array keyed by the same slot index would desync the moment anything moved
// entries, and the policy is a property of the service, not of the table.
let RP_NEVER: i64 = 0;       // never restart, however it exits
let RP_ON_FAIL: i64 = 1;     // restart only after an unclean exit
let RP_ALWAYS: i64 = 2;      // restart whatever happens, clean or not

struct ServiceEntry {
    name: u8[..32],       // inline, no pointer: the entry is self-contained
    id: i64,              // kernel process id once spawned; -1 until then
    state: i64,
    // Which service starts this one. -1 = no dependency (boot services).
    needs: i64,
    restarts: i64,        // how many times this run has been restarted
    last_beat_ms: i64,    // uptime when the last heartbeat arrived
    enabled: bool,        // a disabled service is never started
    // --- B-L1-21 ---
    policy: i64,          // RP_*
    max_restarts: i64,    // 0 = unlimited (capped by policy, not by count)
    base_ms: i64,         // first backoff step
    max_ms: i64,          // backoff ceiling; also the "quick crash" threshold
    // --- B-L1-22 ---
    gen: i64,             // bumped on every (re)assignment of this slot
}

var table: ServiceEntry[..32];
var table_len: i64 = 0;

// Register a service. Registration is start-up only: a table that changes while
// other services are running is a table with no reader/writer rule, and Goose has
// no locks (threads share nothing), so the safe design is "fill it, then read it".
fn sup_register(name: const u8[:], needs: i64, enabled: bool) -> i64, i64 {
    if table_len >= MAX_SERVICES { return -1, E_NOROOM; }
    if name.len == 0 || name.len >= NAME_MAX { return -1, E_INVAL; }
    if sup_find(name) >= 0 { return -1, E_STATE; }   // duplicate names are a bug

    var i: i64 = 0;
    while i < name.len {
        table[table_len].name[i] = name[i];
        i++;
    }
    table[table_len].name[i] = 0;

    table[table_len].id = -1;
    table[table_len].state = ST_STOPPED;
    table[table_len].needs = needs;
    table[table_len].restarts = 0;
    table[table_len].last_beat_ms = 0;
    table[table_len].enabled = enabled;
    // Default is RP_ON_FAIL with a 100 ms rising to 30 s: a service that crashes
    // is retried, a service that exits cleanly is not. RP_ALWAYS has to be asked
    // for, because restarting something that shut down on purpose is a loop.
    table[table_len].policy = RP_ON_FAIL;
    table[table_len].max_restarts = 0;
    table[table_len].base_ms = 100;
    table[table_len].max_ms = 30000;
    table[table_len].gen = 1;

    table_len++;
    return table_len - 1, CODE_OK;
}

// ---------------------------------------------------------------------------
// B-L1-22: names to handles
// ---------------------------------------------------------------------------
//
// Every inter-service call names a service. Naming it by slot index would let a
// caller act on whichever service happens to hold that slot later, which is the
// classic stale-reference bug with a security flavour: the caller thinks it is
// talking to the logger and is writing to the updater.
//
// A handle is (slot, generation) packed into one i64, with slot*4 leaving room for
// generations. A handle is only valid while the slot still holds the generation it
// was issued for. 0 is never a valid handle, so an uninitialised field cannot be
// mistaken for a real service.

let HANDLE_GEN_MAX: i64 = 65535;

fn sup_handle(slot: i64) -> i64 {
    if slot < 0 || slot >= table_len { return 0; }
    return (slot + 1) * HANDLE_GEN_MAX + table[slot].gen;
}

// Resolve a handle to a slot, or -1. This is the check that makes the handle worth
// having: a handle from a replaced service resolves to nothing instead of to the
// service that took its place.
fn sup_resolve(handle: i64) -> i64 {
    if handle <= 0 { return -1; }
    let gen = handle % HANDLE_GEN_MAX;
    let slot = (handle / HANDLE_GEN_MAX) - 1;
    if slot < 0 || slot >= table_len { return -1; }
    if table[slot].gen != gen { return -1; }
    return slot;
}

// Name by handle, for logging. An empty slice for a stale handle, never a guess.
fn sup_name_of(handle: i64) -> const u8[:] {
    let slot = sup_resolve(handle);
    if slot < 0 { return ""; }
    return entry_name_slice(slot);
}

// The stored name as a slice, stopping at the NUL. Bounded by the array length so a
// name that lost its terminator (a corruption this file cannot prevent) still ends.
fn entry_name_slice(slot: i64) -> const u8[:] {
    if slot < 0 || slot >= table_len { return ""; }
    // Sliced straight out of the table, never out of a local copy: a slice into a
    // fixed-size local would point at storage that is gone the moment this returns,
    // and returning it would be a dangling view. The table is static storage, so a
    // slice into it outlives the call.
    var n: i64 = 0;
    while n < NAME_MAX && table[slot].name[n] != 0 { n++; }
    return table[slot].name[..n];
}

// Look a name up and get a handle in one step -- the call every other service
// makes. Two returns because "not registered" and "registered but stale" are
// different answers and a caller that cannot tell them apart will retry forever.
fn sup_lookup(name: const u8[:]) -> i64, i64 {
    let slot = sup_find(name);
    if slot < 0 { return 0, E_NOENT; }
    return sup_handle(slot), CODE_OK;
}

// Free a stopped slot for reuse, bumping its generation so every handle issued to
// the previous occupant stops resolving. Refused while the service is anything but
// STOPPED: reusing a slot under a running service is the bug this guards.
fn sup_release(slot: i64) -> i64 {
    if slot < 0 || slot >= table_len { return E_INVAL; }
    if table[slot].state != ST_STOPPED { return E_STATE; }
    table[slot].gen = table[slot].gen + 1;
    // Clamped at the top of the range, not into it: a generation equal to
    // HANDLE_GEN_MAX would make (slot+1)*MAX + gen collide with the next slot's
    // handle, so the wrap has to happen one before that value.
    if table[slot].gen >= HANDLE_GEN_MAX { table[slot].gen = 1; }
    table[slot].id = -1;
    table[slot].restarts = 0;
    table[slot].last_beat_ms = 0;
    table[slot].needs = -1;
    table[slot].enabled = false;
    table[slot].policy = RP_ON_FAIL;
    table[slot].max_restarts = 0;
    table[slot].base_ms = 100;
    table[slot].max_ms = 30000;
    // The name is cleared byte by byte: a stale name in a released slot would make
    // sup_find match a service that is not there.
    var i: i64 = 0;
    while i < NAME_MAX {
        table[slot].name[i] = 0;
        i++;
    }
    return CODE_OK;
}

// Find by name. Linear and unoptimised: the table is 32 entries and lookups happen
// at start-up and on a heartbeat, not in a hot loop. A hash map here would be a
// data structure to debug for a saving nobody can measure.
fn sup_find(name: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < table_len {
        if entry_name_matches(i, name) { return i; }
        i++;
    }
    return -1;
}

fn entry_name_matches(slot: i64, name: const u8[:]) -> bool {
    // Fixed-size values copy on assignment (tutorial#7), so this is a real copy
    // of the name, not a reference that could be invalidated by a later write.
    let stored = table[slot].name;
    var i: i64 = 0;
    while i < name.len {
        if stored[i] != name[i] { return false; }
        i++;
    }
    // The stored name is NUL-terminated; a longer stored name must not match a
    // shorter query that happens to be its prefix.
    return stored[name.len] == 0;
}

// ---------------------------------------------------------------------------
// Legal transitions
// ---------------------------------------------------------------------------

// Is `to` reachable from `from`? The set is deliberately small. In particular:
// RUNNING -> RUNNING is not a transition (it is a heartbeat), and STOPPED ->
// RUNNING does not exist (a stopped service is started through STARTING, so the
// "did it come up" question always has an answer).
fn transition_legal(from: i64, to: i64) -> bool {
    if from == ST_STOPPED && to == ST_STARTING { return true; }
    if from == ST_STARTING && to == ST_RUNNING { return true; }
    if from == ST_STARTING && to == ST_FAILED { return true; }
    // STARTING -> STOPPING added at B-L1-21: a service that is still coming up can
    // be told to stop (it failed to become ready, or the operator changed their
    // mind). Without this edge there is no legal way out of STARTING except a
    // failure, so "stop" would have had to be spelled "crash".
    if from == ST_STARTING && to == ST_STOPPING { return true; }
    if from == ST_RUNNING && to == ST_STOPPING { return true; }
    if from == ST_RUNNING && to == ST_FAILED { return true; }
    if from == ST_STOPPING && to == ST_STOPPED { return true; }
    if from == ST_STOPPING && to == ST_FAILED { return true; }
    if from == ST_FAILED && to == ST_RESTARTING { return true; }
    if from == ST_FAILED && to == ST_STOPPED { return true; }
    if from == ST_RESTARTING && to == ST_STARTING { return true; }
    if from == ST_RESTARTING && to == ST_STOPPED { return true; }
    return false;
}

// Move a service. An illegal move changes nothing and returns E_STATE; the caller
// logs it. Silently accepting junk transitions is how a supervisor ends up
// believing a dead service is running.
fn sup_set_state(slot: i64, to: i64) -> i64 {
    if slot < 0 || slot >= table_len { return E_INVAL; }
    let from = table[slot].state;
    if !transition_legal(from, to) { return E_STATE; }
    table[slot].state = to;
    // Note for B-L1-21: the restart counter is NOT cleared here. A service that
    // fails during STARTING has not earned a clean slate, and clearing on every
    // transition would let a crash loop restart forever.
    return CODE_OK;
}

fn sup_state(slot: i64) -> i64 {
    if slot < 0 || slot >= table_len { return -1; }
    return table[slot].state;
}

fn sup_is_running(slot: i64) -> bool {
    return sup_state(slot) == ST_RUNNING;
}

// ---------------------------------------------------------------------------
// Heartbeats
// ---------------------------------------------------------------------------

fn sup_beat(slot: i64, uptime_ms: i64) -> i64 {
    if slot < 0 || slot >= table_len { return E_INVAL; }
    if table[slot].state != ST_RUNNING && table[slot].state != ST_STARTING {
        // A heartbeat from a service that is not up is a state disagreement worth
        // surfacing, not a value to store.
        return E_STATE;
    }
    table[slot].last_beat_ms = uptime_ms;
    return CODE_OK;
}

fn sup_ms_since_beat(slot: i64, uptime_ms: i64) -> i64 {
    if slot < 0 || slot >= table_len { return -1; }
    let last = table[slot].last_beat_ms;
    if uptime_ms < last { return 0; }    // clock moved backwards: treat as fresh
    return uptime_ms - last;
}

// ---------------------------------------------------------------------------
// Dependency order
// ---------------------------------------------------------------------------
//
// Registration order is not boot order. A service may be registered before the
// thing it needs, and refusing that would force the manifest to be written in
// exactly one order. Instead: is every dependency of `slot` running?
fn sup_can_start(slot: i64) -> bool, i64 {
    if slot < 0 || slot >= table_len { return false, E_INVAL; }
    if !table[slot].enabled { return false, E_STATE; }
    let needs = table[slot].needs;
    if needs < 0 { return true, CODE_OK; }          // boot service
    if needs >= table_len { return false, E_INVAL; } // bad dependency index
    if needs == slot { return false, E_STATE; }      // cannot need itself
    if sup_is_running(needs) { return true, CODE_OK; }
    return false, E_STATE;                           // dependency not up yet
}

// ---------------------------------------------------------------------------
// What the kernel must provide (request, not fact)
// ---------------------------------------------------------------------------
//
//   extern fn sys_spawn(image: u64, len: i64, priority: i64) -> i64;
//   extern fn sys_kill(pid: i64) -> i32;
//
// ---------------------------------------------------------------------------
// B-L1-21: restart policy
// ---------------------------------------------------------------------------
//
// The question this answers: the supervisor has just been told a service exited.
// What now? Three policies (RP_NEVER / RP_ON_FAIL / RP_ALWAYS) and one backoff.
//
// WHY THE BACKOFF IS EXPONENTIAL AND CAPPED
// -----------------------------------------
// A flat retry delay turns a service that crashes on start-up into a spin loop:
// it burns a core and floods the log with the same failure, and the log is what
// someone reads to find the cause. Doubling from base_ms to max_ms keeps early
// retries fast (a transient failure recovers in a fraction of a second) and later
// retries slow (a broken service stops competing with the services that work).

let RT_LEAVE: i64 = 0;        // no restart; the exit was deliberate
let RT_GIVE_UP: i64 = 1;      // no restart; policy says it has failed for good
let RT_NOW: i64 = 2;          // restart immediately, no wait
let RT_AFTER: i64 = 3;        // restart after the returned delay

fn sup_set_policy(slot: i64, policy: i64, max_restarts: i64, base_ms: i64, max_ms: i64) -> i64 {
    if slot < 0 || slot >= table_len { return E_INVAL; }
    if policy != RP_NEVER && policy != RP_ON_FAIL && policy != RP_ALWAYS { return E_INVAL; }
    if base_ms <= 0 || max_ms < base_ms { return E_INVAL; }
    if max_restarts < 0 { return E_INVAL; }
    table[slot].policy = policy;
    table[slot].max_restarts = max_restarts;
    table[slot].base_ms = base_ms;
    table[slot].max_ms = max_ms;
    return CODE_OK;
}

// Delay before attempt number `attempt` (0 = the first restart). Doubles each
// time, capped at max_ms. Written as a loop rather than a shift because the shift
// operators are not among the forms verified against the Goose docs, and an
// unverified operator in the backoff is a bug that only appears under load.
//
// Overflow: `attempt` is bounded by max_restarts (or by the cap) before it gets
// anywhere near i64, and the loop stops the moment it reaches max_ms, so the
// multiply can never run away.
fn sup_backoff_ms(slot: i64, attempt: i64) -> i64 {
    if slot < 0 || slot >= table_len { return 0; }
    let base = table[slot].base_ms;
    let cap = table[slot].max_ms;
    var d = base;
    var i: i64 = 0;
    while i < attempt {
        if d >= cap { return cap; }
        d = d * 2;
        i++;
    }
    if d > cap { return cap; }
    return d;
}

// The decision, with no side effects, so it can be replayed and tested
// (B-L1-52) without a supervisor, a clock or a process.
//
// Returns (decision, delay_ms). `exited_clean` is the exit status's verdict, not
// the caller's opinion: a signal death is not clean.
fn sup_decide(slot: i64, exited_clean: bool, uptime_ms: i64) -> i64, i64 {
    if slot < 0 || slot >= table_len { return RT_GIVE_UP, 0; }
    let policy = table[slot].policy;

    // A service that stayed up earns a clean slate: 30 s of uptime is a working
    // service that later failed, not a crash loop, and counting both the same
    // would exhaust the retry budget of anything that fails once a week.
    var attempts = table[slot].restarts;
    if uptime_ms >= table[slot].max_ms { attempts = 0; }

    if exited_clean {
        // Clean exit means the service chose to stop. Only ALWAYS overrides that,
        // and it restarts at once: a clean stop has no crash to back off from.
        if policy == RP_ALWAYS { return RT_NOW, 0; }
        return RT_LEAVE, 0;
    }

    if policy == RP_NEVER { return RT_GIVE_UP, 0; }
    // Always restarts anyway; on-fail restarts because the exit was unclean.
    let limit = table[slot].max_restarts;
    if limit > 0 && attempts >= limit { return RT_GIVE_UP, 0; }
    return RT_AFTER, sup_backoff_ms(slot, attempts);
}

// Apply the decision to the table. Two deliberate choices here:
//
// 1. A clean exit walks RUNNING -> STOPPING -> STOPPED rather than jumping. The
//    jump is not a legal transition (B-L1-20 keeps STOPPED reachable only through
//    STOPPING), and widening the state machine to suit this one caller would cost
//    the property that "every stop was observed". The intermediate state is real:
//    the exit has been seen and the entry is being finalised.
// 2. RT_GIVE_UP leaves the service in FAILED, not STOPPED. "Stopped" reads as a
//    decision that went well; a service that crashed out of its retry budget must
//    stay visible as failed, which is what the health line and the audit record
//    (B-L1-41) report on.
//
// Returns (decision, delay_ms) exactly as decided, so the caller knows what it
// owes the kernel: RT_AFTER means "call sup_set_state(STARTING) after delay_ms".
fn sup_on_exit(slot: i64, exited_clean: bool, uptime_ms: i64) -> i64, i64 {
    let decision, delay = sup_decide(slot, exited_clean, uptime_ms);
    if slot < 0 || slot >= table_len { return decision, delay; }

    if uptime_ms >= table[slot].max_ms { table[slot].restarts = 0; }

    if decision == RT_LEAVE {
        sup_walk_stopped(slot);
        return decision, 0;
    }
    if decision == RT_NOW {
        // A clean stop under RP_ALWAYS: the run was healthy, so it costs nothing.
        // The entry goes back to STOPPED and RT_NOW tells the caller to spawn; the
        // caller then records STARTING through the gate like every other start.
        // Nothing is written to `state` directly here -- that would be the
        // "record before acting" bug the state machine exists to prevent.
        table[slot].restarts = 0;
        sup_walk_stopped(slot);
        return decision, 0;
    }
    if decision == RT_AFTER {
        table[slot].restarts = table[slot].restarts + 1;
        sup_set_state(slot, ST_FAILED);
        sup_set_state(slot, ST_RESTARTING);
        return decision, delay;
    }
    // RT_GIVE_UP
    sup_set_state(slot, ST_FAILED);
    return decision, 0;
}

// How a service that is stuck in RESTARTING gets back in: legal, and the only
// entry point to STARTING from there. Separate from sup_on_exit so the caller can
// release the entry if the restart is cancelled while waiting out the backoff.
// Bring an entry to STOPPED through legal moves only. A RUNNING entry has to pass
// through STOPPING (the machine does not allow the jump); a FAILED one goes
// straight to STOPPED, which is legal and is how "stop retrying this" ends.
fn sup_walk_stopped(slot: i64) -> i64 {
    if slot < 0 || slot >= table_len { return E_INVAL; }
    let s = table[slot].state;
    if s == ST_STOPPED { return CODE_OK; }
    if s == ST_RUNNING || s == ST_STARTING {
        if sup_set_state(slot, ST_STOPPING) != CODE_OK { return E_STATE; }
        return sup_set_state(slot, ST_STOPPED);
    }
    if s == ST_FAILED || s == ST_RESTARTING { return sup_set_state(slot, ST_STOPPED); }
    return E_STATE;
}

fn sup_restart_ready(slot: i64) -> i64 {
    if slot < 0 || slot >= table_len { return E_INVAL; }
    if table[slot].state != ST_RESTARTING { return E_STATE; }
    return sup_set_state(slot, ST_STARTING);
}
//
// Not declared as externs in this file yet: a declaration that cannot link would
// make the whole service unlinkable, and the shape above is a guess. It belongs in
// sys.goose the moment K6 fixes the spawn signature (requirement A1/A9 in
// BOUNDARIES.md). Until then the supervisor's table works, and the two calls that
// would act on it do not exist.
