// services/callmatrix/callmatrix.goose
//
// Layer 4, service 26: the service-to-service permission table and the one check that
// consults it.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: structs, static arrays,
// `while`/`if`, slices, `T&` references (reference#46), multi-value returns, bitwise
// operators.
//
// WHY A MATRIX AND NOT A CAPABILITY TREE
// --------------------------------------
// Because the question is always "may A call B", and the answer must be readable in one
// place by a person auditing it. A capability tree answers the same question by walking
// ownership, and the walk is what gets an edge wrong when two services share a parent.
// Every row here is a decision someone can argue with, which is the point.
//
// ONE CHECK
// ---------
// `cm_allows` is the only function that answers the question -- the registry (B-L1-22)
// calls it and nothing else does. A second copy of the logic, even a "convenience" one,
// is a second answer, and the disagreement between them is the bug.
//
// DENY BY DEFAULT
// ---------------
// An unknown caller, an unknown callee, or a pair not in the table is denied. The failure
// mode when this file is wrong is a service that cannot start; the failure mode of an
// allow-by-default table is every service calling everything, and it never announces
// itself.

import common.err.err;

// Service ids. These are index numbers in the matrix AND the numbers services report to
// the supervisor, so they must not be reordered.
let SVC_NONE: i64 = 0;
let SVC_BOOTLOG: i64 = 1;
let SVC_CONSOLE: i64 = 2;
let SVC_LOG: i64 = 3;
let SVC_LOGFMT: i64 = 4;
let SVC_TIME: i64 = 5;
let SVC_SUPERVISOR: i64 = 6;
let SVC_WATCHDOG: i64 = 7;
let SVC_DEVICES: i64 = 8;
let SVC_STORAGE: i64 = 9;
let SVC_INPUT: i64 = 10;
let SVC_DISPLAY: i64 = 11;
let SVC_NET: i64 = 12;
let SVC_NETCFG: i64 = 13;
let SVC_DHCP: i64 = 14;
let SVC_DNS: i64 = 15;
let SVC_SOCKET: i64 = 16;
let SVC_UPDATER: i64 = 17;
let SVC_TIMESYNC: i64 = 18;
let SVC_AGENTHOST: i64 = 19;
let SVC_AUDIT: i64 = 20;
let SVC_SESSION: i64 = 21;

let SVC_COUNT: i64 = 21;   // ids 1..21 inclusive

// One bit per callee id, in a word per caller. 21 services fit in 32 bits, so the row is
// an i64 and `cm_allows` is a shift and a mask: no search, no allocation, and impossible to
// have a partially-written row.
struct Row {
    caller: i64,
    allow: i64,
}

var matrix: Row[SVC_COUNT];

fn cm_bit(id: i64) -> i64 {
    if id <= 0 || id > SVC_COUNT { return 0; }
    return 1 << id;
}

