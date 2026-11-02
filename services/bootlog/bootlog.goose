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
import common.fmt.fmt;
import common.sys.sys;

// ---------------------------------------------------------------------------
// The kernel boundary. Declarations only: how the call actually reaches the
// kernel is open question Q9 and is NOT asserted here.
// ---------------------------------------------------------------------------


// ---------------------------------------------------------------------------
// Records
// ---------------------------------------------------------------------------

// Levels are fixed small integers so a record never carries a string for its
// severity. The names below are for readers of this source, not for the wire.
let LEVEL_INFO  = 1;
let LEVEL_WARN  = 2;
let LEVEL_ERROR = 3;

let TAG = "bootlog";

// One boot record, including its newline. Sized for the longest stage message the
// boot order produces, with room to spare; a longer one is refused by `record`.
let BL_LINE: i64 = 200;

// One record: "<ticks> <tag> <level> <message>\n", formatted into a caller
// buffer and written in a single syscall so a record is never interleaved with
// another writer's bytes.
// `cap` is the caller's limit and it is enforced: a record that does not fit is refused
// before a byte is written, so the buffer is left EMPTY rather than holding half a line.
// A half-written boot record is worse than a missing one -- it is the line somebody reads
// at 3am and believes.
fn record(buf: u8[>..]&, cap: i64, level: i64, msg: const u8[:]) -> bool {
    let need = digits_needed(sys_ticks(), 10) + 1 + TAG.len + 1 + digits_needed(level, 10)
        + 1 + msg.len + 1;
    if need > room_left(buf, cap) { return false; }
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
    return record(line, BL_LINE, level, msg);
}

// The entry the kernel calls (SERVICE_CONTRACT.md §2). Returns 0 on a clean
// stop; the supervisor records anything else as a failure.
