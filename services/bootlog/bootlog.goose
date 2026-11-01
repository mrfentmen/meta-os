// services/bootlog/bootlog.goose
//
// Layer 4, service 1: the boot log.
//
// Status: WRITTEN (not COMPILED). Every symbol and keyword below was checked
// against goose-mcp@1.1.0 (bundled from aardappel/goose @ b781587):
//   - export fn with a C symbol name ....... spec#41, reference#108
//   - extern fn bound to a C symbol ........ spec#40, reference#106
//   - u8[>..] caller-supplied output buffer . spec#40 (read_file example)
//   - builder + append + format ............ samples/03_strings.goose
//   - trailing-bool convention ............. samples/04_errors.goose
// No Goose toolchain exists on this machine (toolchain_status: NOT FOUND), so
// this file has never been through a compiler. It is source, not a build.
//
// Why this service is first: every other service's failures need somewhere to
// be written, and that somewhere cannot itself depend on a working log. bootlog
// talks to the kernel and to nothing else.
//
// Known deviation from SERVICE_CONTRACT.md §2, recorded rather than hidden:
// the contract's entry takes BootInfo by reference. That type is B-L1-08 and
// does not exist yet, and cross-file imports in Goose are a package feature I
// have not verified, so this entry takes no argument today. Reconciling the two
// is an explicit item in B-L1-08. Writing a fake BootInfo struct here to make
// the signature look right would be a mock.

import std;

// ---------------------------------------------------------------------------
// The kernel boundary. Declarations only: how the call actually reaches the
// kernel is open question Q9 and is NOT asserted here.
// ---------------------------------------------------------------------------

extern fn sys_write_serial(s: const u8[:]) -> i64;
extern fn sys_ticks() -> i64;

// ---------------------------------------------------------------------------
// Records
// ---------------------------------------------------------------------------

// Levels are fixed small integers so a record never carries a string for its
// severity. The names below are for readers of this source, not for the wire.
let LEVEL_INFO  = 1;
let LEVEL_WARN  = 2;
let LEVEL_ERROR = 3;

let TAG = "bootlog";

// One record: "<ticks> <tag> <level> <message>\n", formatted into a caller
// buffer and written in a single syscall so a record is never interleaved with
// another writer's bytes.
fn record(buf: u8[>..]&, level: i64, msg: const u8[:]) -> bool {
    // The caller passes a fresh builder; format appends, it does not reset.
    format(buf, sys_ticks(), " ", TAG, " ", level, " ", msg, "\n");
    let n = sys_write_serial(buf);
    // A negative return is the kernel saying it could not write. There is no
    // lower place to report that to, so it is a false here and the caller
    // decides: bootlog itself carries on, because a boot log that dies on a
    // full serial buffer is worse than one with gaps.
    return n >= 0;
}

// ---------------------------------------------------------------------------
// The service
// ---------------------------------------------------------------------------

// Boot sequence record. Each call starts a fresh record buffer on the data
// stack: no allocation, nothing shared between calls.
fn stage(level: i64, msg: const u8[:]) -> bool {
    var line: u8[>..] = [];
    return record(line, level, msg);
}

// The entry the kernel calls (SERVICE_CONTRACT.md §2). Returns 0 on a clean
// stop; the supervisor records anything else as a failure.
export "svc_entry" fn service_main() -> i32 {
    // Order matters: the first record proves the serial path works at all.
    stage(LEVEL_INFO, "start");
    stage(LEVEL_INFO, "serial path up");

    // Boot log retention is a ring in this service's static storage (B-L1-11
    // provides the ring). Until that library exists the records go straight to
    // the kernel, which is the honest minimum: nothing is buffered, nothing is
    // lost silently, and the gap is visible here rather than papered over.
    stage(LEVEL_INFO, "ready");
    return 0;
}
