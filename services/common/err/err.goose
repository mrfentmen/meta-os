// services/common/err/err.goose
//
// The layer's error vocabulary: one code set, one result convention.
//
// Status: WRITTEN (not COMPILED). Verified via goose-mcp@1.1.0: trailing-bool and
// trailing-code returns (samples/04_errors.goose, samples/01_tour.goose), match
// keyword (list_keywords), top-level globals (reference#5), const u8[:] returns
// (spec#41 example).
//
// WHY CODES AND NOT STRINGS
// -------------------------
// A string error cannot cross a service boundary without carrying a pointer into
// the sender's memory, and it cannot be compared, counted or filtered cheaply.
// So: a code crosses, and `name(code)` turns a code into text at the one place
// text is wanted -- a log line or a console message.
//
// THE CONVENTION, IN ONE PARAGRAPH
// --------------------------------
// A call that can fail returns its value first and the code last:
//
//     fn read_sector(n: i64, out: u8[>..]&) -> i64, i64   // bytes, code
//     let n, code = read_sector(7, buf);
//     if err.failed(code) { ... }
//
// `err.ok(0)` means success. This is Goose's own idiom (a trailing bool or code
// says whether the rest is meaningful), generalised so that a service can say
// *why*, not just *that*.
//
// WHY RANGES
// ----------
// Codes are grouped by domain so a log reader can tell a storage failure from an
// agent-policy refusal without a lookup table in their head. A service that adds
// a code takes the next free number in its own range and never renumbers an
// existing one: an audit record from last month must mean the same thing today.

// ---------------------------------------------------------------------------
// Success and the shared codes
// ---------------------------------------------------------------------------

let CODE_OK: i64 = 0;

// 1xxx: failures any service can produce
let E_INVAL: i64 = 1001;      // an argument was out of range or malformed
let E_NOROOM: i64 = 1002;     // the destination has no capacity left
let E_NOTFOUND: i64 = 1003;   // the named thing does not exist
let E_BUSY: i64 = 1004;       // the resource is in use; try again later
let E_TIMEOUT: i64 = 1005;    // a deadline passed before the work completed
let E_IO: i64 = 1006;         // a device or transport failed
let E_CORRUPT: i64 = 1007;    // data arrived but did not validate
let E_UNSUPPORTED: i64 = 1008;// the request is valid but not implemented here
let E_DENIED: i64 = 1009;     // a capability or policy refused the request
let E_STATE: i64 = 1010;      // the caller asked for something in the wrong order
let E_RATE: i64 = 1011;       // a quota or rate limit was reached
let E_NOKEY: i64 = 1012;      // no key was pending (read_key's "nothing now")

// 2xxx: storage (services/storage, fs)
let E_NO_SPACE: i64 = 2001;
let E_NO_DEVICE: i64 = 2002;
let E_BAD_BLOCK: i64 = 2003;
let E_READ_ONLY: i64 = 2004;

// 3xxx: network (dhcp, dns, sockets, timesync)
let E_NO_LINK: i64 = 3001;
let E_NO_ADDRESS: i64 = 3002;
let E_RESOLVE: i64 = 3003;
let E_REFUSED: i64 = 3004;
let E_UNREACHABLE: i64 = 3005;

// 4xxx: agent host and audit
let E_NO_AGENT: i64 = 4001;
let E_NO_CAPABILITY: i64 = 4002;
let E_QUOTA: i64 = 4003;
let E_AUDIT_FULL: i64 = 4004;

// 5xxx: updater
let E_BAD_MANIFEST: i64 = 5001;
let E_BAD_SIGNATURE: i64 = 5002;
let E_VERIFY: i64 = 5003;
let E_ROLLBACK: i64 = 5004;

// 6xxx: session and shell
let E_NO_SESSION: i64 = 6001;
let E_AUTH: i64 = 6002;
let E_SYNTAX: i64 = 6003;

// ---------------------------------------------------------------------------
// Predicates: the only way call sites should test a code
// ---------------------------------------------------------------------------

fn ok(code: i64) -> bool {
    return code == CODE_OK;
}

fn failed(code: i64) -> bool {
    return code != CODE_OK;
}

// Worth trying the same call again. This is a judgement encoded once, so that
// every retry loop in the layer agrees: a busy resource or a timeout is worth
// another attempt, a malformed argument never is.
fn transient(code: i64) -> bool {
    if code == E_BUSY { return true; }
    if code == E_TIMEOUT { return true; }
    if code == E_RATE { return true; }
    if code == E_NO_LINK { return true; }
    return false;
}

// The domain a code belongs to, for routing a failure to the right handler.
fn domain(code: i64) -> i64 {
    if code == CODE_OK { return 0; }
    return code / 1000;
}

// ---------------------------------------------------------------------------
// Text: only for humans, only at the edge
// ---------------------------------------------------------------------------

// Short stable name for a code. Used in log records and console output; never
// parsed, never compared. An unknown code says so rather than inventing a name,
// because a wrong name in a log is worse than "unknown".
fn name(code: i64) -> const u8[:] {
    // An if-chain rather than match: `match` exists in Goose (list_keywords), but
    // the form with constant patterns is not one of the constructs I verified,
    // and this file's rule is that every form in it has evidence behind it.
    if code == CODE_OK { return "ok"; }
    if code == E_INVAL { return "inval"; }
    if code == E_NOROOM { return "noroom"; }
    if code == E_NOTFOUND { return "notfound"; }
    if code == E_BUSY { return "busy"; }
    if code == E_TIMEOUT { return "timeout"; }
    if code == E_IO { return "io"; }
    if code == E_CORRUPT { return "corrupt"; }
    if code == E_UNSUPPORTED { return "unsupported"; }
    if code == E_DENIED { return "denied"; }
    if code == E_STATE { return "state"; }
    if code == E_RATE { return "rate"; }
    if code == E_NOKEY { return "nokey"; }
    if code == E_NO_SPACE { return "no-space"; }
    if code == E_NO_DEVICE { return "no-device"; }
    if code == E_BAD_BLOCK { return "bad-block"; }
    if code == E_READ_ONLY { return "read-only"; }
    if code == E_NO_LINK { return "no-link"; }
    if code == E_NO_ADDRESS { return "no-address"; }
    if code == E_RESOLVE { return "resolve"; }
    if code == E_REFUSED { return "refused"; }
    if code == E_UNREACHABLE { return "unreachable"; }
    if code == E_NO_AGENT { return "no-agent"; }
    if code == E_NO_CAPABILITY { return "no-capability"; }
    if code == E_QUOTA { return "quota"; }
    if code == E_AUDIT_FULL { return "audit-full"; }
    if code == E_BAD_MANIFEST { return "bad-manifest"; }
    if code == E_BAD_SIGNATURE { return "bad-signature"; }
    if code == E_VERIFY { return "verify"; }
    if code == E_ROLLBACK { return "rollback"; }
    if code == E_NO_SESSION { return "no-session"; }
    if code == E_AUTH { return "auth"; }
    if code == E_SYNTAX { return "syntax"; }
    return "unknown";
}

// ---------------------------------------------------------------------------
// Rules this module imposes on every service
// ---------------------------------------------------------------------------
//
// 1. A service returns a code, never a string, across its boundary.
// 2. A service that exits after failing returns a non-zero exit code AND writes
//    one log record with the code's name. Silent failure is a bug.
// 3. A code is never reused for a different meaning. Append new codes at the end
//    of the own domain's block; B-L1-137 freezes the registry at the end.
// 4. Tests compare codes, never names.
