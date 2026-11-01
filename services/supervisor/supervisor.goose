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

struct ServiceEntry {
    name: u8[..32],       // inline, no pointer: the entry is self-contained
    id: i64,              // kernel process id once spawned; -1 until then
    state: i64,
    // Which service starts this one. -1 = no dependency (boot services).
    needs: i64,
    restarts: i64,        // how many times this run has been restarted
    last_beat_ms: i64,    // uptime when the last heartbeat arrived
    enabled: bool,        // a disabled service is never started
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

    table_len++;
    return table_len - 1, CODE_OK;
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
// Not declared as externs in this file yet: a declaration that cannot link would
// make the whole service unlinkable, and the shape above is a guess. It belongs in
// sys.goose the moment K6 fixes the spawn signature (requirement A1/A9 in
// BOUNDARIES.md). Until then the supervisor's table works, and the two calls that
// would act on it do not exist.
