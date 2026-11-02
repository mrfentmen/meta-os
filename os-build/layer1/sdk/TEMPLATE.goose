// services/<name>/<name>.goose
//
// B-L1-119 — Service SDK template. Copy to services/<name>/<name>.goose and work down the
// CHECKLIST in this directory. Status line first, and it stays honest: WRITTEN until the Mac
// build says otherwise, COMPILED only with a build log to name.
//
// Status: TEMPLATE (not compiled, not run, not a service).
//
// THREE PARAGRAPHS BEFORE ANY CODE, ALWAYS
// ----------------------------------------
// 1. WHAT THIS SERVICE IS, in one sentence, using words a person who has not read the layer
//    would understand.
// 2. WHAT IT REFUSES, and why. The refusals are the design; a service defined only by what
//    it accepts is a service whose failure modes were nobody's decision.
// 3. WHAT IT DOES NOT OWN. Every service shares a machine with others; naming the boundary
//    here is what stops the next change from crossing it by accident.
//
// Then imports, then constants, then structs, then functions in the order they are called.

import common.err.err;
import common.fmt.fmt;
import logd.logd;
import supervisor.supervisor;

let TPL_SLOT_MAX: i64 = 8;            // fixed sizes carry their reason, or they get "tuned"
let TPL_NAME_MAX: i64 = 16;

struct Entry {
    id: i64,
    name: u8[..16],
    name_len: i64,
    active: bool,
    created_ms: i64,
}

struct Service {
    entries: Entry[..8],
    count: i64,
    next_id: i64,
    failures: i64,
}

// Init runs once, before the supervisor marks the service RUNNING. It must not block, must
// not call the network, and must leave the service in a state where every other function is
// safe to call -- including on a machine where init half-failed.
fn tpl_init(now_ms: i64) -> i64 {
    var s: Service;
    var i: i64 = 0;
    while i < TPL_SLOT_MAX { s.entries[i] = tpl_blank(); i++; }
    s.count = 0;
    s.next_id = 1;
    s.failures = 0;
    return CODE_OK;
}

fn tpl_blank() -> Entry {
    var e: Entry;
    e.id = 0;
    e.name_len = 0;
    e.active = false;
    e.created_ms = 0;
    var i: i64 = 0;
    while i < TPL_NAME_MAX { e.name[i] = 0; i++; }
    return e;
}

// The one function that mutates. Returns (id, code); every refusal has its own code so the
// caller can act on it, and the error registry (B-L1-12) already has the vocabulary.
fn tpl_add(s: Service&, name: const u8[:], now_ms: i64) -> i64, i64 {
    if name.len == 0 || name.len > TPL_NAME_MAX - 1 { return 0, E_INVAL; }
    var slot: i64 = -1;
    var i: i64 = 0;
    while i < TPL_SLOT_MAX {
        if !s.entries[i].active && slot < 0 { slot = i; }
        i++;
    }
    if slot < 0 { return 0, E_NOROOM; }

    var e = tpl_blank();
    e.id = s.next_id;
    s.next_id = s.next_id + 1;
    var k: i64 = 0;
    while k < name.len {
        e.name[k] = name[k];
        k++;
    }
    e.name_len = name.len;
    e.active = true;
    e.created_ms = now_ms;
    s.entries[slot] = e;
    s.count = s.count + 1;
    return e.id, CODE_OK;
}

// Lookup by id. Returns false, not a sentinel entry: a caller that gets a value back always
// has to handle the false, which is the point.
fn tpl_get(s: Service&, id: i64, out: Entry&) -> bool {
    var i: i64 = 0;
    while i < TPL_SLOT_MAX {
        if s.entries[i].active && s.entries[i].id == id {
            out = s.entries[i];
            return true;
        }
        i++;
    }
    return false;
}

// Health line: the numbers this service wants a reader to see, and nothing else. Called by
// the watchdog; must be cheap and must never fail to produce a line.
fn tpl_health(s: Service&, out: u8[>..]&, cap: i64) -> bool {
    if !fmt.append_str(out, cap, "entries=") { return false; }
    if !fmt.append_int(out, cap, s.count) { return false; }
    if !fmt.append_str(out, cap, " failures=") { return false; }
    return fmt.append_int(out, cap, s.failures);
}

// Failures are counted and logged, never swallowed. One helper so no call site forgets:
// a service that logs at three different levels for the same condition is a service whose
// log cannot be grepped.
fn tpl_fail(s: Service&, tag: const u8[:], what: const u8[:], code: i64) -> i64 {
    s.failures = s.failures + 1;
    let _ = log_error(tag, what);
    return code;
}
