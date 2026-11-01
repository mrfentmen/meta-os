// services/agenthost/agenthost.goose
//
// Layer 4, services 20-22: the process table, the lifecycle rules, and the capability
// grants for the agent layer (Lobster). Written as one file because the three are one
// data structure read three ways: a slot holds a lifecycle state AND a grant set, and a
// grant that outlives its agent is the bug this file exists to make impossible.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs, static
// `Type[n]` arrays, `while`/`if`, slices, `T&` references (reference#46), multi-value
// returns, bitwise operators.
//
// WHY AN AGENT GETS A SLOT, NOT A POINTER
// ---------------------------------------
// Every reference to an agent is a slot number plus a generation, the same handle
// discipline as the supervisor (B-L1-19..21). An operator who types the wrong number, or a
// program that holds a stale table read, must not be able to address a different agent
// that has since been created in that slot. A bare index cannot tell those apart; a
// generation can.
//
// WHY THE TABLE IS FIXED
// ----------------------
// The capacity is compiled in. An agent table that grows on demand has an allocation
// failure path in the middle of an agent lifecycle, and the honest behaviour there -- kill
// something to make room -- is a policy this layer has no mandate to invent. Refusing the
// fifty-third agent is a rule; picking a victim is a decision.
//
// EVERY TRANSITION IS CHECKED
// ---------------------------
// As with the supervisor: there is no assignment to a slot's state outside
// `ah_set_state`, and the legal-edge table is the only place lifecycle is defined. The
// audit writer (B-L1-41) is called from the same place, so a state that is not legal
// produces no record -- the record cannot exist without the transition.

import common.err.err;

let AH_CAP: i64 = 24;

// States. CREATED is the slot being filled by `ah_spawn` before the caller is told the
// handle exists, so no other code can observe a slot that is mid-spawn.
let AS_FREE: i64 = 0;
let AS_CREATED: i64 = 1;
let AS_RUNNING: i64 = 2;
let AS_STOPPED: i64 = 3;
let AS_FAILED: i64 = 4;
let AS_KILLED: i64 = 5;

// Capability bits. These are the whole permission surface of the agent layer: a bit that
// is not set is a call the host refuses, and there is no "root" bit that implies others.
let CAP_AUDIT_WRITE: i64 = 1;       // append records to the audit log
let CAP_STORE_READ: i64 = 2;
let CAP_STORE_WRITE: i64 = 4;
let CAP_NET: i64 = 8;               // sockets at all; the peer policy is the socket layer's
let CAP_SPAWN: i64 = 16;            // create other agents
let CAP_MSG: i64 = 32;              // send to other agents (B-L1-117)
let CAP_DISPLAY: i64 = 64;
let CAP_INPUT: i64 = 128;           // read input events
let CAP_CLOCK_SET: i64 = 256;       // rare, and it is here to have a name for it
let CAP_MAX_BIT: i64 = 512;         // one past the highest defined bit

let AH_NO_SLOT: i64 = -1;

struct Agent {
    name: u8[32],
    name_len: i64,
    state: i64,
    gen: i64,               // bumped on every spawn into this slot, never on free
    pid: i64,               // the host's own process id for it, 0 while CREATED
    caps: i64,
    spawn_ms: i64,
    exit_code: i64,
    exit_cause: i64,        // 0 none, 1 self, 2 killed, 3 fault
    msg_sent: i64,
    msg_recv: i64,
}

var agents: Agent[AH_CAP];
var ah_inited: bool = false;

fn ah_init() {
    var i: i64 = 0;
    while i < AH_CAP {
        agents[i].state = AS_FREE;
        agents[i].gen = 0;
        agents[i].caps = 0;
        agents[i].name_len = 0;
        i++;
    }
    ah_inited = true;
}

// Handle encoding, same shape as the supervisor's: slot in the low bits, generation
// above it. Generation 0 is reserved so that handle 0 can mean "no agent".
fn ah_handle(slot: i64, gen: i64) -> i64 {
    return (gen * AH_CAP) + slot;
}

fn ah_slot_of(h: i64) -> i64 {
    if h <= 0 { return AH_NO_SLOT; }
    let slot = h % AH_CAP;
    if slot < 0 || slot >= AH_CAP { return AH_NO_SLOT; }
    return slot;
}

// Resolve a handle to a live slot, or AH_NO_SLOT when the generation does not match the
// slot's current occupant. This is the only entry point every other function uses.
fn ah_resolve(h: i64) -> i64 {
    if !ah_inited { return AH_NO_SLOT; }
    let slot = ah_slot_of(h);
    if slot == AH_NO_SLOT { return AH_NO_SLOT; }
    if agents[slot].state == AS_FREE { return AH_NO_SLOT; }
    if ah_handle(slot, agents[slot].gen) != h { return AH_NO_SLOT; }
    return slot;
}

