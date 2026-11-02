// services/session/session.goose
//
// Layer 4, service 25: console sessions.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs, static arrays,
// `while`/`if`, slices, `T&` references (reference#46), multi-value returns.
//
// A session is the thing that owns a console. Not the display service (B-L1-27): the
// display service draws whatever console it is told to draw, and what it is told to draw is
// a session's console. Splitting those two is what lets a user's session and an agent's
// session coexist on one framebuffer without either one deciding it gets to be visible.
//
// TWO CITIZENS, ONE MECHANISM
// ---------------------------
// A session is a session whether its owner is a person at a keyboard or an agent handle.
// The difference is in `owner` and in the capabilities the session may exercise, which the
// call matrix (B-L1-44) checks. There is no second code path for agents, because a second
// path is the one that does not get the permission check.
//
// WHAT A SESSION DOES NOT OWN
// ---------------------------
// It does not own input. Input events arrive with no idea which session is focused; the
// session layer maps them, and the mapping is one pointer. An unfocused session's events
// are still consumed (so a background writer does not leak bytes into the foreground), and
// that decision is recorded here rather than being implicit in the input service.

import common.err.err;

let SES_CAP: i64 = 8;
let SES_NO_SESSION: i64 = -1;

let SS_FREE: i64 = 0;
let SS_LOGIN: i64 = 1;      // credentials being checked; no console yet
let SS_ACTIVE: i64 = 2;     // owns its console; may or may not be foreground
let SS_LOCKED: i64 = 3;     // console exists, input refused until re-auth
let SS_CLOSED: i64 = 4;

let OWNER_USER: i64 = 1;
let OWNER_AGENT: i64 = 2;

struct Session {
    id: i64,               // stable for the life of the session, never reused
    owner: i64,
    user_id: i64,          // 0 for an agent
    agent: i64,            // agent handle, 0 for a user
    console: i64,          // display service console index
    state: i64,
    caps: i64,             // session-level mask, further limited by the call matrix
    started_ms: i64,
    last_input_ms: i64,
    gen: i64,
}

var sessions: Session[SES_CAP];
var ses_foreground: i64 = SES_NO_SESSION;
var ses_next_id: i64 = 1;
var ses_inited: bool = false;

fn ses_init() {
    var i: i64 = 0;
    while i < SES_CAP {
        sessions[i].state = SS_FREE;
        sessions[i].id = 0;
        sessions[i].gen = 0;
        i = i + 1;
    }
    ses_inited = true;
    ses_foreground = SES_NO_SESSION;
}

fn ses_resolve(id: i64) -> i64 {
    if !ses_inited { return SES_NO_SESSION; }
    var i: i64 = 0;
    while i < SES_CAP {
        if sessions[i].state != SS_FREE && sessions[i].id == id { return i; }
        i = i + 1;
    }
    return SES_NO_SESSION;
}

fn ses_free_slot() -> i64 {
    var i: i64 = 0;
    while i < SES_CAP {
        if sessions[i].state == SS_FREE { return i; }
        i = i + 1;
    }
    return SES_NO_SESSION;
}

// Begin a session. The caller has already authenticated, or is the system starting the
// boot session; there is no password in this file, by design -- a credential check that
// lives in the layer that also decides who may read the disk is not a check.
//
// Starts in SS_LOGIN: a session that starts ACTIVE has skipped the step where it is told
// which console it got.
fn ses_open(owner: i64, user_id: i64, agent: i64, caps: i64, now_ms: i64) -> i64, i64 {
    if !ses_inited { ses_init(); }
    if owner != OWNER_USER && owner != OWNER_AGENT { return SES_NO_SESSION, E_INVAL; }
    if owner == OWNER_USER && user_id == 0 { return SES_NO_SESSION, E_INVAL; }
    if owner == OWNER_AGENT && agent == 0 { return SES_NO_SESSION, E_INVAL; }
    let slot = ses_free_slot();
    if slot == SES_NO_SESSION { return SES_NO_SESSION, E_NO_SPACE; }

    sessions[slot].id = ses_next_id;
    ses_next_id = ses_next_id + 1;
    sessions[slot].owner = owner;
    sessions[slot].user_id = user_id;
    sessions[slot].agent = agent;
    sessions[slot].console = -1;
    sessions[slot].state = SS_LOGIN;
    sessions[slot].caps = caps;
    sessions[slot].started_ms = now_ms;
    sessions[slot].last_input_ms = now_ms;
    return sessions[slot].id, CODE_OK;
}