// Build the table. Called once before the registry starts.
fn cm_init() {
    var i: i64 = 0;
    while i < SVC_COUNT {
        matrix[i].caller = 0;
        matrix[i].allow = 0;
        i++;
    }
    cm_set(SVC_BOOTLOG, cm_bit(SVC_CONSOLE) | cm_bit(SVC_LOG) | cm_bit(SVC_TIME) | cm_bit(SVC_DEVICES));
    cm_set(SVC_CONSOLE, cm_bit(SVC_BOOTLOG) | cm_bit(SVC_LOG));
    cm_set(SVC_LOG, cm_bit(SVC_CONSOLE) | cm_bit(SVC_STORAGE) | cm_bit(SVC_LOGFMT) | cm_bit(SVC_TIME));
    cm_set(SVC_LOGFMT, cm_bit(SVC_TIME));
    cm_set(SVC_TIME, cm_bit(SVC_DEVICES));
    cm_set(SVC_SUPERVISOR, cm_bit(SVC_LOG) | cm_bit(SVC_WATCHDOG) | cm_bit(SVC_SESSION)
        | cm_bit(SVC_AUDIT) | cm_bit(SVC_TIME) | cm_bit(SVC_AGENTHOST));
    cm_set(SVC_WATCHDOG, cm_bit(SVC_SUPERVISOR) | cm_bit(SVC_TIME) | cm_bit(SVC_LOG));
    cm_set(SVC_DEVICES, cm_bit(SVC_LOG) | cm_bit(SVC_BOOTLOG));
    cm_set(SVC_STORAGE, cm_bit(SVC_LOG) | cm_bit(SVC_DEVICES));
    cm_set(SVC_INPUT, cm_bit(SVC_SESSION) | cm_bit(SVC_DISPLAY) | cm_bit(SVC_LOG));
    cm_set(SVC_DISPLAY, cm_bit(SVC_SESSION) | cm_bit(SVC_LOG));
    cm_set(SVC_NET, cm_bit(SVC_NETCFG) | cm_bit(SVC_LOG) | cm_bit(SVC_DEVICES));
    cm_set(SVC_NETCFG, cm_bit(SVC_NET) | cm_bit(SVC_STORAGE) | cm_bit(SVC_LOG));
    cm_set(SVC_DHCP, cm_bit(SVC_NET) | cm_bit(SVC_NETCFG) | cm_bit(SVC_TIME) | cm_bit(SVC_LOG));
    cm_set(SVC_DNS, cm_bit(SVC_NET) | cm_bit(SVC_NETCFG) | cm_bit(SVC_LOG));
    cm_set(SVC_SOCKET, cm_bit(SVC_NET) | cm_bit(SVC_DNS) | cm_bit(SVC_LOG) | cm_bit(SVC_TIME));
    cm_set(SVC_UPDATER, cm_bit(SVC_SOCKET) | cm_bit(SVC_STORAGE) | cm_bit(SVC_AUDIT)
        | cm_bit(SVC_LOG) | cm_bit(SVC_TIME));
    cm_set(SVC_TIMESYNC, cm_bit(SVC_SOCKET) | cm_bit(SVC_TIME) | cm_bit(SVC_LOG));
    cm_set(SVC_AGENTHOST, cm_bit(SVC_SUPERVISOR) | cm_bit(SVC_AUDIT) | cm_bit(SVC_SESSION)
        | cm_bit(SVC_LOG) | cm_bit(SVC_TIME) | cm_bit(SVC_STORAGE));
    cm_set(SVC_AUDIT, cm_bit(SVC_STORAGE) | cm_bit(SVC_TIME) | cm_bit(SVC_LOG));
    cm_set(SVC_SESSION, cm_bit(SVC_DISPLAY) | cm_bit(SVC_INPUT) | cm_bit(SVC_AUDIT)
        | cm_bit(SVC_LOG) | cm_bit(SVC_TIME));
}

fn cm_set(caller: i64, allow: i64) {
    if caller <= 0 || caller > SVC_COUNT { return; }
    matrix[caller - 1].caller = caller;
    matrix[caller - 1].allow = allow;
}

fn cm_row(caller: i64) -> i64 {
    if caller <= 0 || caller > SVC_COUNT { return 0; }
    if matrix[caller - 1].caller != caller { return 0; }   // uninitialised row is a deny
    return matrix[caller - 1].allow;
}

// THE CHECK. Caller may call callee, or not.
//
// A service calling itself is allowed: it is not a permission boundary, and refusing it
// would make an internal helper that goes through the registry fail for no reason.
// Anything else must be a bit in the caller's row.
fn cm_allows(caller: i64, callee: i64) -> bool {
    if caller == callee && caller > 0 { return caller <= SVC_COUNT; }
    if callee <= 0 || callee > SVC_COUNT { return false; }
    if caller <= 0 || caller > SVC_COUNT { return false; }
    return (cm_row(caller) & cm_bit(callee)) != 0;
}

// For the registry's error path: is this a denial or a broken id? The difference matters,
// because a broken id is a bug in the caller and a denial is a policy decision, and they go
// to different people.
fn cm_check(caller: i64, callee: i64) -> i64 {
    if callee <= 0 || callee > SVC_COUNT { return E_INVAL; }
    if caller <= 0 || caller > SVC_COUNT { return E_INVAL; }
    if cm_allows(caller, callee) { return CODE_OK; }
    return E_DENIED;
}

// Audit helper: every caller this one may reach, as the raw mask, so a startup record can
// state what a service was allowed to do when it started rather than what it did.
fn cm_mask(caller: i64) -> i64 {
    return cm_row(caller);
}