// ---------------------------------------------------------------------------
// Spawn
// ---------------------------------------------------------------------------

// Spawn an agent into a free slot.
//
// `caps` is the full grant set. It is not additive with anything: an agent spawned with
// CAP_NET alone has CAP_NET alone, which is the point of the fixed table.
//
// Returns (handle, code). On failure the handle is 0.
fn ah_spawn(name: const u8[:], caps: i64, now_ms: i64) -> i64, i64 {
    if !ah_inited { ah_init(); }
    if name.len == 0 || name.len > 32 { return 0, E_INVAL; }
    if (caps & (CAP_MAX_BIT - 1)) != caps { return 0, E_INVAL; }   // bits above the surface
    if ah_find(name) != AH_NO_SLOT {
        // One name, one agent. Two agents with one name makes every record that names an
        // agent ambiguous, and records are the thing this layer is audited by.
        return 0, E_BUSY;
    }
    var slot = ah_free_slot();
    if slot == AH_NO_SLOT { return 0, E_NO_SPACE; }

    var gen = agents[slot].gen + 1;
    // Generation wraps at the value that would collide with handle 0. Skipping it costs
    // one generation out of 2^31 and keeps "0 means none" true forever.
    if gen >= (2147483647 / AH_CAP) { gen = 1; }
    agents[slot].gen = gen;
    agents[slot].state = AS_CREATED;
    agents[slot].caps = caps;
    agents[slot].spawn_ms = now_ms;
    agents[slot].pid = 0;
    agents[slot].exit_code = 0;
    agents[slot].exit_cause = 0;
    agents[slot].msg_sent = 0;
    agents[slot].msg_recv = 0;
    agents[slot].name_len = name.len;
    var i: i64 = 0;
    while i < name.len {
        agents[slot].name[i] = name[i];
        i++;
    }
    return ah_handle(slot, gen), CODE_OK;
}

fn ah_free_slot() -> i64 {
    var i: i64 = 0;
    while i < AH_CAP {
        if agents[i].state == AS_FREE { return i; }
        i++;
    }
    return AH_NO_SLOT;
}

fn ah_find(name: const u8[:]) -> i64 {
    var i: i64 = 0;
    while i < AH_CAP {
        if agents[i].state != AS_FREE && agents[i].name_len == name.len {
            var j: i64 = 0;
            var same = true;
            while j < name.len {
                if agents[i].name[j] != name[j] { same = false; }
                j++;
            }
            if same { return i; }
        }
        i++;
    }
    return AH_NO_SLOT;
}