// Attach the console and go ACTIVE. The console is claimed at this point and not before,
// so a session that fails its login never took a console away from anyone.
fn ses_attach(id: i64, console: i64, now_ms: i64) -> i64 {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return E_NOTFOUND; }
    if sessions[slot].state != SS_LOGIN { return E_STATE; }
    if console < 0 { return E_INVAL; }
    // One session per console. A second session attached to a live console would draw over
    // it with no way to tell which output is which.
    var i: i64 = 0;
    while i < SES_CAP {
        if i != slot && sessions[i].state != SS_FREE && sessions[i].state != SS_CLOSED
            && sessions[i].console == console {
            return E_BUSY;
        }
        i = i + 1;
    }
    sessions[slot].console = console;
    sessions[slot].state = SS_ACTIVE;
    let _ = now_ms;
    return CODE_OK;
}

// ---------------------------------------------------------------------------
// Foreground
// ---------------------------------------------------------------------------

// Make a session the visible one. Only an ACTIVE session can be foreground: making a
// locked session visible would show a login prompt over someone else's work, which is a
// screen that lies about who is logged in.
fn ses_focus(id: i64) -> i64 {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return E_NOTFOUND; }
    if sessions[slot].state != SS_ACTIVE { return E_STATE; }
    ses_foreground = id;
    return CODE_OK;
}

fn ses_foreground_id() -> i64 { return ses_foreground; }

// The console that should currently be drawn. -1 when nothing is focused.
fn ses_visible_console() -> i64 {
    let slot = ses_resolve(ses_foreground);
    if slot == SES_NO_SESSION { return -1; }
    return sessions[slot].console;
}

// Is this session allowed to receive input right now? The single gate the input path
// consults, so "focused but locked" and "active but not focused" have one answer each.
fn ses_accepts_input(id: i64) -> bool {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return false; }
    if ses_foreground != id { return false; }
    return sessions[slot].state == SS_ACTIVE;
}

fn ses_note_input(id: i64, now_ms: i64) {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return; }
    sessions[slot].last_input_ms = now_ms;
}

// ---------------------------------------------------------------------------
// Lock, close
// ---------------------------------------------------------------------------

fn ses_lock(id: i64) -> i64 {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return E_NOTFOUND; }
    if sessions[slot].state != SS_ACTIVE { return E_STATE; }
    sessions[slot].state = SS_LOCKED;
    return CODE_OK;
}

fn ses_unlock(id: i64) -> i64 {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return E_NOTFOUND; }
    if sessions[slot].state != SS_LOCKED { return E_STATE; }
    sessions[slot].state = SS_ACTIVE;
    return CODE_OK;
}

// Close: from any state but FREE. Freeing the slot is immediate and the id is not reused,
// so a stale id resolves to nothing rather than to the next session.
fn ses_close(id: i64) -> i64 {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return E_NOTFOUND; }
    sessions[slot].state = SS_CLOSED;
    sessions[slot].console = -1;
    sessions[slot].caps = 0;
    if ses_foreground == id { ses_foreground = SES_NO_SESSION; }
    return CODE_OK;
}

// The supervisor's exit path frees the slot once the close has been recorded.
fn ses_reap(id: i64) -> i64 {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return E_NOTFOUND; }
    if sessions[slot].state != SS_CLOSED { return E_STATE; }
    sessions[slot].state = SS_FREE;
    sessions[slot].id = 0;
    sessions[slot].owner = 0;
    sessions[slot].user_id = 0;
    sessions[slot].agent = 0;
    return CODE_OK;
}

fn ses_state(id: i64) -> i64 {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return SS_FREE; }
    return sessions[slot].state;
}

fn ses_caps(id: i64) -> i64 {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return 0; }
    return sessions[slot].caps;
}

fn ses_owner_agent(id: i64) -> i64 {
    let slot = ses_resolve(id);
    if slot == SES_NO_SESSION { return 0; }
    return sessions[slot].agent;
}

// When an agent dies, its session dies with it. Called by the agent host's exit path; a
// session outliving its agent is a console nobody is accountable for.
fn ses_close_agent_sessions(agent: i64) -> i64 {
    var n: i64 = 0;
    var i: i64 = 0;
    while i < SES_CAP {
        if sessions[i].state != SS_FREE && sessions[i].agent == agent && agent != 0 {
            ses_close(sessions[i].id);
            n = n + 1;
        }
        i = i + 1;
    }
    return n;
}
