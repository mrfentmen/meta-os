// services/tests/t69_callmatrix.goose
//
// B-L1-118 — test program for the permission table (services/callmatrix/callmatrix.goose).
//
// Status: RUNS — tests/t69_callmatrix: 28 checks, 0 failures. Measured 2026-11-02 by audit_status.py.
//
// WHAT IS UNDER TEST, AND WHY THESE CASES
// ---------------------------------------
// The table was written before the services, so for most of this build-out it described a
// system that did not exist yet. Twelve import edges had no permission and two services had no
// id at all; the auditor caught that, and this program is what catches the next one, because it
// asks `cm_allows` instead of reading the source text.
//
// The cases are the four ways this table can be wrong:
//
//   1. An id is missing from the table (a service that exists and cannot be called).
//   2. An edge that exists in source is denied (the failure reads as "service did not start",
//      which is the worst error message in the system).
//   3. An edge nobody has is allowed (a permission wider than the code needs, which is how a
//      shell ends up able to reach the audit trail).
//   4. The error path cannot tell a denial from a broken id, so a caller bug is paged to the
//      person who owns the policy.

import callmatrix.callmatrix;
import common.err.err;
import common.fmt.fmt;
import common.sys.sys;

var t_pass: i64 = 0;
var t_fail: i64 = 0;

fn say(s: const u8[:]) { let _ = sys_write_serial(s); }

fn check(name: const u8[:], cond: bool) {
    if cond { t_pass = t_pass + 1; say("ok   "); }
    else { t_fail = t_fail + 1; say("FAIL "); }
    say(name);
    say("\n");
}

// Every id from 1 to SVC_COUNT must have a row with at least one callee. A service with an
// empty row is a service nothing may call, which is a decision nobody made on purpose.
fn rows_populated() -> bool {
    var i: i64 = 1;
    while i <= SVC_COUNT {
        if cm_mask(i) == 0 { return false; }
        i = i + 1;
    }
    return true;
}

fn main() {
    cm_init();

    // --- 1. the table has a row per id, and the count matches the ids ---
    check("SVC_COUNT is 24", SVC_COUNT == 24);
    check("every id 1..24 has a non-empty row", rows_populated());
    check("the appended ids are the ones the work order named",
          SVC_FS == 22 && SVC_SHELL == 23 && SVC_EXAMPLE == 24);

    // --- 2. the twelve edges that were missing must be allowed ---
    // fs -> storage: the block API is what a filesystem is made of.
    check("fs may call storage", cm_allows(SVC_FS, SVC_STORAGE));
    // netcfg -> fs: persistence is a file.
    check("netcfg may call fs", cm_allows(SVC_NETCFG, SVC_FS));
    // socket -> netcfg: a bound address belongs to netcfg.
    check("socket may call netcfg", cm_allows(SVC_SOCKET, SVC_NETCFG));
    // shell -> five services.
    check("shell may call fs", cm_allows(SVC_SHELL, SVC_FS));
    check("shell may call log", cm_allows(SVC_SHELL, SVC_LOG));
    check("shell may call audit", cm_allows(SVC_SHELL, SVC_AUDIT));
    check("shell may call supervisor", cm_allows(SVC_SHELL, SVC_SUPERVISOR));
    check("shell may call time", cm_allows(SVC_SHELL, SVC_TIME));
    // example -> four services plus the log.
    check("example may call fs", cm_allows(SVC_EXAMPLE, SVC_FS));
    check("example may call time", cm_allows(SVC_EXAMPLE, SVC_TIME));
    check("example may call supervisor", cm_allows(SVC_EXAMPLE, SVC_SUPERVISOR));
    check("example may call watchdog", cm_allows(SVC_EXAMPLE, SVC_WATCHDOG));

    // --- 3. the table is still deny-by-default ---
    check("fs may NOT call net", !cm_allows(SVC_FS, SVC_NET));
    check("shell may NOT call storage", !cm_allows(SVC_SHELL, SVC_STORAGE));
    check("shell may NOT call netcfg", !cm_allows(SVC_SHELL, SVC_NETCFG));
    check("bootlog may NOT call agenthost", !cm_allows(SVC_BOOTLOG, SVC_AGENTHOST));
    check("watchdog may NOT call fs", !cm_allows(SVC_WATCHDOG, SVC_FS));

    // --- 4. self-calls and the error path ---
    check("a service may call itself", cm_allows(SVC_FS, SVC_FS));
    check("id 0 is never allowed", !cm_allows(0, SVC_LOG));
    check("an id past the end is never allowed", !cm_allows(SVC_LOG, SVC_COUNT + 1));
    check("cm_check: denial is E_DENIED", cm_check(SVC_FS, SVC_NET) == E_DENIED);
    check("cm_check: a broken callee id is E_INVAL", cm_check(SVC_FS, 0) == E_INVAL);
    check("cm_check: a broken caller id is E_INVAL", cm_check(999, SVC_LOG) == E_INVAL);
    check("cm_check: an allowed pair is CODE_OK", cm_check(SVC_SHELL, SVC_FS) == CODE_OK);

    // --- 5. the mask agrees with the check, at the one id that used to collide ---
    // `log` is the matrix's name for the logd directory; the id is one bit, not two.
    check("the log service is one bit", (cm_mask(SVC_SHELL) & cm_bit(SVC_LOG)) != 0);

    say("t69 done  pass=");
    var pb: u8[>..] = [];
    format_int(pb, t_pass, 10, 0, 0);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    format_int(fb, t_fail, 10, 0, 0);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