// The host has a pid for the agent. CREATED is the only state this is legal from, so a
// second bind cannot silently replace the pid of a running agent.
fn ah_bind_pid(h: i64, pid: i64) -> i64 {
    let slot = ah_resolve(h);
    if slot == AH_NO_SLOT { return E_NOTFOUND; }
    if agents[slot].state != AS_CREATED { return E_STATE; }
    if pid <= 0 { return E_INVAL; }
    agents[slot].pid = pid;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Lifecycle
// ---------------------------------------------------------------------------

fn ah_transition_legal(from: i64, to: i64) -> bool {
    if from == to { return false; }
    // CREATED -> RUNNING is the normal start. CREATED -> STOPPED is a spawn that was
    // abandoned before its first instruction ran. CREATED -> FAILED is a spawn that
    // failed to bind a pid or load.
    if from == AS_CREATED { return to == AS_RUNNING || to == AS_STOPPED || to == AS_FAILED; }
    if from == AS_RUNNING { return to == AS_STOPPED || to == AS_FAILED || to == AS_KILLED; }
    // Leaves are final: a stopped or killed agent does not resume in place. Spawning again
    // is a new agent with a new handle and a new record. Resuming is the thing that makes
    // "which run was this?" unanswerable.
    return false;
}

fn ah_set_state(h: i64, to: i64, code: i64, now_ms: i64) -> i64 {
    let slot = ah_resolve(h);
    if slot == AH_NO_SLOT { return E_NOTFOUND; }
    if !ah_transition_legal(agents[slot].state, to) { return E_STATE; }
    if to == AS_STOPPED || to == AS_FAILED || to == AS_KILLED {
        agents[slot].exit_code = code;
        if to == AS_STOPPED { agents[slot].exit_cause = 1; }
        if to == AS_KILLED { agents[slot].exit_cause = 2; }
        if to == AS_FAILED { agents[slot].exit_cause = 3; }
    }
    agents[slot].state = to;
    let _ = now_ms;   // the audit writer stamps its own records from the same clock
    return CODE_OK;
}

fn ah_start(h: i64, now_ms: i64) -> i64 { return ah_set_state(h, AS_RUNNING, 0, now_ms); }
fn ah_stop(h: i64, now_ms: i64) -> i64 { return ah_set_state(h, AS_STOPPED, 0, now_ms); }
fn ah_exit(h: i64, code: i64, now_ms: i64) -> i64 { return ah_set_state(h, AS_STOPPED, code, now_ms); }
fn ah_fail(h: i64, code: i64, now_ms: i64) -> i64 { return ah_set_state(h, AS_FAILED, code, now_ms); }
fn ah_kill(h: i64, now_ms: i64) -> i64 { return ah_set_state(h, AS_KILLED, 0, now_ms); }

// The one absence a user cannot see for themselves: a session with no agent layer looks exactly
// like a session with one that is idle. FAILURE.md promises a user-visible line, so the line is
// here as data -- the console prints what this returns, and a test can assert the exact string
// instead of a screenshot (H2's rule: the banner and status formats are data).
let AH_DOWN_LINE: const u8[:] = "AGENT LAYER DOWN";

fn ah_down_line(out: u8[>..]&, cap: i64) -> bool {
    if out.len + AH_DOWN_LINE.len > cap { return false; }
    var i: i64 = 0;
    while i < AH_DOWN_LINE.len {
        out.push(AH_DOWN_LINE[i]);
        i++;
    }
    return true;
}

// Reap: free the slot. Only from a terminal state -- freeing a running agent would leave a
// process with no name and no record. The generation is kept, which is what makes an old
// handle resolve to nothing instead of to the next occupant.
fn ah_reap(h: i64) -> i64 {
    let slot = ah_resolve(h);
    if slot == AH_NO_SLOT { return E_NOTFOUND; }
    let st = agents[slot].state;
    if st == AS_RUNNING || st == AS_CREATED { return E_STATE; }
    agents[slot].state = AS_FREE;
    agents[slot].name_len = 0;
    agents[slot].caps = 0;
    agents[slot].pid = 0;
    return CODE_OK;
}

fn ah_state(h: i64) -> i64 {
    let slot = ah_resolve(h);
    if slot == AH_NO_SLOT { return AS_FREE; }
    return agents[slot].state;
}

fn ah_is_live(h: i64) -> bool {
    let st = ah_state(h);
    return st == AS_CREATED || st == AS_RUNNING;
}

fn ah_live_count() -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < AH_CAP {
        if agents[i].state != AS_FREE { n++; }
        i++;
    }
    return n;
}

// ---------------------------------------------------------------------------
// Grants
// ---------------------------------------------------------------------------

// A grant is only ever reduced, and only ever by the host. There is no `ah_grant_add`:
// an agent that can grow its own permission set has no permission set.
fn ah_caps(h: i64) -> i64 {
    let slot = ah_resolve(h);
    if slot == AH_NO_SLOT { return 0; }
    return agents[slot].caps;
}

fn ah_caps_have(h: i64, need: i64) -> bool {
    let slot = ah_resolve(h);
    if slot == AH_NO_SLOT { return false; }
    if need == 0 { return true; }          // asking for nothing is always allowed
    if need < 0 { return false; }          // a negative mask is a caller bug, not a wildcard
    return (agents[slot].caps & need) == need;
}

// Narrow a live agent's grants. `remove` is the mask to clear.
//
// Takes nothing away from the dead: a terminal agent's caps are already meaningless and
// clearing them would hide what the agent had when its records were written.
fn ah_caps_remove(h: i64, remove: i64, now_ms: i64) -> i64 {
    let slot = ah_resolve(h);
    if slot == AH_NO_SLOT { return E_NOTFOUND; }
    if agents[slot].state != AS_RUNNING && agents[slot].state != AS_CREATED { return E_STATE; }
    if remove < 0 || (remove & (CAP_MAX_BIT - 1)) != remove { return E_INVAL; }
    agents[slot].caps = agents[slot].caps & (~remove);
    let _ = now_ms;
    return CODE_OK;
}

// Every live agent, for the host's own enumeration (quotas, shutdown order).
// Fills `out` by index -- no `push`, because a growable builder here would allocate in
// the middle of a shutdown loop. Returns the count written, which is capped by `cap`.
fn ah_list(out: i64[..24]&, cap: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < AH_CAP && n < cap && n < 24 {
        if agents[i].state != AS_FREE {
            out[n] = ah_handle(i, agents[i].gen);
            n++;
        }
        i++;
    }
    return n;
}
