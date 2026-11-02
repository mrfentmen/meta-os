// services/tests/t139_updater_client_r11.goose
//
// Round 11, updater_client (R11-211..216): the four refusals, their independent counters,
// the apply/retry path, and the seeded truth about what is installed.
//
// t90 proves the happy path and the first STOP/rate/verify sequence; t94 proves a STOP
// cancels an offer. This driver adds: the seed refuses to go backwards, an equal version is
// "no update" not "rollback", each refusal counter counts only its own refusal, a failed
// apply can be retried exactly once, and a hundred checks in a row all answer.
//
// Status: RUNS after the coordinator's native run; written 2026-11-02.

import updater_client.updater_client;
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

fn same(a: const u8[:], b: const u8[:]) -> bool {
    if a.len != b.len { return false; }
    var i: i64 = 0;
    while i < a.len {
        if a[i] != b[i] { return false; }
        i = i + 1;
    }
    return true;
}

fn main() {
    say("t139 updater client r11\n");

    // ======================================================================
    // 1. a fresh client knows nothing, and the seed is the only truth
    // ======================================================================
    uc_init(0);
    let st0, code0 = uc_status();
    check("init: state is idle", st0 == UC_S_IDLE);
    check("init: last code is ok", code0 == CODE_OK);
    check("init: nothing applied", uc_applied_version() == 0);
    check("init: every counter is zero",
          uc_check_count() == 0 && uc_stop_count() == 0 && uc_verify_count() == 0
          && uc_rate_count() == 0 && uc_rollback_count() == 0);

    check("seed: a negative version is E_INVAL", uc_seed_applied(-1) == E_INVAL);
    check("seed: a version is accepted", uc_seed_applied(5) == CODE_OK);
    check("seed: a version below the applied one is E_ROLLBACK",
          uc_seed_applied(4) == E_ROLLBACK);
    check("seed: the applied version did not move backwards", uc_applied_version() == 5);

    // ======================================================================
    // 2. equal, newer, and the rate gate measured from the last accepted check
    // ======================================================================
    let eq = uc_check(false, 5, true, true, 0);
    check("check: the version already installed is UC_NO_UPDATE", eq == UC_NO_UPDATE);
    let st_eq, _code_eq = uc_status();
    check("check: no-update leaves the state idle", st_eq == UC_S_IDLE);

    let newer = uc_check(false, 6, true, true, 60000);
    check("check: a newer verified version is UC_AVAILABLE", newer == UC_AVAILABLE);
    check("check: the offer is recorded", uc_available_version() == 6);

    check("rate: one millisecond inside the window is UC_REFUSED_RATE",
          uc_check(false, 6, true, true, 119999) == UC_REFUSED_RATE);
    check("rate: exactly at the window is allowed",
          uc_check(false, 6, true, true, 120000) == UC_AVAILABLE);
    check("rate: the refusal got its own counter", uc_rate_count() == 1);

    // ======================================================================
    // 3. STOP cancels an offer, and verification does not touch state
    // ======================================================================
    check("stop: a STOP while an offer is open is UC_REFUSED_STOP",
          uc_check(true, 7, true, true, 180000) == UC_REFUSED_STOP);
    check("stop: the offer is withdrawn", uc_available_version() == 0);
    let st_stop, _code_stop = uc_status();
    check("stop: the state goes back to idle", st_stop == UC_S_IDLE);
    check("stop: only the stop counter moved", uc_stop_count() == 1 && uc_rate_count() == 1);

    check("verify: a failed digest is UC_REFUSED_VERIFY",
          uc_check(false, 7, false, true, 240000) == UC_REFUSED_VERIFY);
    check("verify: a failed signature is UC_REFUSED_VERIFY",
          uc_check(false, 8, true, false, 300000) == UC_REFUSED_VERIFY);
    check("verify: two refusals, two counts", uc_verify_count() == 2);
    check("verify: a refused verification offers nothing", uc_available_version() == 0);
    check("verify: no other counter moved",
          uc_stop_count() == 1 && uc_rate_count() == 1 && uc_rollback_count() == 0);

    // ======================================================================
    // 4. a server that goes backwards is a refusal, not a no-op
    // ======================================================================
    check("rollback: a version below the applied one is UC_REFUSED_ROLLBACK",
          uc_check(false, 4, true, true, 360000) == UC_REFUSED_ROLLBACK);
    check("rollback: it has its own counter", uc_rollback_count() == 1);
    check("rollback: nothing was offered", uc_available_version() == 0);

    // ======================================================================
    // 5. apply, and a failure that can be retried exactly once
    // ======================================================================
    uc_init(0);
    check("apply: an offer first", uc_check(false, 3, true, true, 0) == UC_AVAILABLE);
    check("apply: success reports ok", uc_apply(true) == CODE_OK);
    check("apply: the applied version is the offered one", uc_applied_version() == 3);
    let st_done, _code_done = uc_status();
    check("apply: the state is done", st_done == UC_S_DONE);
    check("apply: applied count is one", uc_applied_total() == 1);
    check("apply: applying nothing is E_STATE", uc_apply(true) == E_STATE);

    uc_init(0);
    check("retry: a fresh offer", uc_check(false, 4, true, true, 0) == UC_AVAILABLE);
    check("retry: a failed apply reports E_VERIFY", uc_apply(false) == E_VERIFY);
    let st_fail, _code_fail = uc_status();
    check("retry: the state is failed", st_fail == UC_S_FAILED);
    check("retry: the failure is counted", uc_failed_total() == 1);
    check("retry: the applied version did not move", uc_applied_version() == 0);
    check("retry: the offer is kept for the retry", uc_available_version() == 4);
    check("retry: retry returns to available", uc_retry() == CODE_OK);
    check("retry: a second retry is E_STATE", uc_retry() == E_STATE);

    // ======================================================================
    // 6. the strings a report prints
    // ======================================================================
    check("name: available", same(uc_state_name(UC_S_AVAILABLE), "available"));
    check("name: failed", same(uc_state_name(UC_S_FAILED), "failed"));
    check("name: an unknown state is not invented", same(uc_state_name(9), "?"));
    check("code: refused-stop", same(uc_code_name(UC_REFUSED_STOP), "refused-stop"));
    check("code: refused-verify", same(uc_code_name(UC_REFUSED_VERIFY), "refused-verify"));
    check("code: refused-rollback", same(uc_code_name(UC_REFUSED_ROLLBACK), "refused-rollback"));
    check("code: ok", same(uc_code_name(CODE_OK), "ok"));
    check("code: an unknown code says error", same(uc_code_name(123), "error"));

    // ======================================================================
    // 7. load: 100 checks across 100 windows
    // ======================================================================
    uc_init(0);
    var ops: i64 = 0;
    var okc: i64 = 0;
    var refused: i64 = 0;
    var k: i64 = 0;
    while k < 100 {
        let c = uc_check(false, 5, true, true, k * UC_MIN_INTERVAL_MS);
        if c == UC_AVAILABLE { okc = okc + 1; } else { refused = refused + 1; }
        ops = ops + 1;
        k = k + 1;
    }
    check("load: 100 checks, 100 answers", okc == 100 && refused == 0);
    check("load: the check counter agrees", uc_check_count() == 100);

    say("LOAD updater_client ops=");
    var ob: u8[>..] = [];
    let _ = append_int(ob, 32, ops);
    say(ob[..]);
    say(" ok=");
    var kb: u8[>..] = [];
    let _ = append_int(kb, 32, okc);
    say(kb[..]);
    say(" refused=");
    var rb: u8[>..] = [];
    let _ = append_int(rb, 32, refused);
    say(rb[..]);
    say("\n");

    say("t139 done  pass=");
    var pb: u8[>..] = [];
    let _ = append_int(pb, 32, t_pass);
    say(pb[..]);
    say(" fail=");
    var fb: u8[>..] = [];
    let _ = append_int(fb, 32, t_fail);
    say(fb[..]);
    say("\n");
    if t_fail > 0 { sys_exit(1); }
}
