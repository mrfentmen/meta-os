// services/callmatrix/callmatrix.goose
//
// Layer 4, service 26: the service-to-service permission table and the one check that
// consults it.
//
// Status: RUNS — reached by tests/t69_callmatrix (28 checks, exit 0). Measured 2026-11-02 by audit_status.py. Verified via goose-mcp@1.1.0: structs, static arrays,
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
// Appended 2026-11-01 (B-L1-118 resolution). Appending, never renumbering: these ids are
// also the numbers services report to the supervisor, and a shift would silently rewrite
// every log line and every stored record that named a service.
let SVC_FS: i64 = 22;
let SVC_SHELL: i64 = 23;
// The template keeps a row too. It is not started by the boot sequence, but a service
// generated from it is -- and a template copied without its permissions is exactly how the
// twelve missing edges in this file appeared. `example` is id 24 for that reason alone.
let SVC_EXAMPLE: i64 = 24;

// The face layer (2026-11-02, R7). Appended again, same rule: never renumber. These six are
// the services the home surface draws from -- settings, wallpaper, dock, the dashboard feed,
// the updater's client half and the board client.
let SVC_SETTINGS: i64 = 25;
let SVC_WALLPAPER: i64 = 26;
let SVC_DOCK: i64 = 27;
let SVC_DASHBOARD: i64 = 28;
let SVC_UPDATER_CLIENT: i64 = 29;
let SVC_BOARD: i64 = 30;
// The top-bar feed (2026-11-02, R8). Appended like every id before it: the face services
// push into it, so its own row is short and its callers gained a bit.
let SVC_NOTIFY: i64 = 31;

let SVC_COUNT: i64 = 31;   // ids 1..31 inclusive

// One bit per callee id, in a word per caller. Thirty-one services fit in an i64 with room
// to spare, so the row is a bitmask and `cm_allows` is a shift and a mask: no search, no
// allocation, and impossible to have a partially-written row.
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
        i = i + 1;
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
    // netcfg writes its configuration through the filesystem (persist.goose, B-L1-104):
    // the address model is imported as a library, but the config survives a reboot only
    // because it is a file, and a file is fs.
    cm_set(SVC_NETCFG, cm_bit(SVC_NET) | cm_bit(SVC_STORAGE) | cm_bit(SVC_LOG) | cm_bit(SVC_FS));
    cm_set(SVC_DHCP, cm_bit(SVC_NET) | cm_bit(SVC_NETCFG) | cm_bit(SVC_TIME) | cm_bit(SVC_LOG));
    cm_set(SVC_DNS, cm_bit(SVC_NET) | cm_bit(SVC_NETCFG) | cm_bit(SVC_LOG));
    // socket imports netcfg's address model: a socket is bound to an address that netcfg
    // owns, so the lookup is a call, not a copy.
    cm_set(SVC_SOCKET, cm_bit(SVC_NET) | cm_bit(SVC_DNS) | cm_bit(SVC_LOG) | cm_bit(SVC_TIME)
        | cm_bit(SVC_NETCFG));
    cm_set(SVC_UPDATER, cm_bit(SVC_SOCKET) | cm_bit(SVC_STORAGE) | cm_bit(SVC_AUDIT)
        | cm_bit(SVC_LOG) | cm_bit(SVC_TIME));
    cm_set(SVC_TIMESYNC, cm_bit(SVC_SOCKET) | cm_bit(SVC_TIME) | cm_bit(SVC_LOG));
    cm_set(SVC_AGENTHOST, cm_bit(SVC_SUPERVISOR) | cm_bit(SVC_AUDIT) | cm_bit(SVC_SESSION)
        | cm_bit(SVC_LOG) | cm_bit(SVC_TIME) | cm_bit(SVC_STORAGE));
    cm_set(SVC_AUDIT, cm_bit(SVC_STORAGE) | cm_bit(SVC_TIME) | cm_bit(SVC_LOG));
    cm_set(SVC_SESSION, cm_bit(SVC_DISPLAY) | cm_bit(SVC_INPUT) | cm_bit(SVC_AUDIT)
        | cm_bit(SVC_LOG) | cm_bit(SVC_TIME));
    // The filesystem sits on the storage contract and reports what it refuses. It is the
    // one service whose whole job is another service's API, which is why its row is short.
    cm_set(SVC_FS, cm_bit(SVC_STORAGE) | cm_bit(SVC_LOG));
    // The shell is the widest row in the table and it should be read as a warning: a shell
    // that can reach the supervisor, the audit trail, the filesystem and the clock can do
    // everything a user can. That is correct for the user's shell and is exactly why agents
    // do not get a shell handle -- they get the calls their capabilities allow.
    cm_set(SVC_SHELL, cm_bit(SVC_FS) | cm_bit(SVC_LOG) | cm_bit(SVC_AUDIT)
        | cm_bit(SVC_SUPERVISOR) | cm_bit(SVC_TIME));
    // The template: one of everything it demonstrates (files, clock, service table, health).
    cm_set(SVC_EXAMPLE, cm_bit(SVC_FS) | cm_bit(SVC_TIME) | cm_bit(SVC_SUPERVISOR)
        | cm_bit(SVC_WATCHDOG) | cm_bit(SVC_LOG));

    // The face layer. Read these rows as what each service is allowed to READ from the
    // machine it is drawing, not as what it calls today: none of the six imports another
    // service yet, so the audit reports every edge below as DORMANT, and that is the honest
    // answer. Declaring them now is deliberate -- the alternative is a face service wired
    // later with its permissions added in the same commit that needs them, which is how the
    // matrix stops describing the system and starts describing the last patch.
    cm_set(SVC_SETTINGS, cm_bit(SVC_STORAGE) | cm_bit(SVC_LOG) | cm_bit(SVC_TIME));
    cm_set(SVC_WALLPAPER, cm_bit(SVC_STORAGE) | cm_bit(SVC_LOG) | cm_bit(SVC_SETTINGS));
    cm_set(SVC_DOCK, cm_bit(SVC_STORAGE) | cm_bit(SVC_LOG) | cm_bit(SVC_SETTINGS)
        | cm_bit(SVC_SESSION));
    cm_set(SVC_DASHBOARD, cm_bit(SVC_LOG) | cm_bit(SVC_SUPERVISOR) | cm_bit(SVC_WATCHDOG)
        | cm_bit(SVC_SESSION) | cm_bit(SVC_SETTINGS));
    cm_set(SVC_UPDATER_CLIENT, cm_bit(SVC_UPDATER) | cm_bit(SVC_SOCKET) | cm_bit(SVC_NET)
        | cm_bit(SVC_LOG) | cm_bit(SVC_TIME) | cm_bit(SVC_NOTIFY));
    // The board and the updater's client half push events at the bar: a post arrived, an
    // update is available. The bit is declared here, on the CALLER's row, because that is
    // where a permission lives -- and it is dormant until one of them imports notify.
    cm_set(SVC_BOARD, cm_bit(SVC_NET) | cm_bit(SVC_STORAGE) | cm_bit(SVC_LOG)
        | cm_bit(SVC_TIME) | cm_bit(SVC_NOTIFY));

    // The bar itself reads nothing from the machine except the log and the clock. It is the
    // receiver of the two edges above, which is why its row is the shortest in the face
    // layer: a notification that could call back into the thing that sent it would let a
    // producer make the bar lie about its own event.
    cm_set(SVC_NOTIFY, cm_bit(SVC_LOG) | cm_bit(SVC_TIME));
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
